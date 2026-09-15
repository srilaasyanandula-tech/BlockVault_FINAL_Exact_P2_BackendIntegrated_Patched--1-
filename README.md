# BlockVault — exact P2 frontend with live backend

This build keeps the supplied P2 `index.html` and `style.css` unchanged.
Only `script.js` was wired to the Flask backend; `app.py` serves the exact
relative frontend paths `/style.css` and `/script.js`.

Run:
    pip install -r requirements.txt
    python app.py

Open:
    http://127.0.0.1:5000

The backend uses local Ganache when the wallet has local activity and otherwise
uses Ethereum Mainnet Blockscout transaction data. If data cannot be retrieved,
the UI does not silently classify the wallet as safe.

The Google button remains the supplied P2 MVP demo login; it is not real Google OAuth.
Hello ;)
Nice to meet you