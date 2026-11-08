# network-scanner

A home network scanner for non-experts: a safety score from 0 to 100, every
problem explained in Romanian or English with the steps to fix it, a Fix button
with a re-check, scan history and an AI assistant (local model by default).

## Quick start (one command)

Needs **Python 3.11+** and **Node.js 18+**. [nmap](https://nmap.org/download.html) is needed only for live scans.

```
git clone https://github.com/matei21/network-scanner.git
cd network-scanner
python start.py
```

The first run creates `backend\venv`, installs the Python and UI packages, starts the backend
(http://localhost:8000) and the UI (**http://localhost:5173**) and opens the browser. `Ctrl+C` stops
both. Later runs start in a few seconds: packages are re-installed only when `requirements.txt` or
`package-lock.json` change.

| Option | What it does |
|---|---|
| `python start.py --with-llm` | also installs the optional local AI model (Qwen 2.5 3B, ~2 GB, once) |
| `python start.py --no-browser` | doesn't open the browser |
| `python start.py --skip-install` | starts right away, without checking packages |

## AI assistant (optional)

Findings, severities and scores never use AI: they come from fixed rules and are identical on every run.
AI only writes explanations, fix steps and chat answers, and the app picks one of three modes:

1. **Built-in texts** (default, nothing to install): every explanation and fix comes from our own
   RO/EN templates; the assistant answers from the scan data.
2. **Groq** (cloud, fast, better answers): get a free API key at https://console.groq.com, then in
   the app open the **AI** menu in the top bar, choose **Groq Cloud**, paste the key and press **Save**.
   The key is kept only in the running backend's memory: it is never written to disk or to the
   repository (NFR-01), so **enter it again after every start**. With Groq, the question and the scan
   data are sent to Groq.
3. **Local model** (offline): `python start.py --with-llm` installs `requirements-llm.txt` and
   downloads the model once (~2 GB); slower, needs ~3 GB of free RAM.

## Standard results (FR-15) and tests

```
backend\venv\Scripts\python.exe -m analyzer data/validation --out results/
backend\venv\Scripts\python.exe -m pytest
```

On Linux / macOS use `backend/venv/bin/python`. The first command writes `findings.csv` and
`scores.csv` for the whole folder (`ERROR` for unreadable files).

## Run the app and the live demo

Backend, frontend, lab containers, scan → Fix → scan again, and how to reset
the fixes before a demo: see **[DEMO.md](DEMO.md)**.

Live scans run only on the team hotspot (Wi-Fi `RSH...`), only for private
addresses inside the network this laptop is on, at most a /24, and only after
confirmation (`backend/app/guardrails.py`). From the command line, in a terminal
opened **as administrator**:

```
backend\venv\Scripts\python.exe -m backend.scan --confirm
```

## Project structure

```
analyzer/   nmap XML parser, detection rules, score, CSV export  (python -m analyzer <folder>)
backend/    FastAPI, guardrails, live nmap scans, SQLite history
frontend/   web UI (React + Vite)
ai/         RO/EN explanations, fix commands, AI agents (Groq / local LLM), device recognition
start.py    one command: install what is missing, start backend + UI
docs/       api_contract.json - the JSON format shared by backend and UI
data/       validation/ (V1-V7), lab/ (our scans), test_set/
tests/      pytest + expected results for the Validation Set
results/    generated findings.csv + scores.csv (never edited by hand)
```

## No secrets (NFR-01, live check 7)

Keys and passwords live only in a local `.env` (ignored by git); `.env.example`
files contain placeholders only. Check the whole repository, every commit on
every branch, with [gitleaks](https://github.com/gitleaks/gitleaks):

```bash
winget install --id Gitleaks.Gitleaks -e
gitleaks detect --source . --verbose
```

Expected result: `no leaks found` (exit code 0). Last verified (gitleaks 8.30.1,
`--log-opts="--all"`, every branch): 52 commits, no leaks.

## Privacy of scan files (NFR-02)

Lab scans: MAC addresses masked for privacy (NFR-02); all other data is unchanged nmap output.
New lab scans are masked automatically by `lab/scan.ps1`; for a scan made by hand run
`python lab/mask_macs.py data/lab` before committing (`pytest` fails otherwise).
Raw live scans (`scans/`) are never committed and are erased by "delete my history".
The Validation Set files are the organisers' data and are kept unchanged.
