# 📊 Portfolio Manager

A local investment portfolio tracker built with **Flask + React**, featuring real-time price updates, evolution charts, P&L analysis, and optional Google Drive sync.

> Interface available in **Romanian and English** — toggle with the 🇬🇧/🇷🇴 button in the header.

---

## ✨ Features

- **Portfolio allocation** — Donut chart by category, region and position
- **Profit / Loss** — Unrealized and realized P&L per position and category, including dividends
- **Evolution chart** — Portfolio value over time with per-category selector (ETFs / Stocks / Bonds / Cash)
- **Live price updates** — Real-time streaming via SSE (Server-Sent Events), with per-position progress
- **Smart source caching** — Remembers the best price source (Stooq / Yahoo Finance / BVB) per ticker; subsequent refreshes go directly to the cached source
- **Dividend tracking** — Record dividends per position, auto-add to Cash balance
- **Buy / Sell positions** — Full transaction history with realized P&L and weighted average price updates
- **Cash positions** — Separate wallet-style display (add / withdraw funds)
- **Google Drive sync** — Optional automatic backup and multi-device sync
- **Bilingual UI** — Romanian / English toggle

### Supported markets

| Market | Ticker format (Stooq) | Examples |
|--------|----------------------|----------|
| US | `symbol.us` | `brkb.us`, `aapl.us`, `nflx.us` |
| UK | `symbol.uk` | `igln.uk`, `cspx.uk`, `copx.uk` |
| Germany | `symbol.de` | `vwce.de`, `eunk.de`, `cebl.de` |
| Romania BVB | `symbol.ro` | `snp.ro`, `tlv.ro`, `h2o.ro` |
| Romania bonds | (no ticker needed) | `R3604AE`, `R2907A`, `Tezaur` |
| France | `symbol.fr` | — |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Mithrutz/PortfolioManager01.git
cd PortfolioManager01

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the app
python app.py
```

Open your browser at **http://localhost:5000**

Edit `portfolio_data.json` with your own positions, or use the app interface to add them one by one.

---

## 🏗️ Build a standalone Windows .exe

To generate a single executable (no Python required on the target machine):

```cmd
build_windows.bat
```

Output: **`dist\PortfolioManager.exe`** — a single file, no installation needed.

Place these two files in the same folder anywhere on your computer:

```
📁 anywhere you want/
   ├── PortfolioManager.exe   ← generated executable
   └── portfolio_data.json    ← your portfolio data
```

> On first launch, Windows may show a security warning → click **"More info" → "Run anyway"**

---

## 📁 File Structure

```
PortfolioManager01/
├── app.py                      # Flask backend (API, price scraping, Drive sync)
├── index.html                  # React frontend (single file, no build tool needed)
├── requirements.txt            # Python dependencies
├── build_windows.bat           # Windows .exe build script
├── portfolio_manager.spec      # PyInstaller config (onefile mode)
├── portfolio_data.json         # Your portfolio data (git-ignored, never published)
├── GOOGLE_DRIVE_SETUP.md       # Step-by-step Google Drive sync guide
├── LICENSE                     # MIT License
└── .gitignore
```

---

## 🔄 Price Sources

Prices are fetched in this order:

1. **Stooq** (`stooq.com`) — primary source for most markets
2. **Yahoo Finance** — fallback for international equities
3. **BVB** (`bvb.ro`) — fallback for Romanian stocks and bonds

After the first successful refresh, the working source is saved in `portfolio_data.json` as `ticker_source`. Subsequent refreshes skip the discovery phase and go directly to the cached source — faster and more reliable.

### Finding the correct ticker

Use the **▶ Test** button in the Edit Position form, or browse [stooq.com/t/](https://stooq.com/t/).

**Ticker format examples:**

```
VWCE  (ETF)          → vwce.de
BRK.B (US Stock)     → brkb.us
IGLN  (UK ETF)       → igln.uk
SNP   (Romania)      → snp.ro
IS04  (Bond ETF)     → is04.de
```

---

## ☁️ Google Drive Sync (optional)

Automatically sync your portfolio across multiple computers.

Full guide: **[GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md)**

**Summary:**
1. Create a free project on [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Google Drive API**
3. Create OAuth credentials → type **Desktop app**
4. Download `credentials.json` → place it next to `app.py` or `.exe`
5. On first launch, a browser window opens for Google login — fully automatic after that

> **Note:** In Testing mode, tokens expire after 7 days. The app handles re-authentication automatically by deleting the old token and opening a new login window.

---

## 📊 Data Storage

All data is stored locally in `portfolio_data.json`:

```json
{
  "cursuri": { "EUR": 1.0, "USD": 1.14, "RON": 5.23 },
  "pozitii": [
    {
      "id": 1,
      "nume": "VWCE",
      "categorie": "ETF-uri",
      "cantitate": 10,
      "pret": 140.0,
      "pret_mediu": 120.0,
      "moneda": "EUR",
      "ticker_stooq": "vwce.de",
      "ticker_source": "stooq",
      "regiune": "World",
      "dividende": []
    }
  ],
  "snapshots": [],
  "tranzactii": []
}
```

**This file is in `.gitignore`** — your financial data never leaves your machine (unless you enable Drive sync).

---

## ⚙️ Managing Your Portfolio

| Action | How |
|--------|-----|
| Add position | **＋ Add** button in the sidebar |
| Edit / fix ticker | ✏️ → **Stooq Ticker** field → **▶ Test** |
| Update prices | **🔄 Update prices** — live progress per position |
| Record dividend | 💰 button per position (optionally auto-adds to Cash) |
| Buy more shares | 🛒 button per position (updates weighted average price) |
| Sell (partial/full) | 💸 button per position (records realized P&L in Cash) |
| Add / withdraw cash | ＋ / — directly from the sidebar Cash position |
| View snapshot history | 📋 History button in the Evolution tab |

---

## ⚠️ Disclaimer

This tool is for **personal tracking purposes only**. Prices retrieved from third-party sources (Stooq, Yahoo Finance, BVB) may be delayed or inaccurate. Do not make financial decisions based solely on this application without independent verification. No warranty is provided.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

[MIT](LICENSE)
