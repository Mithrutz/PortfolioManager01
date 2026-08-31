# 📊 Portfolio Manager

A local investment portfolio tracker built with **Flask + React**, featuring real-time price updates, evolution charts, P&L analysis, and optional Google Drive sync.

> 🇷🇴 Interface available in **Romanian and English** — toggle with the 🇬🇧/🇷🇴 button in the header.

---

## ✨ Features

- **Portfolio overview** — Donut allocation chart (by category, region, position)
- **P&L analysis** — Unrealized and realized gains/losses per position and category
- **Evolution chart** — Portfolio value over time with per-category selector
- **Live price updates** — Real-time streaming via SSE (Server-Sent Events), with progress per position
- **Smart source caching** — Remembers the best price source (Stooq / Yahoo Finance / BVB) per ticker, skips retrying on subsequent refreshes
- **Dividend tracking** — Record dividends per position, auto-add to Cash balance
- **Buy / Sell positions** — Full transaction history with realized P&L
- **Cash positions** — Separate wallet-style display (add/withdraw funds)
- **Google Drive sync** — Optional automatic backup and multi-device sync
- **Bilingual UI** — Romanian / English toggle

### Supported markets
| Market | Ticker format (Stooq) | Example |
|--------|----------------------|---------|
| US     | `symbol.us`          | `brkb.us`, `aapl.us` |
| UK     | `symbol.uk`          | `igln.uk`, `cspx.uk` |
| Germany| `symbol.de`          | `vwce.de`, `eunk.de` |
| Romania BVB | `symbol.ro`     | `snp.ro`, `tlv.ro` |
| Romania bonds | (no ticker) | `R3604AE`, `Tezaur` |
| France | `symbol.fr`          | — |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/portfolio-manager.git
cd portfolio-manager

pip install -r requirements.txt
```

### Configure your portfolio

```bash
cp portfolio_data.example.json portfolio_data.json
```

Edit `portfolio_data.json` and replace the example positions with your own.

### Run

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## 📁 File Structure

```
portfolio-manager/
├── app.py                        # Flask backend
├── index.html                    # React frontend (single file)
├── requirements.txt              # Python dependencies
├── portfolio_data.example.json   # Example data — copy to portfolio_data.json
├── portfolio_data.json           # Your data (git-ignored, never committed)
├── GOOGLE_DRIVE_SETUP.md         # Google Drive sync guide
└── .gitignore
```

---

## 🔄 Price Sources & Ticker Format

Prices are fetched in this order:
1. **Stooq** (`stooq.com`) — primary source for most markets
2. **Yahoo Finance** — fallback for World equities
3. **BVB** (`bvb.ro`) — fallback for Romanian stocks and bonds

After the first successful refresh, the working source is cached in `portfolio_data.json` as `ticker_source`. Subsequent refreshes go directly to the cached source — no retrying.

To find the correct Stooq ticker for a position, use the **▶ Testează** button in the Edit Position form, or browse [stooq.com/t/](https://stooq.com/t/).

---

## ☁️ Google Drive Sync (optional)

Sync your portfolio across multiple computers automatically.

See **[GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md)** for the full step-by-step guide.

**Summary:**
1. Create a free project on [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Google Drive API**
3. Create OAuth credentials → **Desktop app** type
4. Download `credentials.json` → place it next to `app.py`
5. On first run, your browser opens for Google login — then it's automatic

> **Note:** For personal use, keep the app in *Testing* mode. Tokens expire after 7 days — the app handles re-authentication automatically.

---

## 🏗️ Build a standalone Windows .exe

```bash
pip install pyinstaller pywebview
pyinstaller --onedir --windowed --name PortfolioManager app.py
```

Or use the included batch file:
```cmd
build_windows.bat
```

Copy `portfolio_data.json` next to the generated `PortfolioManager.exe`.

---

## 📊 Data Storage

All data is stored locally in `portfolio_data.json`:

```json
{
  "cursuri": { "EUR": 1.0, "USD": 1.14, "RON": 5.23 },
  "pozitii": [ ... ],
  "snapshots": [ ... ],
  "tranzactii": [ ... ]
}
```

**This file is git-ignored** — your financial data never leaves your machine (unless you enable Drive sync).

---

## ⚠️ Disclaimer

This tool is for **personal tracking only**. Prices from third-party sources (Stooq, Yahoo Finance) may be delayed or inaccurate. Do not use this for financial decisions without verifying data independently. No warranty is provided.

---

## 🤝 Contributing

Pull requests welcome. For major changes, open an issue first.

---

## 📄 License

[MIT](LICENSE)
