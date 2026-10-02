# 🔒 AI-Based Secure Chat Analyser

A real-time chat application where every message is:
1. **Encrypted** before being stored (AES via Fernet) — the "secure" half.
2. **Analysed by AI** for sentiment, toxicity, and leaked sensitive info, and given a
   risk level (SAFE / LOW / MEDIUM / HIGH) — the "AI" half.
3. Shown live in a **risk dashboard** so risky behaviour is visible instantly.

This was verified end-to-end (dependencies install, AI analysis, encryption
round-trip, and all REST endpoints) before being handed to you.

---

## 1. Architecture

```
Browser (frontend/)              Flask Backend (backend/)
┌────────────────────┐           ┌───────────────────────────────┐
│ login.html          │  REST    │ /api/register, /api/login      │
│ index.html + JS     │ ───────▶ │ (JWT auth, bcrypt password hash)│
│  - Socket.IO client │           │                                 │
│  - Risk dashboard    │◀────────▶│ Socket.IO: join / send_message │
└────────────────────┘  realtime │        │                        │
                                  │        ▼                        │
                                  │  ai_analyzer.py                 │
                                  │  (sentiment, toxicity, PII scan)│
                                  │        │                        │
                                  │        ▼                        │
                                  │  encryption.py (AES/Fernet)     │
                                  │        │                        │
                                  │        ▼                        │
                                  │  SQLite DB (models.py)          │
                                  └───────────────────────────────┘
```

**Flow per message:** user types → sent over Socket.IO with JWT → backend
verifies identity → `ChatAnalyzer.analyze()` scores it → plaintext is
encrypted with Fernet → encrypted content + analysis metadata saved to
SQLite → decrypted content + analysis broadcast back to the room → if
risk is MEDIUM/HIGH, a separate `risk_alert` event fires for the dashboard.

---

## 2. Tech stack

| Layer          | Choice                                    | Why |
|-----------------|--------------------------------------------|-----|
| Backend         | Flask + Flask-SocketIO                    | simple, well-documented, good for a PBL demo |
| Auth            | Flask-JWT-Extended + Flask-Bcrypt         | industry-standard token auth + salted password hashing |
| DB              | SQLite via SQLAlchemy                     | zero-config, file-based, fine for a project |
| Encryption      | `cryptography` (Fernet = AES-128-CBC+HMAC)| authenticated symmetric encryption, easy to explain in a viva |
| AI: sentiment   | TextBlob                                  | lightweight, no model download needed |
| AI: toxicity    | Weighted keyword lexicon                  | transparent/explainable; swap for a trained model later (see §7) |
| AI: PII/leak scan | Regex (email, phone, card, URL)         | standard DLP technique |
| Frontend        | Plain HTML/CSS/JS + Socket.IO client      | no build tooling needed, runs by opening a file |

---

## 3. Project structure

```
secure-chat-analyzer/
├── backend/
│   ├── app.py            # Flask app, REST routes, Socket.IO events
│   ├── ai_analyzer.py     # sentiment + toxicity + sensitive-info + risk scoring
│   ├── encryption.py      # Fernet encrypt/decrypt wrapper
│   ├── models.py          # SQLAlchemy User & Message models
│   ├── config.py          # app config (reads .env)
│   └── requirements.txt
└── frontend/
    ├── login.html
    ├── index.html
    ├── script.js
    ├── config.js           # set your backend URL here
    └── style.css
```

---

## 4. Setup in VS Code (step by step)

### Step 1 — Open the project
Open VS Code → `File > Open Folder` → select the `secure-chat-analyzer` folder.
Install the **Python** extension (Microsoft) and the **Live Server** extension
if you don't have them, from the Extensions panel (`Ctrl+Shift+X`).

### Step 2 — Create a virtual environment
Open a VS Code terminal (`` Ctrl+` ``) and run:

```bash
cd backend
python -m venv venv
```

Activate it:
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

VS Code may prompt "Select this interpreter for the workspace" — click **Yes**.

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Generate your own encryption key
Never ship the default key. Generate one:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Create a file `backend/.env` with:
```
SECRET_KEY=some-random-string
JWT_SECRET_KEY=another-random-string-32-chars-min
ENCRYPTION_KEY=<paste the generated key here>
```
(If you skip this, `app.py` will auto-generate a temporary key each run and
print it to the terminal — fine for quick testing, but old messages become
undecryptable after a restart since the key changes.)

### Step 5 — Run the backend
```bash
python app.py
```
You should see `wsgi starting up on http://0.0.0.0:5000`. Leave this terminal running.

### Step 6 — Run the frontend
Open `frontend/login.html` in VS Code, right-click → **Open with Live Server**
(or just double-click the file in your file explorer to open it in a browser).
If your backend runs on a different host/port, edit `frontend/config.js`.

### Step 7 — Try it out
1. Register two different users (open a second browser tab/incognito window
   for the second user) in the same room name.
2. Send messages between them. Watch the risk badge, sentiment score, and
   dashboard update live.
3. Try a toxic message ("you are so stupid"), and a message with an email or
   10-digit phone number, to see MEDIUM/HIGH risk flags and alerts fire.

---

## 5. How the AI analysis works (for your report/viva)

`ChatAnalyzer.analyze(text)` runs four checks and combines them:

1. **Sentiment** — TextBlob gives a polarity score from -1 (very negative) to
   +1 (very positive), and a subjectivity score. Polarity is bucketed into
   positive / neutral / negative.
2. **Toxicity** — a weighted lexicon of harmful terms; each match contributes
   a severity weight (0–1), the max is taken, with a small boost if multiple
   toxic terms appear together. Above `TOXICITY_FLAG_THRESHOLD` (default 0.4)
   the message is flagged.
3. **Sensitive info** — regex scan for emails, 10-digit phone numbers,
   card-like digit sequences, and URLs — modelling a basic DLP (Data Loss
   Prevention) capability.
4. **Risk level** — combines the three: HIGH if toxicity ≥0.7 or a card
   number is found; MEDIUM if toxic or sensitive info is flagged; LOW if
   sentiment is strongly negative; else SAFE.

## 6. How the security works

- **Passwords**: hashed with bcrypt (salted, adaptive cost) — never stored
  in plaintext.
- **Auth**: JWT access tokens (8-hour expiry) required for every REST call
  and Socket.IO connection.
- **Messages at rest**: encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
  before touching the database — only decrypted server-side, in memory,
  when returning data to an authenticated user.
- **Transport**: for a real deployment you'd run this behind HTTPS/WSS
  (e.g. via Nginx + Let's Encrypt) — mention this as a "production
  consideration" in your report, since plain HTTP is fine for a local demo
  but not for production.

## 7. Good "future scope" points for your report

- Swap the keyword-lexicon toxicity detector for a trained model, e.g. a
  scikit-learn TF-IDF + Logistic Regression classifier trained on the
  Jigsaw Toxic Comments dataset, or a HuggingFace model like
  `unitary/toxic-bert`.
- Add end-to-end encryption (encrypt on the client before sending, so even
  the server never sees plaintext) instead of the current server-side
  at-rest encryption.
- Add rate limiting / anomaly detection to flag spam bursts.
- Add an admin view that only moderators can access to review flagged
  messages, instead of broadcasting alerts to the whole room.
- Deploy with HTTPS/WSS and a production DB (PostgreSQL) instead of SQLite.

## 8. Troubleshooting

- **"Could not reach the server"** on login → backend isn't running, or
  `config.js` points to the wrong URL/port.
- **Socket won't connect** → check the browser console; likely an invalid/
  expired JWT — log out and log back in.
- **`ModuleNotFoundError`** → make sure the venv is activated and
  `pip install -r requirements.txt` completed without errors.
- **Messages decrypt to `[DECRYPTION FAILED]`** → the `ENCRYPTION_KEY`
  changed between when the message was saved and now (e.g. you didn't set
  a `.env` file, so a new key was auto-generated on restart).
