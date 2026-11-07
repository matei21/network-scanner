# network-scanner

## Setup

```bash
pip install -r requirements.txt
python -m analyzer data/validation --out results/
pytest
```

## Structura proiectului

```
analyzer/   A - parser XML, reguli, scor, export CSV  (python -m analyzer <folder>)
backend/    B - FastAPI, guardrail, nmap live, istoric SQLite
frontend/   C - UI web (mock/scan_example.json = date mock)
ai/         D - template-uri RO/EN, LLM, fingerprinting
docs/       api_contract.json - formatul JSON comun
data/       validation/ (V1-V7), lab/ (scanurile noastre), test_set/ (ora 20)
tests/      pytest + raspunsurile asteptate pentru Validation Set
results/    findings.csv + scores.csv generate (nu se editeaza manual)
```

## No secrets (NFR-01, live check 7)

Keys and passwords live only in a local `.env` (ignored by git); `.env.example`
files contain placeholders only. Check the whole repository, every commit on
every branch, with [gitleaks](https://github.com/gitleaks/gitleaks):

```bash
winget install --id Gitleaks.Gitleaks -e
gitleaks detect --source . --verbose
```

Expected result: `no leaks found` (exit code 0). Last verified: 24 commits,
no leaks.

## Privacy of scan files (NFR-02)

Lab scans: MAC addresses masked for privacy (NFR-02); all other data is unchanged nmap output.
New lab scans are masked automatically by `lab/scan.ps1`; for a scan made by hand run
`python lab/mask_macs.py data/lab` before committing (`pytest` fails otherwise).
Raw live scans (`scans/`) are never committed and are erased by "delete my history".
The Validation Set files are the organisers' data and are kept unchanged.



Etapele in ordine

  Etapa 1: ANALYZER (fundatia -- fara asta nimic nu merge)
    - Parser XML nmap
    - Regulile de detectie (cele 15 findings)
    - Calcul scor
    - Export findings.csv + scores.csv
    - Testat pe Validation Set pana scoate exact 24 findings, 0 extra

  Etapa 2: BACKEND + SCAN LIVE
    - FastAPI cu endpoint-uri (upload XML, scan, findings, istoric)
    - Detectie automata subnet
    - Integrare nmap ca subprocess
    - Guardrail (refuz IP public, refuz fara --confirm)
    - SQLite pentru istoric

  Etapa 3: UI + AI + FEATURES
    - Interfata web (scor, devices, findings, fix-uri, istoric)
    - Integrare LLM (explicatii, chatbot)
    - Device fingerprinting (iconite)
    - RO + EN
    - Expert mode / Simple mode
    - Toate features extra (microfon, topology map, etc.)

  Etapa 4: PACKAGING + POLISH
    - PyInstaller exe
    - Testare pe Validation Set + hotspot real
    - Pitch prep

  Impartirea pe echipa (4 persoane)

  Bazat pe brief-ul lor care zice "split along the system's natural parts":

  Persoana A -- "The Engine" (tu sau cineva care stie Python bine)

  Responsabilitate: Analyzer-ul complet
    - Parser XML nmap
    - Cele 15 reguli de detectie
    - Calcul scor
    - Export CSV
    - Testeaza pe Validation Set pana e perfect

  Milestone: ruleaza pe toate 8 fisierele, scoate exact
    24 findings, scorurile corecte, V7 = ERROR

  Dupa: ajuta pe backend / guardrails

  Persoana B -- "The Plumber" (backend dev)

  Responsabilitate: FastAPI backend + infrastructura
    - Endpoint-uri REST (POST /scan, POST /upload, GET /findings, etc.)
    - Detectie automata subnet
    - Integrare nmap subprocess
    - Guardrail (allowlist, refuz IP public, --confirm flag)
    - SQLite pentru istoric (salvare scan, diff intre scanuri)
    - Integrare cu analyzer-ul lui A

  Milestone: pot uploada un XML si primesc JSON cu findings

  Dupa: packaging PyInstaller

  Persoana C -- "The Face" (frontend / UI)

  Responsabilitate: Interfata web completa
    - Pagina principala cu scor (semafor mare)
    - Lista devices cu iconite
    - Findings sortate, colorate, cu explicatii + fix-uri
    - Pagina istoric (before/after, trend scor)
    - Upload XML + buton Scan
    - RO/EN toggle
    - Responsive (sa mearga si pe telefon)
    - Accessibility (16px, contrast, keyboard nav)

  Milestone: pot vedea scor + findings + fix-uri in browser

  Dupa: expert mode toggle, topology map, polish

  Persoana D -- "The Brain" (tu, ML person)

  Responsabilitate: tot ce e AI + inovatie
    - Integrare LLM API (Claude/OpenAI)
    - System prompt pentru chatbot (grounded pe datele scanului)
    - Generare explicatii personalizate per device
    - Fallback pe template-uri statice (RO + EN) pentru toate
      cele 15 findings -- ASTA TREBUIE ORICUM, chiar fara LLM
    - Device fingerprinting (vendor + porturi -> tip device)
    - Risk prioritization contextual
    - Mapare CIS Controls / OWASP IoT
    - Optional: voice input, threat narrative, raport PDF

  Milestone: pot intreba "ce e cel mai periculos?" si primesc
    raspuns corect bazat pe scan

  Dupa: expert mode content, voice, wow features

  Cum lucrati in paralel fara sa va blocati

  Ora 0:  A incepe analyzer-ul
          B pregateste structura FastAPI + endpoint-uri stub
          C incepe UI-ul cu date mock (JSON hardcodat)
          D scrie template-urile de explicatii pentru toate 15 findings

          Nimeni nu depinde de nimeni inca.

  Ora ~4: A are analyzer-ul functional
          → B il integreaza in backend (acum endpoint-urile returneaza date reale)
          → C inlocuieste mock-ul cu API calls la backend-ul lui B
          → D incepe integrarea LLM cu datele reale din analyzer

  Ora ~8: Totul e conectat end-to-end.
          Upload XML → analyzer → backend → UI cu findings reale

          De aici toti lucreaza pe features si polish.

  Cheia: C lucreaza cu date mock pana B si A sunt gata. Asa nu sta nimeni dupa nimeni. Definiti de la inceput formatul JSON pe care backend-ul il
  returneaza:

  {
    "scan_id": "abc123",
    "score": 40,
    "devices": [
      {
        "ip": "192.168.1.1",
        "mac": "50:C7:**:**:**:**",
        "vendor": "TP-Link",
        "hostname": "router.lan",
        "type": "router",
        "icon": "🌐",
        "open_ports": [80, 443],
        "findings": [
          {
            "code": "HTTP_ADMIN_CLEARTEXT",
            "port": 80,
            "severity": "medium",
            "points": 10,
            "explanation_ro": "...",
            "explanation_en": "...",
            "fix_steps_ro": ["..."],
            "fix_steps_en": ["..."]
          }
        ]
      }
    ],
    "history": [...]
  }

  Daca toti 4 lucrati cu acest contract JSON, puteti lucra complet independent.







