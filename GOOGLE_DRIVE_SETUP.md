# Configurare Google Drive Sync
## Ghid pas cu pas (durează ~10 minute, o singură dată)

---

## Pasul 1 — Creează un proiect Google Cloud

1. Mergi la https://console.cloud.google.com
2. Click pe **"Select a project"** → **"New Project"**
3. Nume proiect: `PortfolioManager` → **Create**
4. Asigură-te că proiectul nou e selectat în bara de sus

---

## Pasul 2 — Activează Google Drive API

1. În meniul stânga: **"APIs & Services" → "Library"**
2. Caută **"Google Drive API"**
3. Click pe el → **"Enable"**

---

## Pasul 3 — Creează credențialele OAuth

1. **"APIs & Services" → "Credentials"**
2. Click **"+ Create Credentials" → "OAuth client ID"**
3. Dacă îți cere să configurezi **OAuth consent screen**:
   - User Type: **External** → Create
   - App name: `PortfolioManager`
   - User support email: adresa ta de Gmail
   - Developer contact: adresa ta de Gmail
   - **Save and Continue** (de 3 ori) → **Back to Dashboard**
4. Revino la **Credentials → + Create Credentials → OAuth client ID**
5. Application type: **Desktop app**
6. Name: `PortfolioManager`
7. Click **Create**

---

## Pasul 4 — Descarcă credentials.json

1. În lista de credențiale, găsești clientul creat
2. Click pe **⬇ Download** (iconița de download din dreapta)
3. Se descarcă un fișier cu un nume lung `.json`
4. **Redenumește-l exact `credentials.json`**
5. **Pune-l în același folder cu `PortfolioManager.exe`**

---

## Pasul 5 — Prima rulare cu autentificare

1. Pornești `PortfolioManager.exe`
2. Se deschide automat browserul cu pagina de login Google
3. Selectezi contul Google dorit
4. Click **"Continue"** când îți arată că `PortfolioManager` cere acces la Drive
5. Browserul afișează mesajul **"The authentication flow has completed"** → îl poți închide
6. Aplicația se deschide normal, iar badge-ul din header devine **☁ verde**

Un fișier `token.json` este creat automat lângă `.exe` — **nu-l șterge!** Conține sesiunea ta și nu va mai trebui să te loghezi din nou.

---

## Cum funcționează sincronizarea

| Eveniment | Ce se întâmplă |
|-----------|---------------|
| Pornire aplicație | Descarcă automat din Drive dacă e mai nou |
| Click "💾 Salvează" | Salvează local + uploadează pe Drive |
| Click "🔄 Actualizează prețuri" | Salvează prețurile noi + uploadează |
| Click badge "☁ Drive" | Sync manual forțat (download) |

**Pe al doilea calculator:** copiezi `PortfolioManager.exe` + `credentials.json` + `token.json`
Sau: copiezi doar `exe` + `credentials.json` și te loghezi din nou (se generează `token.json` nou).

---

## Culori badge

| Badge | Semnificație |
|-------|-------------|
| ☁ Drive (gri) | Drive neconfigurat sau se conectează |
| ☁ HH:MM:SS (verde) | Sincronizat cu succes la ora afișată |
| ☁ Eroare (roșu) | Problemă — hover pe badge pentru detalii |

---

## Troubleshooting

**"credentials.json not found"** → Fișierul nu e în același folder cu `.exe`

**"Access blocked"** la login → Pe pagina OAuth consent, mergi la **"Test users"** și adaugă adresa ta de Gmail

**Token expirat** → Șterge `token.json` și repornește aplicația pentru un nou login
