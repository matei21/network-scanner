# network-scanner

A home network scanner for non-experts: a safety score from 0 to 100, every
problem explained in Romanian or English with the steps to fix it, a Fix button
with a re-check, scan history and an AI assistant (local model by default).

## Setup

```
python -m venv backend\venv
backend\venv\Scripts\python.exe -m pip install -r requirements.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
cd frontend
npm install
cd ..
backend\venv\Scripts\python.exe -m analyzer data/validation --out results/
backend\venv\Scripts\python.exe -m pytest
```

## Run the app and the live demo

Backend, frontend, lab containers, scan → Fix → scan again, and how to reset
the fixes before a demo: see **[DEMO.md](DEMO.md)**.

Live scans run only on the team hotspot (Wi-Fi `RSH...`), only for private
addresses inside the network this laptop is on, at most a /24, and only after
confirmation (`backend/app/guardrails.py`).

## Project structure

```
analyzer/   nmap XML parser, detection rules, score, CSV export  (python -m analyzer <folder>)
backend/    FastAPI, guardrails, live nmap scans, SQLite history
frontend/   web UI (React + Vite)
ai/         RO/EN explanations, fix commands, local LLM, device recognition
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
