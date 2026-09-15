
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timezone
from decimal import Decimal
from collections import Counter, defaultdict
import os, re, time
import requests

try:
    from web3 import Web3
except Exception:
    Web3 = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)

GANACHE_RPC = os.getenv("GANACHE_RPC", "http://127.0.0.1:7545")
BLOCKSCOUT_TX_URL = "https://eth.blockscout.com/api/v2/addresses/{address}/transactions"
BLOCKSCOUT_PAGE_LIMIT = 10
BLOCKSCOUT_PAGE_SIZE = 50

# This is a project-configured intelligence indicator supplied for the
# demonstration wallet used by the team. It is NOT a generic claim that
# every address should be treated as fraudulent.
KNOWN_HIGH_RISK = {
    "0x7db418b5d567a4e0e8c59ad71be1fce48f3e6107":
        "OFAC Blocked / sanctions-related address indicator"
}

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def valid_address(address):
    return isinstance(address, str) and bool(ADDRESS_RE.fullmatch(address.strip()))


def short(address):
    if not address:
        return "—"
    return address[:10] + "..." + address[-8:]


def fmt_time(value):
    if not value:
        return "Unknown"
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
        else:
            text = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%d %b %Y, %H:%M")
    except Exception:
        return str(value)


def wei_to_eth(value):
    try:
        return Decimal(str(value)) / Decimal(10**18)
    except Exception:
        return Decimal("0")


def tx_shape(tx, wallet):
    wallet_l = wallet.lower()
    from_addr = (tx.get("from") or "").strip()
    to_addr = (tx.get("to") or "").strip() or None

    if from_addr.lower() == wallet_l:
        direction = "OUT"
        counterparty = to_addr
    elif to_addr and to_addr.lower() == wallet_l:
        direction = "IN"
        counterparty = from_addr
    else:
        # Internal/edge cases: prefer whichever address is not the wallet.
        direction = "OUT"
        counterparty = to_addr or from_addr or None

    return {
        "hash": tx.get("hash") or tx.get("transaction_hash") or "",
        "fullHash": tx.get("hash") or tx.get("transaction_hash") or "",
        "from": from_addr,
        "to": to_addr or "",
        "counterparty": counterparty or "",
        "valueEth": float(tx.get("value_eth", 0)),
        "value": f'{float(tx.get("value_eth", 0)):.6f} ETH',
        "numericValue": float(tx.get("value_eth", 0)),
        "time": fmt_time(tx.get("timestamp")),
        "block": tx.get("block_number", ""),
        "gas": tx.get("gas", "Unavailable"),
        "status": tx.get("status", "Confirmed"),
        "direction": direction,
    }


def fetch_ganache(wallet):
    if Web3 is None:
        return []

    w3 = Web3(Web3.HTTPProvider(GANACHE_RPC, request_kwargs={"timeout": 4}))
    if not w3.is_connected():
        return []

    latest = w3.eth.block_number
    results = []

    # Ganache chains are intentionally small; scan their complete local history.
    for block_no in range(latest + 1):
        block = w3.eth.get_block(block_no, full_transactions=True)
        timestamp = block.get("timestamp", 0)

        for tx in block["transactions"]:
            frm = tx.get("from", "")
            to = tx.get("to", "") or ""

            if frm.lower() != wallet.lower() and to.lower() != wallet.lower():
                continue

            results.append({
                "hash": tx["hash"].hex() if hasattr(tx["hash"], "hex") else str(tx["hash"]),
                "from": frm,
                "to": to,
                "value_eth": float(w3.from_wei(tx["value"], "ether")),
                "timestamp": timestamp,
                "block_number": block_no,
                "gas": f'{float(w3.from_wei(tx["gas"] * tx["gasPrice"], "ether")):.8f} ETH',
                "status": "Confirmed"
            })

    results.sort(key=lambda x: (x.get("block_number", 0), x.get("hash", "")), reverse=True)
    return results


def fetch_blockscout(wallet):
    url = BLOCKSCOUT_TX_URL.format(address=wallet)
    params = {"filter": "from | to"}
    all_items = []
    page_params = None

    for _ in range(BLOCKSCOUT_PAGE_LIMIT):
        p = dict(params)
        if page_params:
            p.update(page_params)

        r = requests.get(url, params=p, timeout=12)
        r.raise_for_status()
        payload = r.json()
        items = payload.get("items", [])
        all_items.extend(items)

        next_params = payload.get("next_page_params")
        if not next_params or not items:
            break
        page_params = next_params

    results = []
    for item in all_items:
        frm = ((item.get("from") or {}).get("hash") or "").strip()
        to_obj = item.get("to") or {}
        to = (to_obj.get("hash") or "").strip()

        # Blockscout can return contract creations without a "to" address.
        # Those remain visible, but are not treated as a wallet counterparty.
        value_wei = item.get("value") or "0"
        try:
            value_eth = float(Decimal(str(value_wei)) / Decimal(10**18))
        except Exception:
            value_eth = 0.0

        results.append({
            "hash": item.get("hash", ""),
            "from": frm,
            "to": to,
            "value_eth": value_eth,
            "timestamp": item.get("timestamp"),
            "block_number": item.get("block_number", ""),
            "gas": "Available from chain explorer",
            "status": "Confirmed" if item.get("status") in (None, "ok") else str(item.get("status")),
        })

    return results


def fetch_transactions(wallet):
    # Prefer the local Ganache chain when the supplied wallet actually has
    # local activity. Otherwise query Ethereum mainnet through Blockscout.
    try:
        local = fetch_ganache(wallet)
        if local:
            return local, "Ganache (local Ethereum-compatible network)"
    except Exception as exc:
        print("Ganache lookup skipped:", exc)

    try:
        remote = fetch_blockscout(wallet)
        return remote, "Ethereum Mainnet via Blockscout"
    except Exception as exc:
        print("Blockscout lookup failed:", exc)
        return [], "Unavailable"


def score_transaction(tx):
    score = 0
    reasons = []

    address = (tx.get("counterparty") or tx.get("to") or "").lower()
    value = float(tx.get("value_eth", 0) or 0)

    if address in KNOWN_HIGH_RISK:
        score += 90
        reasons.append(KNOWN_HIGH_RISK[address])

    if value >= 10:
        score += 20
        reasons.append("High-value native transfer.")
    elif value >= 5:
        score += 10
        reasons.append("Elevated-value native transfer.")

    if not tx.get("to"):
        reasons.append("Contract-creation transaction; no wallet recipient was available.")

    if not reasons:
        reasons.append("No configured high-risk indicator was detected for this transaction.")

    return min(score, 100), reasons


def build_analysis(wallet, raw, source):
    shaped = [tx_shape(t, wallet) for t in raw]

    # Score individual transactions and compute behavioural features.
    for tx in shaped:
        s, reasons = score_transaction(tx)
        tx["riskScore"] = s
        tx["riskReasons"] = reasons
        tx["behavior"] = "; ".join(reasons[:2])
        tx["analyzed"] = False

    counterparties = Counter(
        tx["counterparty"].lower()
        for tx in shaped
        if valid_address(tx.get("counterparty"))
    )

    graph_links = []
    linked_wallets = []
    for addr, count in counterparties.most_common(4):
        original = next(
            tx["counterparty"] for tx in shaped
            if tx.get("counterparty", "").lower() == addr
        )
        high = addr in KNOWN_HIGH_RISK
        graph_links.append({
            "address": original,
            "label": "H" if high else "L",
            "type": "High-risk indicator" if high else "Linked Wallet",
            "count": count
        })
        linked_wallets.append({
            "address": original,
            "type": "Direct Counterparty",
            "risk": "HIGH" if high else "LOW"
        })

    scores = [tx["riskScore"] for tx in shaped]
    total_value = sum(tx["numericValue"] for tx in shaped)

    risk_score = 0
    factors = []

    if wallet.lower() in KNOWN_HIGH_RISK:
        risk_score += 90
        factors.append({
            "title": "External Threat-Intelligence Match",
            "description": KNOWN_HIGH_RISK[wallet.lower()] + "."
        })

    if len(shaped) >= 10:
        risk_score += 5
        factors.append({
            "title": "Repeated On-Chain Activity",
            "description": f"{len(shaped)} transactions were retrieved for the investigated wallet."
        })

    if len(counterparties) >= 4:
        risk_score += 5
        factors.append({
            "title": "Multiple Wallet Relationships",
            "description": f"{len(counterparties)} distinct counterparties were observed in the retrieved evidence."
        })

    if any(tx["numericValue"] >= 10 for tx in shaped):
        risk_score += 5
        factors.append({
            "title": "High-Value Movement",
            "description": "At least one retrieved transaction contains a high-value native transfer."
        })

    if not factors:
        factors.append({
            "title": "No configured high-risk indicator detected",
            "description": "The available evidence did not match the configured risk indicators."
        })

    risk_score = min(risk_score, 100)

    if risk_score >= 80:
        label, classification = "CRITICAL RISK", "FRAUD-LINKED"
    elif risk_score >= 60:
        label, classification = "HIGH RISK", "SUSPICIOUS"
    elif risk_score >= 40:
        label, classification = "MEDIUM RISK", "SUSPICIOUS"
    else:
        label, classification = "LOW RISK", "NORMAL"

    # If data could not be retrieved, do not present that as a safe wallet.
    if source == "Unavailable":
        label = "UNABLE TO VERIFY"
        classification = "DATA UNAVAILABLE"
        risk_score = 0
        factors = [{
            "title": "Blockchain Evidence Unavailable",
            "description": "The configured blockchain data sources could not return transaction evidence."
        }]

    timeline = []
    for tx in reversed(shaped[-8:]):
        timeline.append({
            "time": tx["time"],
            "event": f'{tx["direction"]} {tx["value"]} — {short(tx["counterparty"])}'
        })

    return {
        "wallet": wallet,
        "caseId": "BV-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
        "riskScore": risk_score,
        "riskLabel": label,
        "classification": classification,
        "transactionCount": len(shaped),
        "walletHops": len(counterparties),
        "traceableValue": f"{total_value:.4f} ETH",
        "dataSource": source,
        "transactions": shaped,
        "riskFactors": factors,
        "linkedWallets": linked_wallets,
        "graphLinks": graph_links,
        "exchange": {
            "name": "No verified exchange attribution",
            "description": "The current P2 frontend does not contain an exchange-attribution module. No exchange identity is fabricated.",
            "confidence": 0
        },
        "timeline": timeline
    }


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:filename>")
def frontend_asset(filename):
    # The supplied frontend uses relative /style.css and /script.js paths.
    if filename in {"index.html", "script.js", "style.css"}:
        return send_from_directory(BASE_DIR, filename)
    return ("Not Found", 404)


@app.get("/api/health")
def health():
    ganache = False
    try:
        if Web3:
            ganache = Web3(Web3.HTTPProvider(
                GANACHE_RPC, request_kwargs={"timeout": 2}
            )).is_connected()
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "ganache": ganache,
        "ethereum_fallback": True
    })


@app.post("/api/analyze-wallet")
def analyze_wallet():
    body = request.get_json(silent=True) or {}
    wallet = (body.get("wallet") or "").strip()

    if not valid_address(wallet):
        return jsonify({"error": "Invalid Ethereum wallet address."}), 400

    raw, source = fetch_transactions(wallet)

    # A configured threat-intelligence match remains visible even if the
    # network provider is temporarily unavailable.
    if not raw and wallet.lower() in KNOWN_HIGH_RISK:
        source = "Threat-intelligence match; transaction provider unavailable"

    result = build_analysis(wallet, raw, source)
    return jsonify(result)


@app.post("/api/analyze-transaction")
def analyze_transaction():
    body = request.get_json(silent=True) or {}
    wallet = body.get("wallet")
    tx = body.get("transaction") or {}

    if not valid_address(wallet):
        return jsonify({"error": "Invalid wallet address."}), 400

    counterparty = (tx.get("counterparty") or tx.get("to") or "").strip()

    # Contract-creation transactions legitimately have no recipient ("to")
    # address. Analyze the transaction itself instead of showing a browser
    # alert or treating the missing recipient as an application error.
    if not valid_address(counterparty):
        updated = dict(tx)
        base_score, base_reasons = score_transaction(tx)
        updated["riskScore"] = base_score
        updated["riskReasons"] = list(dict.fromkeys(
            base_reasons + [
                "Counterparty tracing is unavailable because this transaction has no recipient wallet address."
            ]
        ))
        updated["behavior"] = "; ".join(updated["riskReasons"][:2])
        updated["analyzed"] = True

        return jsonify({
            "transaction": updated,
            "counterpartyAnalysis": None
        })

    # Investigate the counterparty itself rather than fabricating a local score.
    raw, source = fetch_transactions(counterparty)
    result = build_analysis(counterparty, raw, source)

    # Surface the counterparty-level investigation in the transaction modal.
    base_score, base_reasons = score_transaction({
        "counterparty": counterparty,
        "to": counterparty,
        "value_eth": tx.get("numericValue", 0)
    })

    combined_score = max(base_score, result["riskScore"])
    reasons = list(dict.fromkeys(
        base_reasons +
        [f"Counterparty investigation returned {result['transactionCount']} transaction(s)."] +
        ([f"Counterparty classification: {result['classification']}."] if result["classification"] else [])
    ))

    updated = dict(tx)
    updated["riskScore"] = combined_score
    updated["riskReasons"] = reasons
    updated["behavior"] = "; ".join(reasons[:2])
    updated["analyzed"] = True

    return jsonify({
        "transaction": updated,
        "counterpartyAnalysis": result
    })


if __name__ == "__main__":
    print("BlockVault backend running at http://127.0.0.1:5000")
    print("Ganache RPC:", GANACHE_RPC)
    app.run(host="127.0.0.1", port=5000, debug=False)
