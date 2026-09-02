"""
Portfolio Manager – backend Flask
Rulează: python app.py
Build:   pyinstaller portfolio_manager.spec
Dependințe: pip install flask requests beautifulsoup4 lxml
"""
import json, os, threading, time, sys, re
from flask import Flask, jsonify, request, send_from_directory

# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE SYNC
# Necesita: pip install google-auth-oauthlib google-api-python-client
# Setup o singura data: pune credentials.json langa PortfolioManager.exe
# ══════════════════════════════════════════════════════════════════════════════
DRIVE_SCOPES    = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_FILENAME  = "portfolio_data.json"
DRIVE_FOLDER    = "PortfolioManager"   # folder creat automat in Drive


class DriveSync:
    """
    Sincronizare cu Google Drive folosind REST API direct (requests).
    Nu foloseste google-api-python-client pentru a evita timeout-urile
    la descarcarea discovery document-ului.
    Necesita: google-auth-oauthlib (doar pentru OAuth flow).
    """

    DRIVE_API = "https://www.googleapis.com/drive/v3"
    UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"

    def __init__(self, base_dir):
        self.base_dir   = base_dir
        self.creds_file = os.path.join(base_dir, "credentials.json")
        self.token_file = os.path.join(base_dir, "token.json")
        self.creds      = None
        self.file_id    = None
        self.folder_id  = None
        self.enabled    = os.path.exists(self.creds_file)
        self.last_sync  = None
        self.error      = None

    def _get_creds(self):
        """Obtine/reimprospateza credentialele OAuth. Deschide browserul doar la prima rulare."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as e:
            self.error = f"Instalează: pip install google-auth-oauthlib"
            return None

        def do_auth():
            """Incearca autentificarea. Returneaza credentials sau ridica exceptie."""
            creds = None
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, DRIVE_SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.creds_file, DRIVE_SCOPES
                    )
                    creds = flow.run_local_server(port=0, open_browser=True)
                with open(self.token_file, "w") as f:
                    f.write(creds.to_json())
            return creds

        try:
            creds = do_auth()
            self.creds = creds
            self.error = None
            return creds

        except Exception as e:
            err = str(e)
            # Token expirat/revocat → sterge token.json si reautentifica
            if "invalid_grant" in err or "Token has been expired" in err:
                if os.path.exists(self.token_file):
                    os.remove(self.token_file)
                try:
                    creds = do_auth()
                    self.creds = creds
                    self.error = None
                    return creds
                except Exception as e2:
                    self.error = f"Re-autentificare eșuată: {str(e2)[:80]}"
                    return None

            if "access_denied" in err or "access_blocked" in err.lower():
                self.error = "Acces blocat — adaugă Gmail-ul în Test Users (OAuth consent screen → Audience)"
            elif "invalid_client" in err:
                self.error = "credentials.json invalid — descarcă unul nou din Google Cloud"
            elif "10060" in err or "timed out" in err.lower() or "WinError" in err:
                self.error = "Timeout — verifică Windows Firewall (permite Python/exe)"
            elif "FileNotFoundError" in err or "No such file" in err:
                self.error = "credentials.json negăsit lângă .exe"
            else:
                self.error = f"OAuth: {err[:100]}"
            return None

    def _headers(self):
        """Headers HTTP cu token Bearer."""
        if not self.creds:
            return None
        return {
            "Authorization": f"Bearer {self.creds.token}",
            "Content-Type":  "application/json",
        }

    def _api_get(self, url, params=None):
        """GET catre Drive REST API."""
        import requests as req
        creds = self._get_creds()
        if not creds:
            return None
        try:
            r = req.get(url, headers=self._headers(), params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.error = f"API GET eroare: {str(e)[:80]}"
            return None

    def _get_or_create_folder(self):
        """Gaseste sau creeaza folderul PortfolioManager."""
        import requests as req
        q = f"name='{DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        data = self._api_get(f"{self.DRIVE_API}/files",
                             {"q": q, "fields": "files(id,name)"})
        if data is None:
            return None
        files = data.get("files", [])
        if files:
            return files[0]["id"]
        # Creeaza folderul
        try:
            r = req.post(
                f"{self.DRIVE_API}/files",
                headers=self._headers(),
                json={"name": DRIVE_FOLDER,
                      "mimeType": "application/vnd.google-apps.folder"},
                timeout=15
            )
            r.raise_for_status()
            return r.json()["id"]
        except Exception as e:
            self.error = f"Creare folder: {str(e)[:80]}"
            return None

    def _find_file(self):
        """Cauta portfolio_data.json in Drive."""
        if not self.folder_id:
            return None
        q = f"name='{DRIVE_FILENAME}' and '{self.folder_id}' in parents and trashed=false"
        data = self._api_get(f"{self.DRIVE_API}/files",
                             {"q": q, "fields": "files(id,name,modifiedTime)"})
        if data is None:
            return None
        files = data.get("files", [])
        return files[0] if files else None

    def download(self):
        """Descarca portfolio_data.json din Drive."""
        if not self.enabled:
            return False
        import requests as req
        creds = self._get_creds()
        if not creds:
            return False
        try:
            self.folder_id = self._get_or_create_folder()
            if not self.folder_id:
                return False
            remote = self._find_file()
            if not remote:
                return False      # prima rulare, fisierul nu exista inca
            self.file_id = remote["id"]

            # Compara timpii de modificare
            from datetime import datetime, timezone
            remote_time = datetime.fromisoformat(
                remote["modifiedTime"].replace("Z", "+00:00")
            )
            if os.path.exists(DATA_FILE):
                local_time = datetime.fromtimestamp(
                    os.path.getmtime(DATA_FILE), tz=timezone.utc
                )
                if remote_time <= local_time:
                    self.last_sync = datetime.now().strftime("%H:%M:%S")
                    return True    # local e la zi

            # Download the file
            r = req.get(
                f"{self.DRIVE_API}/files/{self.file_id}",
                headers=self._headers(),
                params={"alt": "media"},
                timeout=30
            )
            r.raise_for_status()
            with open(DATA_FILE, "wb") as f:
                f.write(r.content)
            self.last_sync = datetime.now().strftime("%H:%M:%S")
            self.error = None
            return True

        except Exception as e:
            err = str(e)
            if "10060" in err or "timed out" in err.lower():
                self.error = "Timeout — verifică Windows Firewall (permite Python/exe)"
            else:
                self.error = f"Download: {err[:80]}"
            return False

    def upload(self, local_file=None):
        """Uploadeaza portfolio_data.json pe Drive."""
        if not self.enabled:
            return False
        import requests as req
        local_file = local_file or DATA_FILE
        creds = self._get_creds()
        if not creds:
            return False
        try:
            if not self.folder_id:
                self.folder_id = self._get_or_create_folder()
            if not self.folder_id:
                return False
            if not self.file_id:
                remote = self._find_file()
                self.file_id = remote["id"] if remote else None

            with open(local_file, "rb") as f:
                content = f.read()

            headers_upload = {
                "Authorization": f"Bearer {creds.token}",
                "Content-Type":  "application/json",
            }

            if self.file_id:
                # Update existing file
                r = req.patch(
                    f"{self.UPLOAD_API}/files/{self.file_id}",
                    headers={**headers_upload, "Content-Type": "application/octet-stream"},
                    params={"uploadType": "media"},
                    data=content,
                    timeout=30
                )
            else:
                # Create new file (multipart)
                import email.mime.multipart, email.mime.base, email.mime.application
                meta = json.dumps({
                    "name": DRIVE_FILENAME,
                    "parents": [self.folder_id]
                }).encode()
                boundary = b"--portfolio_boundary"
                body = (
                    boundary + b"\r\n" +
                    b"Content-Type: application/json; charset=UTF-8\r\n\r\n" +
                    meta + b"\r\n" +
                    boundary + b"\r\n" +
                    b"Content-Type: application/json\r\n\r\n" +
                    content + b"\r\n" +
                    boundary + b"--\r\n"
                )
                r = req.post(
                    f"{self.UPLOAD_API}/files",
                    headers={**headers_upload,
                             "Content-Type": "multipart/related; boundary=portfolio_boundary"},
                    params={"uploadType": "multipart", "fields": "id"},
                    data=body,
                    timeout=30
                )
                if r.ok:
                    self.file_id = r.json().get("id")

            r.raise_for_status()
            from datetime import datetime
            self.last_sync = datetime.now().strftime("%H:%M:%S")
            self.error = None
            return True

        except Exception as e:
            err = str(e)
            if "10060" in err or "timed out" in err.lower():
                self.error = "Timeout upload — verifică Windows Firewall (permite Python/exe)"
            else:
                self.error = f"Upload: {err[:80]}"
            return False

    def status(self):
        return {
            "enabled":   self.enabled,
            "connected": self.creds is not None and self.error is None,
            "last_sync": self.last_sync,
            "error":     self.error,
            "file_id":   self.file_id,
        }


# Global instance
_drive = None

def get_drive():
    global _drive
    if _drive is None:
        base = os.path.dirname(sys.executable) if getattr(sys,"frozen",False) \
               else os.path.dirname(os.path.abspath(__file__))
        _drive = DriveSync(base)
    return _drive



def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

def data_path(filename):
    base = os.path.dirname(sys.executable) if getattr(sys,"frozen",False) \
           else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

DATA_FILE = data_path("portfolio_data.json")
app = Flask(__name__, static_folder=None)

# ── Date implicite ─────────────────────────────────────────────────────────────
DEFAULT_DATA = {
    "cursuri": {"EUR": 1.0, "USD": 1.14, "RON": 5.23},
    "pozitii": [
        # ── ETFs / World ──────────────────────────────────────────────────────
        {"id":1,  "nume":"VWCE",     "categorie":"ETF-uri",    "regiune":"World",   "cantitate":25,    "pret":142.80, "pret_mediu":118.40, "moneda":"EUR", "ticker_stooq":"vwce.de",  "dividende":[], "ticker_source":""},
        {"id":2,  "nume":"CSPX",     "categorie":"ETF-uri",    "regiune":"World",   "cantitate":8,     "pret":534.20, "pret_mediu":420.60, "moneda":"USD", "ticker_stooq":"cspx.uk",  "dividende":[], "ticker_source":""},
        {"id":3,  "nume":"EUNK.DE",  "categorie":"ETF-uri",    "regiune":"World",   "cantitate":15,    "pret":104.60, "pret_mediu":88.30,  "moneda":"EUR", "ticker_stooq":"eunk.de",  "dividende":[], "ticker_source":""},
        {"id":4,  "nume":"IGLN",     "categorie":"ETF-uri",    "regiune":"World",   "cantitate":20,    "pret":82.50,  "pret_mediu":68.90,  "moneda":"USD", "ticker_stooq":"igln.uk",  "dividende":[], "ticker_source":""},
        # ── Stocks / World ────────────────────────────────────────────────────
        {"id":5,  "nume":"AAPL",     "categorie":"Acțiuni",   "regiune":"World",   "cantitate":10,    "pret":213.40, "pret_mediu":162.80, "moneda":"USD", "ticker_stooq":"aapl.us",  "dividende":[], "ticker_source":""},
        {"id":6,  "nume":"MSFT",     "categorie":"Acțiuni",   "regiune":"World",   "cantitate":5,     "pret":478.90, "pret_mediu":380.50, "moneda":"USD", "ticker_stooq":"msft.us",  "dividende":[], "ticker_source":""},
        {"id":7,  "nume":"BRK.B",    "categorie":"Acțiuni",   "regiune":"World",   "cantitate":8,     "pret":496.40, "pret_mediu":338.20, "moneda":"USD", "ticker_stooq":"brkb.us",  "dividende":[], "ticker_source":""},
        # ── Stocks / Romania ──────────────────────────────────────────────────
        {"id":8,  "nume":"SNP",      "categorie":"Acțiuni",   "regiune":"România", "cantitate":5000,  "pret":1.248,  "pret_mediu":0.820,  "moneda":"RON", "ticker_stooq":"snp.ro",   "dividende":[], "ticker_source":""},
        {"id":9,  "nume":"TLV",      "categorie":"Acțiuni",   "regiune":"România", "cantitate":120,   "pret":42.60,  "pret_mediu":22.40,  "moneda":"RON", "ticker_stooq":"tlv.ro",   "dividende":[], "ticker_source":""},
        # ── Bonds / Romania ───────────────────────────────────────────────────
        {"id":10, "nume":"R3604AE",  "categorie":"Obligațiuni","regiune":"România", "cantitate":50,    "pret":101.20, "pret_mediu":100.0,  "moneda":"EUR", "ticker_stooq":"",         "dividende":[], "ticker_source":""},
        {"id":11, "nume":"Tezaur",   "categorie":"Obligațiuni","regiune":"România", "cantitate":1000,  "pret":100.00, "pret_mediu":100.0,  "moneda":"RON", "ticker_stooq":"",         "dividende":[], "ticker_source":""},
        # ── Crypto ────────────────────────────────────────────────────────────
        {"id":12, "nume":"Bitcoin",  "categorie":"Crypto",     "regiune":"World",   "cantitate":0.1,   "pret":77200,  "pret_mediu":74000,  "moneda":"USD", "ticker_stooq":"BTC-USD",  "dividende":[], "ticker_source":"yahoo"},
        # ── Cash ──────────────────────────────────────────────────────────────
        {"id":13, "nume":"Cash EUR", "categorie":"Cash",        "regiune":"World",   "cantitate":1,     "pret":3500.0, "pret_mediu":3500.0, "moneda":"EUR", "ticker_stooq":"",         "dividende":[], "ticker_source":""},
        {"id":14, "nume":"Cash USD", "categorie":"Cash",        "regiune":"World",   "cantitate":1,     "pret":1200.0, "pret_mediu":1200.0, "moneda":"USD", "ticker_stooq":"",         "dividende":[], "ticker_source":""},
        {"id":15, "nume":"Cash RON", "categorie":"Cash",        "regiune":"România", "cantitate":1,     "pret":8400.0, "pret_mediu":8400.0, "moneda":"RON", "ticker_stooq":"",         "dividende":[], "ticker_source":""},
    ],
    "next_id": 16,
}

CAT_MIGRATE = {
    "Acțiuni individuale": "Acțiuni",
    "Obligațiuni de stat":  "Obligațiuni",
}

def migrate(data):
    changed = False
    for p in data.get("pozitii", []):
        if p.get("categorie") in CAT_MIGRATE:
            p["categorie"] = CAT_MIGRATE[p["categorie"]]
            changed = True
        for field, default in [("pret_mediu", p.get("pret",0)),
                                ("regiune", "World"),
                                ("ticker_stooq", p.get("ticker_yf","")),
                                ("dividende", []),
                                ("ticker_source", "")]:
            if field not in p:
                p[field] = default
                changed = True
        # sterge campul vechi ticker_yf daca exista
        if "ticker_yf" in p:
            if not p.get("ticker_stooq"):
                p["ticker_stooq"] = p["ticker_yf"]
            del p["ticker_yf"]
            changed = True
    return data, changed

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data, changed = migrate(data)
        if changed:
            save_data(data)
        return data
    return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    if "snapshots" not in data:
        data["snapshots"] = []
    if "tranzactii" not in data:
        data["tranzactii"] = []
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Upload to Drive in background (non-blocking)
    drive = get_drive()
    if drive.enabled:
        threading.Thread(target=drive.upload, daemon=True).start()

def save_snapshot(data, cursuri):
    """Salveaza un snapshot zilnic al valorii portofoliului in EUR."""
    from datetime import date as dt_date
    today = str(dt_date.today())
    snapshots = data.setdefault("snapshots", [])

    # Calculate current values
    def to_eur(v, m):
        return v / (cursuri.get(m) or 1.0)

    total = 0.0
    categorii = {}
    for p in data.get("pozitii", []):
        val = to_eur(p["cantitate"] * p["pret"], p["moneda"])
        total += val
        cat = p.get("categorie", "Altele")
        categorii[cat] = categorii.get(cat, 0.0) + val

    snapshot = {
        "data": today,
        "total_eur": round(total, 2),
        "categorii": {k: round(v, 2) for k, v in categorii.items()},
        "cursuri": {"USD": cursuri.get("USD", 1.16), "RON": cursuri.get("RON", 5.23)}
    }

    # Replace today's snapshot if it already exists
    existing = [s for s in snapshots if s["data"] != today]
    existing.append(snapshot)
    existing.sort(key=lambda s: s["data"])
    data["snapshots"] = existing
    save_data(data)
    return snapshot


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPING
# ══════════════════════════════════════════════════════════════════════════════
import urllib.request, urllib.error

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}


# ── 1. STOOQ HTML scraping ───────────────────────────────────────────────────
def get_stooq(ticker_stooq):
    """
    Scraping pagina HTML Stooq: https://stooq.com/q/?s={ticker}
    Incearca multiple variante de ID si regex ca fallback.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        import re as _re
    except ImportError:
        return None, "Lipsesc librarii: pip install requests beautifulsoup4 lxml"

    ticker = ticker_stooq.lower().strip()
    url    = f"https://stooq.com/q/?s={ticker}"
    try:
        sess = requests.Session()
        sess.headers.update({**HEADERS_BASE, "Referer": "https://stooq.com/"})
        r = sess.get(url, timeout=12)
        r.raise_for_status()
        html = r.text

        # Stooq returneaza pagina de eroare daca ticker-ul nu exista
        if "No data" in html or "nie istnieje" in html or "does not exist" in html.lower():
            return None, f"Ticker '{ticker}' nu există pe Stooq"

        soup = BeautifulSoup(html, "lxml")

        # Incercam mai multe variante de ID (cu punct, cu underscore, fara separator)
        variants = [ticker, ticker.replace(".", "_"), ticker.replace(".", "")]
        for tv in variants:
            el = soup.find(id=f"aq_{tv}_l1")
            if el:
                txt = el.get_text(strip=True).replace(",","").replace(" ","")
                if txt and txt not in ("N/D","-","","0"):
                    try:
                        return round(float(txt), 4), f"Stooq/{ticker}"
                    except ValueError:
                        pass

        # Orice td cu _l1 in id
        for td in soup.find_all("td", id=True):
            if "_l1" in td.get("id",""):
                txt = td.get_text(strip=True).replace(",","").replace(" ","")
                if txt and txt not in ("N/D","-","","0"):
                    try:
                        val = float(txt)
                        if val > 0:
                            return round(val, 4), f"Stooq/{ticker} (td/_l1)"
                    except ValueError:
                        pass

        # Regex direct in HTML sursa
        m = _re.search(r'id="aq_[^"]+_l1"[^>]*>\s*([0-9]+[.,][0-9]+)', html)
        if m:
            try:
                return round(float(m.group(1).replace(",",".")), 4), f"Stooq/{ticker} (regex)"
            except ValueError:
                pass

        return None, f"Preț negăsit în HTML Stooq pentru '{ticker}' (posibil JS-rendered)"

    except requests.exceptions.HTTPError as e:
        return None, f"Stooq HTTP {e.response.status_code} pentru '{ticker}'"
    except requests.exceptions.ConnectionError:
        return None, "Fără conexiune la stooq.com"
    except requests.exceptions.Timeout:
        return None, "Timeout stooq.com (>12s)"
    except Exception as e:
        return None, f"Stooq eroare: {str(e)[:80]}"


# ── 1b. YFINANCE (fallback World) ─────────────────────────────────────────────
# Mapare automata ticker comun → Yahoo Finance symbol
_YF_MAP = {
    # London ETFs  (.uk → .L pe Yahoo)
    ".uk": lambda s: s[:-3].upper() + ".L",
    # Frankfurt    (.de → .DE pe Yahoo)
    ".de": lambda s: s[:-3].upper() + ".DE",
    # Romania      (.ro → .RO pe Yahoo)
    ".ro": lambda s: s[:-3].upper() + ".RO",
    # US           (.us → fara sufix pe Yahoo, cu - in loc de .)
    ".us": lambda s: s[:-3].upper().replace(".", "-"),
}

def ticker_to_yf(ticker_stooq):
    """Converteste ticker stooq in ticker Yahoo Finance."""
    t = ticker_stooq.lower().strip()
    for suf, fn in _YF_MAP.items():
        if t.endswith(suf):
            return fn(t)
    return ticker_stooq.upper()

def get_yfinance(ticker_stooq):
    """
    Fallback via yfinance (Yahoo Finance).
    Converteste automat ticker-ul Stooq in format Yahoo.
    """
    try:
        import yfinance as yf
    except ImportError:
        return None, "yfinance nu e instalat: pip install yfinance"

    yf_ticker = ticker_to_yf(ticker_stooq)
    try:
        info  = yf.Ticker(yf_ticker).fast_info
        price = info.get("lastPrice") or info.get("regularMarketPrice")
        if price is None or float(price) == 0:
            return None, f"Yahoo returnează preț null pentru {yf_ticker}"
        return round(float(price), 4), f"Yahoo/{yf_ticker}"
    except Exception as e:
        return None, f"Yahoo/{yf_ticker}: {str(e)[:80]}"


# ── 2. BVB.ro scraping ────────────────────────────────────────────────────────
# ── 2. BVB.ro scraping ────────────────────────────────────────────────────────
def get_bvb(simbol):
    """
    Preia pretul de pe BVB pentru actiuni si obligatiuni romanesti.
    Incearca: 1) Stooq .ro  2) BVB scraping  3) fallback 100 pt obligatiuni Fidelis
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return None, "requests/bs4 lipsesc"

    simbol_up = simbol.upper().strip()

    # 1. Incearca Stooq cu extensia .ro (functioneaza pt SNP, TLV, H2O, R3604AE etc.)
    stooq_t = simbol.lower().strip() + ".ro"
    try:
        url = "https://stooq.com/q/l/?s={}&f=sd2t2ohlcv&h&e=csv".format(stooq_t)
        r = requests.get(url, headers=HEADERS_BASE, timeout=8)
        if r.status_code == 200:
            lines = r.text.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split(",")
                if len(parts) >= 5 and parts[4] not in ("N/D","0",""):
                    return round(float(parts[4]), 4), "Stooq ({})".format(stooq_t)
    except Exception:
        pass

    # 2. BVB scraping with session ASP.NET
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        session.get("https://www.bvb.ro", timeout=5)
        time.sleep(0.3)
        url = "https://www.bvb.ro/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx?s={}".format(simbol_up)
        r = session.get(url, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            # Selectori in ordinea probabilitatii
            for sel in [
                {"id": re.compile(r"LastPrice|CurrentPrice|PretCurent", re.I)},
                {"class": re.compile(r"last.?price|current.?price|pret.?curent", re.I)},
            ]:
                el = soup.find(["span","td","div","p"], sel)
                if el:
                    txt = el.get_text(strip=True).replace(",",".").replace(" ","")
                    m = re.search(r"(\d+\.?\d*)", txt)
                    if m:
                        try:
                            val = round(float(m.group(1)), 4)
                            if val > 0:
                                return val, "BVB ({})".format(simbol_up)
                        except ValueError:
                            pass
            # Cauta numere in range tipic de obligatiune (90-115)
            for el in soup.find_all(["span","td"], limit=400):
                txt = el.get_text(strip=True).replace(",",".")
                try:
                    val = float(txt)
                    if 85.0 <= val <= 115.0:
                        return round(val, 4), "BVB ({})".format(simbol_up)
                except (ValueError, AttributeError):
                    pass
    except Exception:
        pass

    # 3. Fallback obligatiuni Fidelis/Tezaur — pret nominal 100
    if re.match(r"^R\d{4}[A-Z]{1,2}$", simbol_up, re.I) or simbol_up in ("TEZAUR","TEZAUR7","TEZAUR75"):
        return 100.0, "Nominal ({}) — pret neactualizat".format(simbol_up)

    return None, "Negasit BVB ({})".format(simbol_up)


def get_tradeville(simbol):
    """
    Fallback suplimentar pentru acțiuni românești.
    Returnează (pret_float, sursa) sau (None, eroare)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return None, "requests/beautifulsoup4 nu sunt instalate"

    url = f"https://www.tradeville.ro/actiuni/actiuni-{simbol.upper()}"
    try:
        session = requests.Session()
        session.headers.update(HEADERS_BASE)
        r = session.get(url, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # Tradeville shows price in specific CSS classes
        for sel in [
            {"class": re.compile(r"pret|price|cotatie|last", re.I)},
            {"id":    re.compile(r"pret|price|last",          re.I)},
        ]:
            el = soup.find(["span","div","td","strong"], sel)
            if el:
                txt = el.get_text(strip=True).replace(",",".").replace(" ","").split()[0]
                try:
                    val = float(re.sub(r"[^\d.]", "", txt))
                    if val > 0:
                        return round(val, 4), f"Tradeville ({simbol})"
                except ValueError:
                    continue

        return None, "Element preț negăsit pe Tradeville"
    except Exception as e:
        return None, f"Tradeville eroare: {str(e)[:60]}"


# ── 4. Cursuri valutare ────────────────────────────────────────────────────────
def get_cursuri():
    """
    Preia EUR/USD și EUR/RON de la frankfurter.app (gratuit, fără cheie).
    """
    try:
        url = "https://api.frankfurter.app/latest?from=EUR&to=USD,RON"
        req = urllib.request.Request(url, headers=HEADERS_BASE)
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        return {
            "EUR": 1.0,
            "USD": round(data["rates"]["USD"], 4),
            "RON": round(data["rates"]["RON"], 4),
            "data": data.get("date",""),
        }
    except Exception as e:
        return {"error": str(e)[:80]}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory(resource_path("."), "index.html")

@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(load_data())

@app.route("/api/data", methods=["POST"])
def set_data():
    new_data = request.get_json()
    # Preserve ticker_source from existing file
    # (frontend does not manage this field — only backend writes it)
    try:
        existing = load_data()
        src_map = {p["id"]: p.get("ticker_source", "")
                   for p in existing.get("pozitii", [])}
        for p in new_data.get("pozitii", []):
            if not p.get("ticker_source") and p.get("id") in src_map:
                p["ticker_source"] = src_map[p["id"]]
    except Exception:
        pass
    save_data(new_data)
    return jsonify({"ok": True})


@app.route("/api/refresh-prices", methods=["POST"])
def refresh_prices():
    pozitii  = request.get_json().get("pozitii", [])
    rezultate = []

    # ── Cursuri valutare ────────────────────────────────────────────────────
    cursuri_live = get_cursuri()

    # ── Prices per position ──────────────────────────────────────────────────
    for p in pozitii:
        ticker  = (p.get("ticker_stooq") or "").strip()
        regiune = p.get("regiune", "World")
        entry = {
            "id":         p["id"],
            "nume":       p["nume"],
            "regiune":    regiune,
            "pret_vechi": p.get("pret", 0),
            "moneda":     p.get("moneda","EUR"),
            "ticker_stooq": ticker,
        }

        ticker = normalize_stooq(ticker, regiune) if ticker else ticker
        entry['ticker_stooq'] = ticker  # ticker normalizat
        if not ticker:
            entry.update(status="manual", pret_nou=None,
                         mesaj="Fără ticker — actualizare manuală", sursa="—")
        else:
            # ── 1. Stooq HTML (primar, ambele regiuni) ───────────────
            pret, sursa = get_stooq(ticker)

            # ── 2. Fallback World → yfinance ─────────────────────────────
            if pret is None and regiune == "World":
                pret2, sursa2 = get_yfinance(ticker)
                if pret2 is not None:
                    pret, sursa = pret2, sursa2
                else:
                    sursa = f"Stooq: {sursa} | Yahoo: {sursa2}"

            # ── 3. Fallback Romania → yfinance (.RO) → BVB → Tradeville ──
            if pret is None and regiune == "România":
                # yfinance stie SNP.RO, TLV.RO, H2O.RO etc.
                pret2, sursa2 = get_yfinance(ticker)
                if pret2 is not None:
                    pret, sursa = pret2, sursa2
                else:
                    simbol = ticker.replace(".ro","").replace(".RO","").upper()
                    pret3, sursa3 = get_bvb(simbol)
                    if pret3 is not None:
                        pret, sursa = pret3, sursa3
                    else:
                        pret4, sursa4 = get_tradeville(simbol)
                        if pret4 is not None:
                            pret, sursa = pret4, sursa4
                        else:
                            sursa = f"Stooq: {sursa} | Yahoo: {sursa2} | BVB: {sursa3} | Tradeville: {sursa4}"

            if pret is not None:
                entry.update(status="ok", pret_nou=pret,
                             sursa=sursa, mesaj=sursa)
            else:
                entry.update(status="eroare", pret_nou=None,
                             sursa="—", mesaj=sursa[:120])

        rezultate.append(entry)
        time.sleep(0.2)

    # Auto-save snapshot dupa refresh reusit
    try:
        data = load_data()
        final_cursuri = cursuri_live if not cursuri_live.get("error") else data.get("cursuri", {})
        save_snapshot(data, final_cursuri)
    except Exception:
        pass

    return jsonify({"rezultate": rezultate, "cursuri_live": cursuri_live})


# ── Normalizare ticker Stooq ──────────────────────────────────────────────────
def normalize_stooq(ticker, regiune="World"):
    """
    Normalizeaza ticker-ul pentru Stooq.
    Detecteaza format Yahoo Finance (BTC-USD, ETH-USD) si le pastreaza neschimbate
    pentru a fi procesate de Yahoo Finance, nu Stooq.
    """
    t = ticker.strip()
    tl = t.lower()

    # Detect Yahoo Finance format: XXX-USD, XXX-EUR, XXX-BTC etc.
    # These are NOT sent to Stooq, but to Yahoo Finance
    import re as _re
    if _re.match(r'^[A-Za-z0-9]+-(USD|EUR|GBP|BTC|ETH|USDT|USDC)$', t, _re.I):
        return t  # return unchanged — will be processed by Yahoo Finance

    return tl   # stooq uses lowercase


def test_ticker():
    """Testeaza un ticker: Stooq → yfinance (World) sau BVB/Tradeville (Romania)."""
    body    = request.get_json()
    ticker  = (body.get("ticker") or "").strip().lower()
    regiune = body.get("regiune", "World")

    if not ticker:
        return jsonify({"ok": False, "mesaj": "Ticker gol"})

    pret, sursa = get_stooq(ticker)

    # Stooq a esuat — incearca ticker normalizat
    if pret is None:
        tn = normalize_stooq(ticker, regiune)
        if tn != ticker:
            p2, s2 = get_stooq(tn)
            if p2 is not None:
                return jsonify({"ok": True, "pret": p2, "sursa": s2,
                                "ticker_sugerat": tn,
                                "mesaj": f"Gasit ca {tn} -> {p2}"})

    # Fallback World → yfinance
    if pret is None and regiune == "World":
        p_yf, s_yf = get_yfinance(ticker)
        if p_yf is not None:
            return jsonify({"ok": True, "pret": p_yf, "sursa": s_yf,
                            "mesaj": f"Yahoo Finance ({ticker_to_yf(ticker)}) -> {p_yf}"})
        sursa = f"Stooq: {sursa} | Yahoo: {s_yf}"

    # Fallback Romania → yfinance → BVB → Tradeville
    if pret is None and (regiune == "Romania" or regiune == "România"):
        p_yf, s_yf = get_yfinance(ticker)
        if p_yf is not None:
            return jsonify({"ok": True, "pret": p_yf, "sursa": s_yf,
                            "mesaj": f"Yahoo Finance ({ticker_to_yf(ticker)}) -> {p_yf}"})
        simbol = ticker.replace(".ro","").upper()
        p_b, s_b = get_bvb(simbol)
        if p_b is None:
            p_b, s_b = get_tradeville(simbol)
        if p_b is not None:
            return jsonify({"ok": True, "pret": p_b, "sursa": s_b,
                            "mesaj": f"{s_b} -> {p_b}"})
        sursa = f"Stooq: {sursa} | Yahoo: {s_yf} | BVB+Tradeville: indisponibile"

    if pret is not None:
        return jsonify({"ok": True, "pret": pret, "sursa": sursa,
                        "mesaj": f"{sursa} -> {pret}"})

    tn = normalize_stooq(ticker, regiune)
    return jsonify({"ok": False, "mesaj": sursa, "ticker_sugerat": tn,
                    "mesaj_hint": f"Format sugerat: {tn}"})



@app.route("/api/snapshots", methods=["GET"])
def get_snapshots():
    data = load_data()
    return jsonify(data.get("snapshots", []))

@app.route("/api/snapshots", methods=["POST"])
def add_snapshot():
    """Adauga manual un snapshot sau auto-save dupa refresh."""
    body = request.get_json() or {}
    data = load_data()
    cursuri = body.get("cursuri") or data.get("cursuri", {"EUR":1,"USD":1.16,"RON":5.23})
    snap = save_snapshot(data, cursuri)
    return jsonify({"ok": True, "snapshot": snap})

@app.route("/api/snapshots/<string:data_str>", methods=["DELETE"])
def delete_snapshot(data_str):
    data = load_data()
    data["snapshots"] = [s for s in data.get("snapshots",[]) if s["data"] != data_str]
    save_data(data)
    return jsonify({"ok": True})


@app.route("/api/drive/diagnose", methods=["GET"])
def drive_diagnose():
    """Diagnosticare detaliata pentru Google Drive."""
    import sys, platform
    result = {
        "platform": platform.system(),
        "python": sys.version,
        "frozen": getattr(sys, "frozen", False),
        "base_dir": data_path(""),
        "credentials_exists": os.path.exists(data_path("credentials.json")),
        "token_exists": os.path.exists(data_path("token.json")),
        "libraries": {}
    }
    # Check libraries
    for lib in ["google.auth", "google_auth_oauthlib", "googleapiclient", "httplib2"]:
        try:
            __import__(lib.replace("-","_"))
            result["libraries"][lib] = "OK"
        except ImportError as e:
            result["libraries"][lib] = f"LIPSESTE: {e}"
    # Check drive status
    drive = get_drive()
    result["drive_enabled"]   = drive.enabled
    result["drive_error"]     = drive.error
    result["drive_last_sync"] = drive.last_sync
    result["drive_file_id"]   = drive.file_id
    return jsonify(result)


@app.route("/api/drive/status", methods=["GET"])
def drive_status():
    return jsonify(get_drive().status())

@app.route("/api/drive/sync", methods=["POST"])
def drive_sync():
    """Sync manual: download (default) sau upload explicit."""
    drive = get_drive()
    if not drive.enabled:
        return jsonify({"ok": False, "mesaj": "Google Drive nu e configurat (lipsește credentials.json)"})
    body  = request.get_json(silent=True) or {}
    action = body.get("action", "download")   # "download" sau "upload"
    if action == "upload":
        ok = drive.upload()
        mesaj = "Date uploadate în Drive ✓" if ok else (drive.error or "Upload eșuat")
    else:
        ok = drive.download()
        mesaj = "Date sincronizate din Drive ✓" if ok else (drive.error or "Download eșuat")
    return jsonify({"ok": ok, "status": drive.status(), "mesaj": mesaj})


@app.route("/api/refresh-prices/stream")
def refresh_prices_stream():
    """SSE endpoint: trimite progress live pentru fiecare pozitie."""
    from flask import Response, stream_with_context

    def generate():
        data_local   = load_data()
        pozitii_list = data_local.get("pozitii", [])
        total        = len(pozitii_list)
        cursuri_live = {}
        try:
            cursuri_live = get_cursuri()
        except Exception:
            pass

        msg_start = json.dumps({"type": "start", "total": total})
        yield "data: " + msg_start + "\n\n"

        rezultate = []
        for i, p in enumerate(pozitii_list):
            ticker  = (p.get("ticker_stooq") or "").strip()
            regiune = p.get("regiune", "World")
            if ticker:
                ticker = normalize_stooq(ticker, regiune)

            entry = {
                "type":        "progress",
                "index":       i,
                "total":       total,
                "id":          p["id"],
                "nume":        p["nume"],
                "moneda":      p.get("moneda", "EUR"),
                "pret_vechi":  p.get("pret", 0),
                "ticker_stooq": ticker,
                "regiune":     regiune,
            }

            if not ticker:
                entry.update(status="manual", pret_nou=None, mesaj="—")
            else:
                cached_source = (p.get("ticker_source") or "").strip()
                pret, sursa, new_source = None, "", cached_source

                def try_stooq():
                    pr, sr = get_stooq(ticker)
                    return pr, sr, "stooq" if pr else ""

                def try_yahoo():
                    pr, sr = get_yfinance(ticker)
                    return pr, sr, "yahoo" if pr else ""

                def try_bvb():
                    simbol = ticker.replace(".ro", "").upper()
                    pr, sr = get_bvb(simbol)
                    return pr, sr, "bvb" if pr else ""

                # Yahoo Finance format tickers (BTC-USD, ETH-EUR etc.) → go direct to Yahoo
                import re as _re2
                is_yahoo_format = bool(_re2.match(
                    r'^[A-Za-z0-9]+-(USD|EUR|GBP|BTC|ETH|USDT|USDC)$', ticker, _re2.I))

                if is_yahoo_format:
                    pret, sursa, new_source = try_yahoo()
                elif cached_source == "stooq":
                    pret, sursa, new_source = try_stooq()
                    if not pret:  # cached source failed, re-discovering
                        pret, sursa, new_source = try_yahoo()
                    if not pret and regiune != "World":
                        pret, sursa, new_source = try_bvb()

                elif cached_source == "yahoo":
                    pret, sursa, new_source = try_yahoo()
                    if not pret:
                        pret, sursa, new_source = try_stooq()
                    if not pret and regiune != "World":
                        pret, sursa, new_source = try_bvb()

                elif cached_source == "bvb":
                    pret, sursa, new_source = try_bvb()
                    if not pret:
                        pret, sursa, new_source = try_stooq()
                    if not pret:
                        pret, sursa, new_source = try_yahoo()

                else:
                    # First run — discover optimal source
                    pret, sursa, new_source = try_stooq()
                    if not pret and regiune == "World":
                        pret, sursa, new_source = try_yahoo()
                    elif not pret:
                        p2, s2, src2 = try_yahoo()
                        if p2:
                            pret, sursa, new_source = p2, s2, src2
                        else:
                            pret, sursa, new_source = try_bvb()

                if pret is not None:
                    entry.update(status="ok", pret_nou=pret, mesaj=str(sursa),
                                 source_used=new_source,
                                 source_cached=cached_source == new_source)
                    d2 = load_data()
                    for poz in d2.get("pozitii", []):
                        if poz["id"] == p["id"]:
                            poz["pret"] = pret
                            if new_source:
                                poz["ticker_source"] = new_source
                            break
                    save_data(d2)
                else:
                    entry.update(status="eroare", pret_nou=None, mesaj=str(sursa or "")[:80])

            rezultate.append(entry)
            yield "data: " + json.dumps(entry) + "\n\n"
            time.sleep(0.15)

        # Auto-save snapshot
        try:
            d3 = load_data()
            save_snapshot(d3, cursuri_live if not cursuri_live.get("error") else d3.get("cursuri", {}))
        except Exception:
            pass

        n_ok = sum(1 for r in rezultate if r.get("status") == "ok")
        msg_done = json.dumps({"type": "done", "cursuri_live": cursuri_live,
                               "n_ok": n_ok, "n_total": total})
        yield "data: " + msg_done + "\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/api/test-ticker", methods=["POST"])
def test_ticker():
    """Testeaza un ticker: Stooq → Yahoo Finance → BVB."""
    import re as _re
    body    = request.get_json() or {}
    ticker  = (body.get("ticker") or "").strip()
    regiune = body.get("regiune", "World")

    if not ticker:
        return jsonify({"ok": False, "pret": None, "eroare": "Ticker gol"})

    moneda = "EUR"
    pret, sursa = None, ""

    # Detecteaza format Yahoo Finance: BTC-USD, ETH-EUR etc.
    is_yahoo_fmt = bool(_re.match(
        r"^[A-Za-z0-9]+-( USD|EUR|GBP|BTC|ETH|USDT|USDC)$".replace(" ",""),
        ticker, _re.I))

    if is_yahoo_fmt:
        # Go directly to Yahoo Finance
        pret, sursa = get_yfinance(ticker)
        moneda = "USD" if ticker.upper().endswith("-USD") else                  "EUR" if ticker.upper().endswith("-EUR") else "USD"
        src_key = "yahoo" if pret else ""
    else:
        ticker_norm = normalize_stooq(ticker, regiune)
        # Detect currency from ticker extension
        if ".de" in ticker_norm or ".fr" in ticker_norm:
            moneda = "EUR"
        elif ".ro" in ticker_norm:
            moneda = "RON"
        else:
            moneda = "USD"

        pret, sursa = get_stooq(ticker_norm)
        src_key = "stooq" if pret else ""

        if not pret and regiune == "World":
            pret, sursa = get_yfinance(ticker_norm)
            src_key = "yahoo" if pret else ""

        if not pret and regiune != "World":
            simbol = ticker_norm.replace(".ro","").upper()
            pret, sursa = get_bvb(simbol)
            src_key = "bvb" if pret else ""
            moneda = "RON"

    if pret is not None:
        return jsonify({"ok": True, "pret": pret, "sursa": sursa,
                        "moneda": moneda, "source_key": src_key})
    return jsonify({"ok": False, "pret": None,
                    "eroare": "Ticker negăsit — verifică formatul (ex: brkb.us · snp.ro · BTC-USD)"})


@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    """Opreste serverul complet — inclusiv procesul PyInstaller exe."""
    import threading
    t = threading.Timer(0.5, lambda: os._exit(0))
    t.daemon = True
    t.start()
    return jsonify({"ok": True})



# ── Start ──────────────────────────────────────────────────────────────────────
def run_flask():
    """Porneste Flask intr-un thread separat."""
    app.run(debug=False, port=5000, use_reloader=False, threaded=True)

def sync_on_startup():
    """Incearca sa descarce datele din Drive la pornire."""
    time.sleep(2)   # wait for Flask to start
    drive = get_drive()
    if drive.enabled:
        print("[Drive] Se verifică datele din cloud...")
        ok = drive.download()
        if ok:
            print("[Drive] Date sincronizate din Google Drive ✓")
        else:
            print(f"[Drive] Sync eșuat: {drive.error}")

if __name__ == "__main__":
    try:
        import webview

        # Porneste Flask in background
        t = threading.Thread(target=run_flask, daemon=True)
        t.start()
        # Sync Drive in background
        threading.Thread(target=sync_on_startup, daemon=True).start()
        time.sleep(1.2)   # wait for Flask to start

        # Deschide fereastra GUI nativa
        window = webview.create_window(
            title    = "Portfolio Manager",
            url      = "http://localhost:5000",
            width    = 1440,
            height   = 900,
            min_size = (900, 600),
            resizable= True,
        )
        # La inchiderea ferestrei, opreste tot
        webview.start()
        os._exit(0)

    except ImportError:
        # Fallback la browser daca pywebview nu e instalat
        print("\n╔══════════════════════════════════════════╗")
        print("║   Portfolio Manager  →  localhost:5000   ║")
        print("║   pywebview negăsit → se deschide browser║")
        print("╚══════════════════════════════════════════╝\n")
        threading.Thread(
            target=lambda: (time.sleep(1.4),
                            __import__("webbrowser").open("http://localhost:5000")),
            daemon=True
        ).start()
        app.run(debug=False, port=5000, use_reloader=False)
