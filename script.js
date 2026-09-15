/* =====================================================
   BLOCKVAULT
   Crypto Fraud Investigation MVP

   FRONTEND VERSION

   Authentication:
   - Google Demo Login
   - MetaMask / Web3 Wallet

   Blockchain:
   - Demo transaction data for MVP

   Later:
   Replace buildDemoResult() with FastAPI response.
===================================================== */


/* =====================================================
   GLOBAL STATE
===================================================== */

let currentUser = null;

let currentResult = null;

let connectedWallet = null;


/* =====================================================
   DEMO WALLET
===================================================== */

const DEMO_WALLET =
    "0x742d35Cc6634C0532925a3b844Bc454e4438f44e";


/* =====================================================
   PAGE LOAD
===================================================== */

document.addEventListener("DOMContentLoaded", () => {

    const loggedIn =
        localStorage.getItem("blockvaultLoggedIn");

    if (loggedIn === "true") {

        currentUser = {

            name:
                localStorage.getItem(
                    "blockvaultUserName"
                ) || "Wallet User",

            email:
                localStorage.getItem(
                    "blockvaultUserEmail"
                ) || "",

            wallet:
                localStorage.getItem(
                    "blockvaultWallet"
                ) || ""

        };

        connectedWallet =
            currentUser.wallet || null;

        showApp();

    } else {

        showAuth();

    }


    /* Wallet input */

    const walletInput =
        document.getElementById(
            "walletInput"
        );


    if (walletInput) {

        walletInput.addEventListener(
            "keydown",
            event => {

                if (event.key === "Enter") {

                    analyzeWallet();

                }

            }
        );

    }


    /* Close transaction modal
       when clicking outside */

    const transactionModal =
        document.getElementById(
            "transactionModal"
        );


    if (transactionModal) {

        transactionModal.addEventListener(
            "click",
            event => {

                if (
                    event.target ===
                    transactionModal
                ) {

                    closeTransactionModal();

                }

            }
        );

    }


    /* Close transaction analysis */

    const transactionAnalysisModal =
        document.getElementById(
            "transactionAnalysisModal"
        );


    if (transactionAnalysisModal) {

        transactionAnalysisModal.addEventListener(
            "click",
            event => {

                if (
                    event.target ===
                    transactionAnalysisModal
                ) {

                    closeTransactionAnalysis();

                }

            }
        );

    }

});


/* =====================================================
   AUTH PAGE
===================================================== */

function showAuth() {

    document
        .getElementById("authPage")
        .classList.remove("hidden");


    document
        .getElementById("appPage")
        .classList.add("hidden");

}


/* =====================================================
   SHOW APPLICATION
===================================================== */

function showApp() {

    document
        .getElementById("authPage")
        .classList.add("hidden");


    document
        .getElementById("appPage")
        .classList.remove("hidden");


    updateUserUI();

    goHome();

}


/* =====================================================
   GOOGLE LOGIN
===================================================== */

function continueWithGoogle() {

    /*
        REAL VERSION LATER:

        Google button
             ↓
        Google OAuth
             ↓
        Backend verification
             ↓
        User session

        For MVP we simulate successful
        Google authentication.
    */


    const googleName =
        "Google Investigator";


    const googleEmail =
        "investigator@blockvault.demo";


    currentUser = {

        name: googleName,

        email: googleEmail,

        wallet:
            localStorage.getItem(
                "blockvaultWallet"
            ) || ""

    };


    localStorage.setItem(
        "blockvaultLoggedIn",
        "true"
    );


    localStorage.setItem(
        "blockvaultUserName",
        googleName
    );


    localStorage.setItem(
        "blockvaultUserEmail",
        googleEmail
    );


    updateUserUI();

    showApp();

}


/* =====================================================
   METAMASK / WEB3 WALLET
===================================================== */
async function connectWallet() {
    // Check if MetaMask / Ethereum wallet is installed
    if (!window.ethereum) {
        alert(
            "MetaMask is not detected.\n\n" +
            "Please install the MetaMask browser extension and try again."
        );
        return;
    }

    try {
        // Open MetaMask
        const accounts = await window.ethereum.request({
            method: "eth_requestAccounts"
        });

        if (!accounts || accounts.length === 0) {
            alert("No wallet account was selected.");
            return;
        }

        // Get the selected wallet address
        connectedWallet = accounts[0];

        currentUser = {
            name: "Wallet Investigator",
            email: "",
            wallet: connectedWallet
        };

        // Save wallet session
        localStorage.setItem(
            "blockvaultWallet",
            connectedWallet
        );

        localStorage.setItem(
            "blockvaultLoggedIn",
            "true"
        );

        localStorage.setItem(
            "blockvaultUserName",
            "Wallet Investigator"
        );

        // Open the BlockVault application
        showApp();

        // Put the actual MetaMask address into the wallet input
        const walletInput = document.getElementById("walletInput");

        if (walletInput) {
            walletInput.value = connectedWallet;
        }

        updateUserUI();

    } catch (error) {

        console.error("MetaMask connection error:", error);

        if (error.code === 4001) {
            alert("You rejected the MetaMask connection.");
        } else {
            alert("Unable to connect to MetaMask. Please try again.");
        }
    }
}


/* =====================================================
   SAVE WALLET SESSION
===================================================== */

function saveWalletSession() {

    localStorage.setItem(
        "blockvaultLoggedIn",
        "true"
    );


    localStorage.setItem(
        "blockvaultUserName",
        currentUser.name
    );


    localStorage.setItem(
        "blockvaultUserEmail",
        currentUser.email || ""
    );


    localStorage.setItem(
        "blockvaultWallet",
        currentUser.wallet || ""
    );

}


/* =====================================================
   LOGOUT / DISCONNECT
===================================================== */

function logout() {

    localStorage.removeItem(
        "blockvaultLoggedIn"
    );

    localStorage.removeItem(
        "blockvaultUserName"
    );

    localStorage.removeItem(
        "blockvaultUserEmail"
    );

    localStorage.removeItem(
        "blockvaultWallet"
    );


    currentUser = null;

    connectedWallet = null;

    currentResult = null;


    showAuth();

}


/* =====================================================
   UPDATE USER UI
===================================================== */

function updateUserUI() {

    const name =
        currentUser?.name ||
        "Wallet User";


    document
        .getElementById("userName")
        .textContent =
        name;


    document
        .getElementById(
            "caseInvestigator"
        )
        .textContent =
        name;


    document
        .getElementById(
            "userAvatar"
        )
        .textContent =
        name
            .charAt(0)
            .toUpperCase();


    const walletElement =
        document.getElementById(
            "connectedWallet"
        );


    if (
        currentUser?.wallet
    ) {

        walletElement.textContent =
            shortenAddress(
                currentUser.wallet
            );

    } else {

        walletElement.textContent =
            "Google Account";

    }

}


/* =====================================================
   NAVIGATION
===================================================== */

function goHome() {

    document
        .getElementById("homeSection")
        .classList.remove("hidden");


    document
        .getElementById("dashboardSection")
        .classList.add("hidden");


    setActiveNav(0);


    window.scrollTo({

        top: 0,

        behavior: "smooth"

    });

}


/* =====================================================
   OPEN DASHBOARD
===================================================== */

function openDashboard() {

    document
        .getElementById("homeSection")
        .classList.add("hidden");


    document
        .getElementById("dashboardSection")
        .classList.remove("hidden");


    setActiveNav(1);


    window.scrollTo({

        top: 0,

        behavior: "smooth"

    });


    /*
        The dashboard is evidence-driven.
        Do not fabricate a demo investigation.
    */

    if (!currentResult) {
        const wallet =
            document.getElementById("walletInput").value.trim() ||
            connectedWallet ||
            "";

        if (isValidEthereumAddress(wallet)) {
            analyzeWallet();
            return;
        }
    }

}


/* =====================================================
   REPORTS
===================================================== */

function openReports() {

    openDashboard();


    setTimeout(() => {

        const report =
            document.querySelector(
                ".report-card"
            );


        if (report) {

            report.scrollIntoView({

                behavior:
                    "smooth",

                block:
                    "center"

            });

        }

    }, 150);

}


/* =====================================================
   ACTIVE NAVIGATION
===================================================== */

function setActiveNav(index) {

    const buttons =
        document.querySelectorAll(
            ".nav-btn"
        );


    buttons.forEach(
        button => {

            button.classList.remove(
                "active"
            );

        }
    );


    if (buttons[index]) {

        buttons[index]
            .classList.add(
                "active"
            );

    }

}


/* =====================================================
   ANALYZE WALLET
===================================================== */


function analyzeWallet() {

    let wallet =
        document.getElementById("walletInput").value.trim();

    if (!wallet) {
        wallet = connectedWallet || "";
        document.getElementById("walletInput").value = wallet;
    }

    if (!isValidEthereumAddress(wallet)) {
        alert("Please enter a valid Ethereum wallet address.");
        return;
    }

    resetAnalysisSteps();

    const overlay = document.getElementById("analysisOverlay");
    overlay.classList.remove("hidden");

    const status = document.getElementById("analysisStatus");
    const steps = [
        ["Collecting all wallet transactions...", 1],
        ["Mapping linked wallet relationships...", 2],
        ["Analyzing transaction behavior...", 3],
        ["Calculating wallet risk score...", 4]
    ];

    steps.forEach(([text, n], i) => {
        setTimeout(() => {
            status.textContent = text;
            const step = document.getElementById("step" + n);
            if (step) {
                step.classList.add("step-done");
                const marker = step.querySelector("span");
                if (marker) marker.textContent = "✓";
            }
        }, i * 450);
    });

    fetch("/api/analyze-wallet", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({wallet: wallet})
    })
    .then(async response => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || "Wallet analysis failed.");
        }
        return data;
    })
    .then(data => {
        currentResult = data;
        renderDashboard(currentResult);
        overlay.classList.add("hidden");
        openDashboard();
    })
    .catch(error => {
        console.error("Wallet analysis error:", error);
        overlay.classList.add("hidden");
        alert(
            "Analysis could not be completed.\n\n" +
            error.message
        );
    });
}


/* =====================================================
   RESET ANALYSIS STEPS
===================================================== */

function resetAnalysisSteps() {

    for (
        let i = 1;
        i <= 4;
        i++
    ) {

        const step =
            document.getElementById(
                "step" + i
            );


        if (step) {

            step.classList.remove(
                "step-done"
            );


            step
                .querySelector(
                    "span"
                )
                .textContent =
                "○";

        }

    }

}


/* =====================================================
   ETHEREUM ADDRESS VALIDATION
===================================================== */

function isValidEthereumAddress(
    address
) {

    return /^0x[a-fA-F0-9]{40}$/
        .test(address);

}


/* =====================================================
   DEMO BLOCKCHAIN RESULT
===================================================== */

function buildDemoResult(
    wallet
) {

    /*
        IMPORTANT:

        These are demonstration transactions.

        Later this function will be replaced with:

        fetch("/api/analyze-wallet")

        and the response will come from FastAPI.
    */


    const transactions = [

        {
            id: 1,

            hash:
                "0x8a71d3e9f4c0b12e9a17",

            fullHash:
                "0x8a71d3e9f4c0b12e9a17b84d731f9e82b4e18f90",

            from:
                wallet,

            to:
                "0x91b7A2d4E9f8C3b6A1D52a84",

            value:
                "12.48 ETH",

            numericValue:
                12.48,

            time:
                "08 Sep 2026, 18:42",

            block:
                "23184521",

            gas:
                "0.00184 ETH",

            status:
                "Confirmed",

            behavior:
                "Rapid movement after receipt",

            riskScore:
                87,

            analyzed:
                false,

            riskReasons: [

                "Large-value transfer",

                "Rapid movement pattern",

                "Counterparty linked to another wallet",

                "Short time interval between transfers"

            ]

        },


        {
            id: 2,

            hash:
                "0x5f29b8a10d7c441a8c21",

            fullHash:
                "0x5f29b8a10d7c441a8c21d9f4b731eab8239c71",

            from:
                wallet,

            to:
                "0x42e9B71C91bc",

            value:
                "7.20 ETH",

            numericValue:
                7.20,

            time:
                "08 Sep 2026, 18:36",

            block:
                "23184505",

            gas:
                "0.00121 ETH",

            status:
                "Confirmed",

            behavior:
                "Multiple-hop movement",

            riskScore:
                79,

            analyzed:
                false,

            riskReasons: [

                "Multiple wallet hop detected",

                "Unusual transfer frequency",

                "Destination has connected counterparties"

            ]

        },


        {
            id: 3,

            hash:
                "0xb19e4c8a71f332d7f81",

            fullHash:
                "0xb19e4c8a71f332d7f81c829f3e8d11a94c",

            from:
                wallet,

            to:
                "0x7ca1C9D44de",

            value:
                "3.75 ETH",

            numericValue:
                3.75,

            time:
                "08 Sep 2026, 17:51",

            block:
                "23184391",

            gas:
                "0.00094 ETH",

            status:
                "Confirmed",

            behavior:
                "Unusual counterparty",

            riskScore:
                61,

            analyzed:
                false,

            riskReasons: [

                "Counterparty is newly observed",

                "Transaction value is above normal baseline",

                "Wallet relationship requires further investigation"

            ]

        },


        {
            id: 4,

            hash:
                "0xd8124f9a20c6b88e2f5",

            fullHash:
                "0xd8124f9a20c6b88e2f5123ac9d771b42",

            from:
                "0x91b7A2d4E9f8C3b6A1D52a84",

            to:
                "0xexchange44F1",

            value:
                "11.90 ETH",

            numericValue:
                11.90,

            time:
                "08 Sep 2026, 17:58",

            block:
                "23184402",

            gas:
                "0.00147 ETH",

            status:
                "Confirmed",

            behavior:
                "Exchange-linked movement",

            riskScore:
                91,

            analyzed:
                false,

            riskReasons: [

                "Exchange-linked destination",

                "Large-value transfer",

                "Fund movement occurred shortly after receipt"

            ]

        },


        {
            id: 5,

            hash:
                "0xc71f9a8b21d45e73",

            fullHash:
                "0xc71f9a8b21d45e73b28c71f92d8e44",

            from:
                wallet,

            to:
                "0x8d92F1B3e71A",

            value:
                "0.35 ETH",

            numericValue:
                0.35,

            time:
                "08 Sep 2026, 16:21",

            block:
                "23184021",

            gas:
                "0.00031 ETH",

            status:
                "Confirmed",

            behavior:
                "Normal wallet transfer",

            riskScore:
                14,

            analyzed:
                false,

            riskReasons: [

                "Low transaction value",

                "Normal transaction interval",

                "No high-risk counterparty detected"

            ]

        },


        {
            id: 6,

            hash:
                "0xa92c71f44e28d913",

            fullHash:
                "0xa92c71f44e28d913b8274d1a9c5e31",

            from:
                "0x8d92F1B3e71A",

            to:
                wallet,

            value:
                "0.82 ETH",

            numericValue:
                0.82,

            time:
                "08 Sep 2026, 15:04",

            block:
                "23183790",

            gas:
                "0.00028 ETH",

            status:
                "Confirmed",

            behavior:
                "Normal incoming transfer",

            riskScore:
                9,

            analyzed:
                false,

            riskReasons: [

                "Normal incoming transaction",

                "Low value",

                "No suspicious pattern detected"

            ]

        },


        {
            id: 7,

            hash:
                "0xe17d28b4c912a71f",

            fullHash:
                "0xe17d28b4c912a71f39c8e22d1a",

            from:
                wallet,

            to:
                "0x71B4C92e8A22",

            value:
                "0.18 ETH",

            numericValue:
                0.18,

            time:
                "07 Sep 2026, 21:18",

            block:
                "23180142",

            gas:
                "0.00022 ETH",

            status:
                "Confirmed",

            behavior:
                "Normal transfer",

            riskScore:
                11,

            analyzed:
                false,

            riskReasons: [

                "Low-value transaction",

                "Normal frequency",

                "No high-risk destination detected"

            ]

        },


        {
            id: 8,

            hash:
                "0xf29e71c8b412d55a",

            fullHash:
                "0xf29e71c8b412d55a82e91f4c7a",

            from:
                wallet,

            to:
                "0x9f81C44A2e71",

            value:
                "5.90 ETH",

            numericValue:
                5.90,

            time:
                "07 Sep 2026, 20:42",

            block:
                "23179980",

            gas:
                "0.00091 ETH",

            status:
                "Confirmed",

            behavior:
                "High-value movement",

            riskScore:
                73,

            analyzed:
                false,

            riskReasons: [

                "High transaction value",

                "Transaction occurred during rapid activity period",

                "Destination has multiple wallet relationships"

            ]

        }

    ];


    /*
        Linked wallets
    */

    const linkedWallets = [

        {
            address:
                "0x91b7...2a84",

            type:
                "Direct Counterparty",

            risk:
                "HIGH"
        },

        {
            address:
                "0x42e9...91bc",

            type:
                "Second-Hop Wallet",

            risk:
                "HIGH"
        },

        {
            address:
                "0x7ca1...44de",

            type:
                "Connected Wallet",

            risk:
                "MEDIUM"
        },

        {
            address:
                "0x8d92...e71A",

            type:
                "Normal Counterparty",

            risk:
                "LOW"
        }

    ];


    /*
        Overall wallet risk factors
    */

    const riskFactors = [

        {
            title:
                "Rapid Fund Movement",

            description:
                "Several high-value transfers occurred within short time intervals."
        },

        {
            title:
                "Multiple Wallet Relationships",

            description:
                "The reported wallet is connected to multiple downstream and upstream addresses."
        },

        {
            title:
                "Large Transaction Values",

            description:
                "Multiple transactions involve significantly higher values than ordinary wallet activity."
        },

        {
            title:
                "Exchange Exposure",

            description:
                "A downstream transaction reaches an address identified as exchange/VASP-linked."
        }

    ];


    /*
        Timeline
    */

    const timeline = [

        {
            time:
                "15:04",

            event:
                "0.82 ETH received"
        },

        {
            time:
                "16:21",

            event:
                "0.35 ETH transferred"
        },

        {
            time:
                "17:51",

            event:
                "3.75 ETH transferred"
        },

        {
            time:
                "17:58",

            event:
                "11.90 ETH reached exchange-linked address"
        },

        {
            time:
                "18:36",

            event:
                "7.20 ETH transferred"
        },

        {
            time:
                "18:42",

            event:
                "12.48 ETH transferred"
        }

    ];


    return {

        wallet:

            wallet,

        caseId:

            "BV-" +
            Math.floor(
                100000 +
                Math.random() *
                899999
            ),

        /*
            Overall wallet score.
        */

        riskScore:
            87,

        riskLabel:
            "HIGH RISK",

        transactionCount:
            transactions.length,

        walletHops:
            4,

        traceableValue:
            "32.63 ETH",

        transactions:

            transactions,

        riskFactors:

            riskFactors,

        linkedWallets:

            linkedWallets,

        exchange: {

            name:
                "Detected Exchange / VASP",

            description:
                "A downstream address shows characteristics consistent with a centralized exchange or virtual asset service provider.",

            confidence:
                91

        },

        timeline:

            timeline

    };

}


/* =====================================================
   RENDER COMPLETE DASHBOARD
===================================================== */

function renderDashboard(
    data
) {

    document
        .getElementById(
            "caseId"
        )
        .textContent =
        data.caseId;


    document
        .getElementById(
            "reportedWallet"
        )
        .textContent =
        data.wallet;


    document
        .getElementById(
            "riskScore"
        )
        .textContent =
        data.riskScore;


    document
        .getElementById(
            "riskLabel"
        )
        .textContent =
        data.riskLabel;


    document
        .getElementById(
            "riskBar"
        )
        .style.width =
        data.riskScore + "%";


    document
        .getElementById(
            "transactionCount"
        )
        .textContent =
        data.transactionCount;


    document
        .getElementById(
            "walletHops"
        )
        .textContent =
        data.walletHops;


    document
        .getElementById(
            "traceableValue"
        )
        .textContent =
        data.traceableValue;


    renderWalletProfile(
        data
    );


    renderRiskFactors(
        data.riskFactors
    );


    renderTransactions(
        data.transactions
    );


    renderLinkedWallets(
        data.linkedWallets
    );


    renderExchange(
        data.exchange
    );


    renderTimeline(
        data.timeline
    );

    renderGraph(
        data
    );

}


/* =====================================================
   WALLET PROFILE
===================================================== */

function renderWalletProfile(
    data
) {

    const container =
        document.getElementById(
            "walletProfile"
        );


    if (!container) {
        return;
    }


    container.innerHTML = `

        <div class="wallet-profile-item">

            <span>
                NETWORK
            </span>

            <strong>
                Ethereum
            </strong>

        </div>


        <div class="wallet-profile-item">

            <span>
                TRANSACTIONS
            </span>

            <strong>
                ${data.transactionCount}
            </strong>

        </div>


        <div class="wallet-profile-item">

            <span>
                TRACE DEPTH
            </span>

            <strong>
                ${data.walletHops} hops
            </strong>

        </div>


        <div class="wallet-profile-item">

            <span>
                WALLET RISK
            </span>

            <strong>
                ${data.riskLabel}
            </strong>

        </div>

    `;

}


/* =====================================================
   RISK FACTORS
===================================================== */

function renderRiskFactors(
    factors
) {

    const container =
        document.getElementById(
            "riskFactors"
        );


    container.innerHTML =

        factors
            .map(
                factor => `

                <div class="risk-factor">

                    <div class="risk-factor-icon">
                        ⚠
                    </div>

                    <div>

                        <h4>
                            ${escapeHTML(
                                factor.title
                            )}
                        </h4>

                        <p>
                            ${escapeHTML(
                                factor.description
                            )}
                        </p>

                    </div>

                </div>

            `
            )
            .join("");

}


/* =====================================================
   RENDER ALL TRANSACTIONS
===================================================== */

function renderTransactions(
    transactions
) {

    const table =
        document.getElementById(
            "transactionTable"
        );


    /*
        Update summary
    */

    const suspicious =
        transactions.filter(
            tx =>
                tx.riskScore >= 60
        ).length;


    const normal =
        transactions.length -
        suspicious;


    document
        .getElementById(
            "transactionBadge"
        )
        .textContent =
        transactions.length;


    document
        .getElementById(
            "totalTransactions"
        )
        .textContent =
        transactions.length;


    document
        .getElementById(
            "suspiciousTransactions"
        )
        .textContent =
        suspicious;


    document
        .getElementById(
            "normalTransactions"
        )
        .textContent =
        normal;


    /*
        Render every transaction
    */

    table.innerHTML =

        transactions
            .map(
                (tx, index) => {

                    const status =
                        tx.analyzed

                            ? (
                                tx.riskScore >= 60
                                    ? "SUSPICIOUS"
                                    : "NOT SUSPICIOUS"
                            )

                            : "NOT ANALYZED";


                    const statusClass =
                        tx.analyzed

                            ? (
                                tx.riskScore >= 60
                                    ? "suspicious"
                                    : "normal"
                            )

                            : "pending";


                    const riskClass =
                        tx.riskScore >= 60

                            ? "risk-high"

                            : tx.riskScore >= 40

                                ? "risk-medium"

                                : "risk-low";


                    return `

                        <tr>

                            <td class="hash">

                                ${escapeHTML(
                                    tx.hash
                                )}

                            </td>


                            <td class="address">

                                ${escapeHTML(
                                    shortenAddress(
                                        tx.from
                                    )
                                )}

                            </td>


                            <td class="address">

                                ${escapeHTML(
                                    shortenAddress(
                                        tx.to
                                    )
                                )}

                            </td>


                            <td>

                                ${escapeHTML(
                                    tx.value
                                )}

                            </td>


                            <td>

                                ${escapeHTML(
                                    tx.time
                                )}

                            </td>


                            <td>

                                <span
                                    class="
                                        transaction-status
                                        ${statusClass}
                                    ">

                                    ${status}

                                </span>

                            </td>


                            <td class="${riskClass}">

                                ${
                                    tx.analyzed
                                        ? tx.riskScore + "/100"
                                        : "—"
                                }

                            </td>


                            <td>

                                <div
                                    class="transaction-actions">


                                    <button
                                        class="analyze-tx-btn"
                                        onclick="
                                            analyzeTransaction(
                                                ${index}
                                            )
                                        ">

                                        Analyze

                                    </button>


                                    <button
                                        class="view-btn"
                                        onclick="
                                            showTransaction(
                                                ${index}
                                            )
                                        ">

                                        View

                                    </button>


                                </div>

                            </td>

                        </tr>

                    `;

                }
            )
            .join("");

}


/* =====================================================
   INDIVIDUAL TRANSACTION ANALYSIS
===================================================== */


async function analyzeTransaction(index) {

    if (!currentResult || !currentResult.transactions[index]) {
        return;
    }

    const tx = currentResult.transactions[index];

    try {
        const response = await fetch("/api/analyze-transaction", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                wallet: currentResult.wallet,
                transaction: tx
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Transaction analysis failed.");
        }

        Object.assign(tx, result.transaction || {});
        tx.analyzed = true;

        const suspicious = tx.riskScore >= 60;
        const decision = suspicious ? "SUSPICIOUS" : "NOT SUSPICIOUS";
        const decisionClass = suspicious ? "suspicious" : "normal";

        const resultContainer =
            document.getElementById("transactionRiskResult");

        resultContainer.innerHTML = `
            <div class="tx-risk-header">
                <div>
                    <div class="tx-analysis-title">TRANSACTION RISK SCORE</div>
                    <div class="tx-risk-score">
                        <strong>${tx.riskScore}</strong>
                        <span>/100</span>
                    </div>
                </div>
                <div class="tx-decision ${decisionClass}">
                    ${suspicious ? "🔴 " : "🟢 "}${decision}
                </div>
            </div>

            <div class="tx-risk-meter">
                <div style="
                    width:${tx.riskScore}%;
                    background:${
                        suspicious
                        ? "linear-gradient(90deg,#f59e0b,#ef4444)"
                        : "linear-gradient(90deg,#22c55e,#22d3ee)"
                    };
                "></div>
            </div>

            <div class="tx-analysis-title">ANALYSIS REASONS</div>

            <div class="tx-reasons">
                ${(tx.riskReasons || ["No suspicious indicator detected."])
                    .map(reason => `
                        <div class="tx-reason">
                            <span>✓</span>
                            ${escapeHTML(reason)}
                        </div>
                    `).join("")}
            </div>
        `;

        const evidence = document.getElementById("transactionEvidence");

        evidence.innerHTML = `
            <div class="evidence-heading">BLOCKCHAIN EVIDENCE</div>
            <div class="evidence-grid">
                <div class="evidence-item full">
                    <span>TRANSACTION HASH</span>
                    <strong>${escapeHTML(tx.fullHash || tx.hash || "")}</strong>
                </div>
                <div class="evidence-item">
                    <span>FROM</span>
                    <strong>${escapeHTML(tx.from || "")}</strong>
                </div>
                <div class="evidence-item">
                    <span>TO</span>
                    <strong>${escapeHTML(tx.to || "Contract creation / unavailable")}</strong>
                </div>
                <div class="evidence-item">
                    <span>VALUE</span>
                    <strong>${escapeHTML(tx.value || "0 ETH")}</strong>
                </div>
                <div class="evidence-item">
                    <span>TIMESTAMP</span>
                    <strong>${escapeHTML(tx.time || "")}</strong>
                </div>
                <div class="evidence-item">
                    <span>BLOCK</span>
                    <strong>${escapeHTML(String(tx.block || ""))}</strong>
                </div>
                <div class="evidence-item">
                    <span>GAS</span>
                    <strong>${escapeHTML(tx.gas || "Unavailable")}</strong>
                </div>
                <div class="evidence-item full">
                    <span>BEHAVIOR</span>
                    <strong>${escapeHTML(tx.behavior || "No behavioral summary available")}</strong>
                </div>
            </div>
        `;

        document
            .getElementById("transactionAnalysisModal")
            .classList.remove("hidden");

        renderTransactions(currentResult.transactions);

    } catch (error) {
        console.error("Transaction analysis error:", error);
        alert("Transaction analysis failed.\n\n" + error.message);
    }
}


/* =====================================================
   CLOSE INDIVIDUAL ANALYSIS
===================================================== */

function closeTransactionAnalysis() {

    document
        .getElementById(
            "transactionAnalysisModal"
        )
        .classList.add(
            "hidden"
        );

}


/* =====================================================
   VIEW TRANSACTION DETAILS
===================================================== */

function showTransaction(
    index
) {

    const tx =
        currentResult
            .transactions[index];


    const container =
        document.getElementById(
            "transactionDetails"
        );


    container.innerHTML = `

        <div class="detail-row">

            <span>
                Transaction Hash
            </span>

            <strong>
                ${escapeHTML(
                    tx.fullHash
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                From
            </span>

            <strong>
                ${escapeHTML(
                    tx.from
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                To
            </span>

            <strong>
                ${escapeHTML(
                    tx.to
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Value
            </span>

            <strong>
                ${escapeHTML(
                    tx.value
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Timestamp
            </span>

            <strong>
                ${escapeHTML(
                    tx.time
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Block Number
            </span>

            <strong>
                ${escapeHTML(
                    tx.block
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Gas Used
            </span>

            <strong>
                ${escapeHTML(
                    tx.gas
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Blockchain Status
            </span>

            <strong>
                ${escapeHTML(
                    tx.status
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Transaction Behavior
            </span>

            <strong>
                ${escapeHTML(
                    tx.behavior
                )}
            </strong>

        </div>


        <div class="detail-row">

            <span>
                Risk Score
            </span>

            <strong>

                ${
                    tx.analyzed
                        ? tx.riskScore +
                          "/100"
                        : "Not analyzed yet"
                }

            </strong>

        </div>

    `;


    document
        .getElementById(
            "transactionModal"
        )
        .classList.remove(
            "hidden"
        );

}


/* =====================================================
   CLOSE TRANSACTION DETAILS
===================================================== */

function closeTransactionModal() {

    document
        .getElementById(
            "transactionModal"
        )
        .classList.add(
            "hidden"
        );

}


/* =====================================================
   LINKED WALLETS
===================================================== */


/* =====================================================
   DYNAMIC FUND-FLOW GRAPH
===================================================== */

function renderGraph(data) {

    const graph = document.getElementById("graph");
    if (!graph) return;

    const links = data.graphLinks || [];
    const center = data.wallet || "";

    /*
        Keep the existing P2 graph container and styling.
        Only replace its demo nodes/edges with evidence-backed
        relationships returned by the backend.
    */
    graph.innerHTML = '<div class="graph-grid"></div>';

    const positions = [
        ["graph-left", -1],
        ["graph-right", 1],
        ["graph-top", -1],
        ["graph-bottom", 1]
    ];

    const maxNodes = Math.min(links.length, positions.length);

    const centerNode = document.createElement("div");
    centerNode.className = "graph-node graph-center";
    centerNode.innerHTML =
        `<span>W</span><small>Reported Wallet</small>`;
    graph.appendChild(centerNode);

    for (let i = 0; i < maxNodes; i++) {
        const item = links[i];
        const [positionClass] = positions[i];

        const node = document.createElement("div");
        node.className = "graph-node " + positionClass;
        node.innerHTML =
            `<span>${escapeHTML(item.label || String.fromCharCode(65 + i))}</span>` +
            `<small>${escapeHTML(item.type || "Linked Wallet")}</small>`;
        graph.appendChild(node);

        const edge = document.createElement("div");
        edge.className = "graph-edge edge-" + (i + 1);
        graph.appendChild(edge);
    }

    if (maxNodes === 0) {
        const empty = document.createElement("div");
        empty.style.cssText =
            "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;" +
            "color:#64748b;font-size:12px;z-index:4;";
        empty.textContent =
            "No wallet relationships were returned from the available blockchain evidence.";
        graph.appendChild(empty);
    }
}

function renderLinkedWallets(
    wallets
) {

    const container =
        document.getElementById(
            "linkedWallets"
        );


    container.innerHTML =

        wallets
            .map(
                wallet => `

                <div class="linked-wallet">

                    <div class="wallet-info">

                        <strong>
                            ${escapeHTML(
                                wallet.address
                            )}
                        </strong>

                        <span>
                            ${escapeHTML(
                                wallet.type
                            )}
                        </span>

                    </div>


                    <span
                        class="
                            wallet-risk
                            ${
                                wallet.risk ===
                                "HIGH"

                                    ? "high"

                                    : wallet.risk ===
                                      "MEDIUM"

                                        ? "medium"

                                        : "low"
                            }
                        ">

                        ${escapeHTML(
                            wallet.risk
                        )}

                    </span>

                </div>

            `
            )
            .join("");

}


/* =====================================================
   EXCHANGE
===================================================== */

function renderExchange(
    exchange
) {

    const container =
        document.getElementById(
            "exchangeInfo"
        );


    container.innerHTML = `

        <div class="exchange-box">


            <div class="exchange-name">

                ${escapeHTML(
                    exchange.name
                )}

            </div>


            <p>

                ${escapeHTML(
                    exchange.description
                )}

            </p>


            <div class="confidence">

                <span>
                    Attribution Confidence
                </span>

                <strong>
                    ${exchange.confidence}%
                </strong>

            </div>


            <div class="confidence-bar">

                <div
                    style="
                        width:${exchange.confidence}%
                    ">
                </div>

            </div>


        </div>

    `;

}


/* =====================================================
   TIMELINE
===================================================== */

function renderTimeline(
    events
) {

    const container =
        document.getElementById(
            "timeline"
        );


    container.innerHTML =

        events
            .map(
                event => `

                <div class="timeline-item">

                    <strong>
                        ${escapeHTML(
                            event.time
                        )}
                    </strong>

                    <span>
                        ${escapeHTML(
                            event.event
                        )}
                    </span>

                </div>

            `
            )
            .join("");

}


/* =====================================================
   COPY WALLET
===================================================== */

function copyWallet() {

    const wallet =
        document
            .getElementById(
                "reportedWallet"
            )
            .textContent;


    if (
        navigator.clipboard
    ) {

        navigator.clipboard
            .writeText(wallet)
            .then(() => {

                alert(
                    "Wallet address copied."
                );

            });

    } else {

        alert(
            "Copy is not supported by this browser."
        );

    }

}


/* =====================================================
   JSON REPORT
===================================================== */

function generateJSONReport() {

    if (!currentResult) {

        alert(
            "Run a wallet analysis first."
        );

        return;

    }


    const report = {

        platform:
            "BlockVault",

        version:
            "MVP",

        generatedAt:
            new Date().toISOString(),

        investigation:
            currentResult

    };


    const blob =
        new Blob(

            [
                JSON.stringify(
                    report,
                    null,
                    2
                )
            ],

            {
                type:
                    "application/json"
            }

        );


    const url =
        URL.createObjectURL(
            blob
        );


    const link =
        document.createElement(
            "a"
        );


    link.href =
        url;


    link.download =
        currentResult.caseId +
        "_investigation.json";


    document
        .body
        .appendChild(
            link
        );


    link.click();


    link.remove();


    URL.revokeObjectURL(
        url
    );

}


/* =====================================================
   PDF REPORT
===================================================== */

function generatePDFReport() {

    if (!currentResult) {

        alert(
            "Run a wallet analysis first."
        );

        return;

    }


    /*
        Browser print dialog allows
        user to choose:

        Save as PDF
    */

    window.print();

}


/* =====================================================
   SHORTEN ADDRESS
===================================================== */

function shortenAddress(
    address
) {

    if (
        !address ||
        address.length < 12
    ) {

        return address;

    }


    return (
        address.slice(0, 7) +
        "..." +
        address.slice(-6)
    );

}


/* =====================================================
   HTML ESCAPE
===================================================== */

function escapeHTML(
    value
) {

    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


/* =====================================================
   METAMASK ACCOUNT CHANGE
===================================================== */

if (
    typeof window.ethereum !==
    "undefined"
) {

    window.ethereum.on(
        "accountsChanged",
        accounts => {

            if (
                accounts.length === 0
            ) {

                connectedWallet =
                    null;

                return;

            }


            connectedWallet =
                accounts[0];


            if (currentUser) {

                currentUser.wallet =
                    connectedWallet;

                saveWalletSession();

                updateUserUI();

            }


            const walletInput =
                document.getElementById(
                    "walletInput"
                );


            if (walletInput) {

                walletInput.value =
                    connectedWallet;

            }

        }
    );

}