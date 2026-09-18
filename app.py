
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timezone
from decimal import Decimal
from collections import Counter, defaultdict
import json
import os, re, time, threading
import requests

try:
    from web3 import Web3
except Exception:
    Web3 = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)

GANACHE_RPC = os.getenv("GANACHE_RPC", "http://127.0.0.1:7545")
BLOCKSCOUT_TX_URL = "https://eth.blockscout.com/api/v2/addresses/{address}/transactions"
BLOCKSCOUT_TOKEN_TX_URL = "https://eth.blockscout.com/api/v2/addresses/{address}/token-transfers"
BLOCKSCOUT_PAGE_LIMIT = 10
BLOCKSCOUT_PAGE_SIZE = 50
TRANSACTION_CACHE_TTL = int(os.getenv("TRANSACTION_CACHE_TTL", "60"))

_transaction_cache = {}
_transaction_cache_lock = threading.Lock()

def load_known_high_risk():
    """Load verified intelligence indicators from deployment configuration."""
    try:
        configured = json.loads(os.getenv("KNOWN_HIGH_RISK_JSON", "{}"))
    except (TypeError, json.JSONDecodeError):
        configured = {}

    if not isinstance(configured, dict):
        return {}

    return {
        address.lower(): str(reason)
        for address, reason in configured.items()
        if isinstance(address, str) and re.fullmatch(
            r"0x[a-fA-F0-9]{40}", address
        )
    }


KNOWN_HIGH_RISK = load_known_high_risk()

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

    asset_type = tx.get("asset_type", "native")
    token_amount = float(tx.get("token_amount", 0) or 0)
    token_symbol = tx.get("token_symbol", "")
    native_value = float(tx.get("value_eth", 0) or 0)

    return {
        "hash": tx.get("hash") or tx.get("transaction_hash") or "",
        "fullHash": tx.get("hash") or tx.get("transaction_hash") or "",
        "from": from_addr,
        "to": to_addr or "",
        "counterparty": counterparty or "",
        "assetType": asset_type,
        "assetSymbol": token_symbol or "ETH",
        "tokenAmount": token_amount if asset_type == "token" else 0,
        "nativeValueEth": native_value,
        "valueEth": native_value,
        "value": (
            f"{token_amount:.6f} {token_symbol}"
            if asset_type == "token"
            else f"{native_value:.6f} ETH"
        ),
        "numericValue": native_value,
        "time": fmt_time(tx.get("timestamp")),
        "timestamp": tx.get("timestamp"),
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


def fetch_blockscout_pages(url):
    # The address endpoint already scopes results to this wallet. Blockscout
    # rejects the old `from | to` filter value with HTTP 422.
    params = {}
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

    return all_items


def fetch_blockscout(wallet):
    transaction_items = fetch_blockscout_pages(
        BLOCKSCOUT_TX_URL.format(address=wallet)
    )

    results = []
    for item in transaction_items:
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

    try:
        token_items = fetch_blockscout_pages(
            BLOCKSCOUT_TOKEN_TX_URL.format(address=wallet)
        )
    except Exception as exc:
        print("Blockscout token lookup skipped:", exc)
        token_items = []

    for item in token_items:
        from_addr = ((item.get("from") or {}).get("hash") or "").strip()
        to_addr = ((item.get("to") or {}).get("hash") or "").strip()
        token = item.get("token") or {}
        total = item.get("total") or {}
        decimals = int(token.get("decimals") or 0)
        raw_value = total.get("value") or "0"
        try:
            token_amount = float(Decimal(str(raw_value)) / Decimal(10 ** decimals))
        except (ArithmeticError, ValueError):
            token_amount = 0.0

        results.append({
            "hash": item.get("transaction_hash") or item.get("hash", ""),
            "from": from_addr,
            "to": to_addr,
            "value_eth": 0.0,
            "token_amount": token_amount,
            "token_symbol": token.get("symbol") or "TOKEN",
            "asset_type": "token",
            "timestamp": item.get("timestamp"),
            "block_number": item.get("block_number", ""),
            "gas": "Available from chain explorer",
            "status": "Confirmed"
        })

    return results


def fetch_transactions(wallet):
    # Prefer the local Ganache chain when the supplied wallet actually has
    # local activity. Otherwise query Ethereum mainnet through Blockscout.
    cache_key = wallet.lower()
    now = time.monotonic()

    with _transaction_cache_lock:
        cached = _transaction_cache.get(cache_key)
        if cached and now - cached["created"] < TRANSACTION_CACHE_TTL:
            return [dict(tx) for tx in cached["transactions"]], cached["source"]

    try:
        local = fetch_ganache(wallet)
        if local:
            with _transaction_cache_lock:
                _transaction_cache[cache_key] = {
                    "created": time.monotonic(),
                    "transactions": [dict(tx) for tx in local],
                    "source": "Ganache (local Ethereum-compatible network)"
                }
            return local, "Ganache (local Ethereum-compatible network)"
    except Exception as exc:
        print("Ganache lookup skipped:", exc)

    try:
        remote = fetch_blockscout(wallet)
        with _transaction_cache_lock:
            _transaction_cache[cache_key] = {
                "created": time.monotonic(),
                "transactions": [dict(tx) for tx in remote],
                "source": "Ethereum Mainnet via Blockscout"
            }
        return remote, "Ethereum Mainnet via Blockscout"
    except Exception as exc:
        print("Blockscout lookup failed:", exc)
        return [], "Unavailable"


def timestamp_seconds(tx):
    value = tx.get("timestamp")
    if isinstance(value, (int, float)):
        return float(value)

    if value:
        try:
            text = str(value).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except (TypeError, ValueError, OverflowError):
            pass

    return None


def median_value(values):
    ordered = sorted(values)
    if not ordered:
        return 0.0

    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def analyze_behavior(transactions):
    values = [tx["numericValue"] for tx in transactions if tx["numericValue"] > 0]
    baseline = median_value(values)
    outlier_multiplier = float(os.getenv("RISK_OUTLIER_MULTIPLIER", "5"))
    burst_window = float(os.getenv("RISK_BURST_WINDOW_SECONDS", "3600"))
    pass_through_window = float(
        os.getenv("RISK_PASS_THROUGH_WINDOW_SECONDS", "21600")
    )
    fanout_threshold = int(os.getenv("RISK_FANOUT_THRESHOLD", "5"))

    outliers = {
        id(tx) for tx in transactions
        if tx["numericValue"] > 0 and (
            tx["numericValue"] >= max(5.0, baseline * outlier_multiplier)
            if baseline
            else tx["numericValue"] >= 10.0
        )
    }

    dated = sorted(
        (
            (timestamp_seconds(tx), tx)
            for tx in transactions
            if timestamp_seconds(tx) is not None
        ),
        key=lambda item: item[0]
    )

    burst_transactions = set()
    for index, (start, _) in enumerate(dated):
        window = dated[index:index + 8]
        if len(window) >= 4 and window[-1][0] - start <= burst_window:
            burst_transactions.update(id(tx) for _, tx in window)

    incoming = [
        (timestamp_seconds(tx), tx) for tx in transactions
        if tx["direction"] == "IN" and timestamp_seconds(tx) is not None
    ]
    outgoing = [
        (timestamp_seconds(tx), tx) for tx in transactions
        if tx["direction"] == "OUT" and timestamp_seconds(tx) is not None
    ]
    pass_through_transactions = set()
    for incoming_time, incoming_tx in incoming:
        for outgoing_time, outgoing_tx in outgoing:
            if 0 <= outgoing_time - incoming_time <= pass_through_window:
                pass_through_transactions.update({
                    id(incoming_tx),
                    id(outgoing_tx)
                })

    counterparties = {
        tx["counterparty"].lower()
        for tx in transactions
        if valid_address(tx.get("counterparty"))
    }
    total_value = sum(tx["numericValue"] for tx in transactions)
    largest_counterparty_value = 0.0
    if counterparties:
        largest_counterparty_value = max(
            sum(
                tx["numericValue"] for tx in transactions
                if tx.get("counterparty", "").lower() == address
            )
            for address in counterparties
        )

    return {
        "medianValueEth": round(baseline, 6),
        "outlierTransactions": outliers,
        "burstTransactions": burst_transactions,
        "passThroughTransactions": pass_through_transactions,
        "burstDetected": bool(burst_transactions),
        "passThroughDetected": bool(pass_through_transactions),
        "fanoutDetected": len(counterparties) >= fanout_threshold,
        "counterpartyConcentration": round(
            largest_counterparty_value / total_value,
            6
        ) if total_value else 0
    }


def score_transaction(tx, behavior=None):
    score = 0
    reasons = []

    address = (tx.get("counterparty") or tx.get("to") or "").lower()
    value = float(tx.get("value_eth", 0) or 0)

    if address in KNOWN_HIGH_RISK:
        score += 90
        reasons.append(KNOWN_HIGH_RISK[address])

    if behavior and id(tx) in behavior["outlierTransactions"]:
        score += 25
        reasons.append(
            "Transaction value is a significant outlier against this wallet's median transfer."
        )
    elif value >= 10:
        score += 15
        reasons.append("High-value native transfer.")

    if behavior and id(tx) in behavior["burstTransactions"]:
        score += 15
        reasons.append("Transaction occurred inside a high-frequency activity burst.")

    if behavior and id(tx) in behavior["passThroughTransactions"]:
        score += 15
        reasons.append("Funds moved in and out within the configured pass-through window.")

    if not tx.get("to"):
        reasons.append("Contract-creation transaction; no wallet recipient was available.")

    if not reasons:
        reasons.append("No configured high-risk indicator was detected for this transaction.")

    return min(score, 100), reasons


def build_analysis(wallet, raw, source, include_counterparty_scan=False):
    shaped = [tx_shape(t, wallet) for t in raw]
    behavior = analyze_behavior(shaped)

    # Score individual transactions and compute behavioural features.
    for tx in shaped:
        s, reasons = score_transaction(tx, behavior)
        tx["riskScore"] = s
        tx["riskReasons"] = reasons
        tx["behavior"] = "; ".join(reasons[:2])
        tx["analyzed"] = True

    counterparties = Counter(
        tx["counterparty"].lower()
        for tx in shaped
        if valid_address(tx.get("counterparty"))
    )

    counterparty_investigations = {}
    if include_counterparty_scan:
        for address in counterparties:
            counterparty_raw, counterparty_source = fetch_transactions(address)
            counterparty_investigations[address] = build_analysis(
                address,
                counterparty_raw,
                counterparty_source
            )

        for tx in shaped:
            address = tx.get("counterparty", "").lower()
            investigation = counterparty_investigations.get(address)
            if investigation and investigation["riskScore"] > tx["riskScore"]:
                tx["riskScore"] = investigation["riskScore"]
                tx["riskReasons"] = list(dict.fromkeys(
                    tx["riskReasons"] + [
                        "Counterparty pre-scan raised the transaction risk score."
                    ]
                ))
                tx["behavior"] = "; ".join(tx["riskReasons"][:2])

    direct_risk_links = sorted({
        tx["counterparty"].lower()
        for tx in shaped
        if tx.get("counterparty", "").lower() in KNOWN_HIGH_RISK
    })

    graph_links = []
    linked_wallets = []
    for addr, count in counterparties.most_common(4):
        original = next(
            tx["counterparty"] for tx in shaped
            if tx.get("counterparty", "").lower() == addr
        )
        investigation = counterparty_investigations.get(addr)
        high = (
            addr in KNOWN_HIGH_RISK or
            bool(investigation and investigation["riskScore"] >= 60)
        )
        graph_links.append({
            "address": original,
            "label": "H" if high else "L",
            "type": "High-risk indicator" if high else "Linked Wallet",
            "count": count,
            "totalValueEth": round(
                sum(
                    tx["numericValue"] for tx in shaped
                    if tx.get("counterparty", "").lower() == addr
                ),
                6
            ),
            "incomingCount": sum(
                1 for tx in shaped
                if tx.get("counterparty", "").lower() == addr
                and tx["direction"] == "IN"
            ),
            "outgoingCount": sum(
                1 for tx in shaped
                if tx.get("counterparty", "").lower() == addr
                and tx["direction"] == "OUT"
            ),
            "risk": "HIGH" if high else "LOW"
        })
        linked_wallets.append({
            "address": original,
            "type": "Direct Counterparty",
            "risk": "HIGH" if high else "LOW",
            "transactionCount": count,
            "totalValueEth": round(
                sum(
                    tx["numericValue"] for tx in shaped
                    if tx.get("counterparty", "").lower() == addr
                ),
                6
            )
        })

    total_value = sum(tx["numericValue"] for tx in shaped)
    incoming = [tx for tx in shaped if tx["direction"] == "IN"]
    outgoing = [tx for tx in shaped if tx["direction"] == "OUT"]
    high_risk_transactions = [tx for tx in shaped if tx["riskScore"] >= 60]

    if "Blockscout" in source:
        for tx in shaped:
            if tx["hash"]:
                tx["explorerUrl"] = f"https://eth.blockscout.com/tx/{tx['hash']}"

    counterparty_summary = []
    for address, count in counterparties.most_common(10):
        matching = [
            tx for tx in shaped
            if tx.get("counterparty", "").lower() == address
        ]
        counterparty_summary.append({
            "address": matching[0]["counterparty"],
            "transactionCount": count,
            "totalValueEth": round(
                sum(tx["numericValue"] for tx in matching),
                6
            ),
            "risk": (
                "HIGH"
                if address in KNOWN_HIGH_RISK or (
                    counterparty_investigations.get(address) and
                    counterparty_investigations[address]["riskScore"] >= 60
                )
                else "LOW"
            )
        })

    largest_transaction = max(
        shaped,
        key=lambda tx: tx["numericValue"],
        default=None
    )

    transaction_summary = {
        "total": len(shaped),
        "tokenTransferCount": sum(
            1 for tx in shaped if tx["assetType"] == "token"
        ),
        "incomingCount": len(incoming),
        "outgoingCount": len(outgoing),
        "incomingValueEth": round(
            sum(tx["numericValue"] for tx in incoming),
            6
        ),
        "outgoingValueEth": round(
            sum(tx["numericValue"] for tx in outgoing),
            6
        ),
        "averageValueEth": round(
            total_value / len(shaped),
            6
        ) if shaped else 0,
        "highRiskCount": len(high_risk_transactions),
        "largestTransaction": {
            "hash": largest_transaction["hash"],
            "valueEth": largest_transaction["numericValue"],
            "direction": largest_transaction["direction"],
            "counterparty": largest_transaction["counterparty"]
        } if largest_transaction else None
    }

    risk_score = 0
    factors = []

    if wallet.lower() in KNOWN_HIGH_RISK:
        risk_score += 90
        factors.append({
            "title": "External Threat-Intelligence Match",
            "description": KNOWN_HIGH_RISK[wallet.lower()] + "."
        })

    if direct_risk_links:
        risk_score += 35
        factors.append({
            "title": "Direct High-Risk Wallet Exposure",
            "description": (
                f"The wallet has a direct transaction relationship with "
                f"{len(direct_risk_links)} configured high-risk wallet(s)."
            )
        })

    if behavior["outlierTransactions"]:
        risk_score += 20
        factors.append({
            "title": "Adaptive Value Outliers",
            "description": (
                f"{len(behavior['outlierTransactions'])} transaction(s) "
                f"are unusually large relative to the wallet's "
                f"{behavior['medianValueEth']:.6f} ETH median transfer."
            )
        })

    if behavior["burstDetected"]:
        risk_score += 20
        factors.append({
            "title": "High-Frequency Activity Burst",
            "description": "Several transactions occurred within a short time window."
        })

    if behavior["passThroughDetected"]:
        risk_score += 20
        factors.append({
            "title": "Rapid Pass-Through Movement",
            "description": "Incoming funds were followed by outgoing movement within the pass-through window."
        })

    if behavior["fanoutDetected"]:
        risk_score += 10
        factors.append({
            "title": "High Counterparty Fan-Out",
            "description": "The wallet distributes funds across many distinct counterparties."
        })

    if behavior["counterpartyConcentration"] >= 0.7 and len(counterparties) >= 2:
        risk_score += 10
        factors.append({
            "title": "Counterparty Concentration",
            "description": "Most observed value is concentrated with one counterparty."
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

    highest_transaction_score = max(
        (tx["riskScore"] for tx in shaped),
        default=0
    )
    if highest_transaction_score > risk_score:
        risk_score = highest_transaction_score
        factors.append({
            "title": "Highest Transaction Risk Signal",
            "description": (
                f"The wallet score includes the highest precomputed "
                f"transaction risk score of {highest_transaction_score}/100."
            )
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

    evidence_unavailable = (
        source == "Unavailable" or
        "provider unavailable" in source.lower()
    )

    # If data could not be retrieved, do not present that as a safe wallet.
    if evidence_unavailable and wallet.lower() not in KNOWN_HIGH_RISK:
        label = "UNABLE TO VERIFY"
        classification = "DATA UNAVAILABLE"
        risk_score = 0
        factors = [{
            "title": "Blockchain Evidence Unavailable",
            "description": "The configured blockchain data sources could not return transaction evidence."
        }]
    elif not shaped and not evidence_unavailable:
        label = "NO OBSERVED ACTIVITY"
        classification = "NO_ACTIVITY"
        risk_score = 0
        factors = [{
            "title": "No On-Chain Transactions Found",
            "description": "The configured blockchain source responded successfully but returned no transactions for this wallet."
        }]
    elif evidence_unavailable:
        factors.append({
            "title": "Blockchain Evidence Unavailable",
            "description": "Transaction providers were unavailable, but the configured wallet intelligence match remains visible."
        })

    timeline = []
    ordered_transactions = sorted(
        shaped,
        key=lambda tx: int(str(tx.get("block", "0")).split(".")[0])
        if str(tx.get("block", "0")).split(".")[0].isdigit()
        else 0,
        reverse=True
    )
    for tx in reversed(ordered_transactions[:8]):
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
        "analysisMethod": "Transparent adaptive behavior rules plus one-hop graph exposure analysis",
        "behaviorSignals": {
            "medianValueEth": behavior["medianValueEth"],
            "burstDetected": behavior["burstDetected"],
            "passThroughDetected": behavior["passThroughDetected"],
            "fanoutDetected": behavior["fanoutDetected"],
            "counterpartyConcentration": behavior["counterpartyConcentration"]
        },
        "riskThresholds": {
            "critical": 80,
            "high": 60,
            "medium": 40
        },
        "evidenceStatus": "unavailable" if evidence_unavailable else "available",
        "evidenceMessage": (
            "Blockchain providers did not return transaction evidence."
            if evidence_unavailable
            else "Blockchain source responded successfully."
        ),
        "transactions": shaped,
        "transactionSummary": transaction_summary,
        "transactionAnalysis": {
            "status": "complete" if shaped else "complete_no_transactions",
            "analyzedCount": len(shaped),
            "pendingCount": 0,
            "scope": "All retrieved wallet transactions"
        },
        "counterpartySummary": counterparty_summary,
        "riskFactors": factors,
        "linkedWallets": linked_wallets,
        "graphLinks": graph_links,
        "graphAnalysis": {
            "nodes": len(counterparties) + 1,
            "edges": len(shaped),
            "directRiskLinks": len(direct_risk_links),
            "riskPropagation": "one-hop direct counterparty exposure"
        },
        "limitations": [
            "Risk scoring is rule-based and is not a machine-learning prediction.",
            "Graph exposure currently covers observed direct counterparties only.",
            "Exchange attribution is not asserted without a verified data source."
        ],
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

    result = build_analysis(
        wallet,
        raw,
        source,
        include_counterparty_scan=True
    )
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
