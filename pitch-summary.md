# Network Health Check — pitch summary

**R Systems Hackathon 2026 · Secure Networks, Simply Explained**

> *Other tools show you the open doors. Ours explains them in plain Romanian or English,
> walks you through closing them, and proves they are closed.*

---

## 1. The problem

Homes and small offices are full of devices nobody configured: routers with admin pages over
plain HTTP, cameras streaming to anyone on the Wi-Fi, old FTP servers, forgotten Telnet. Every
open service is a door. Professional scanners such as nmap find those doors, but they speak
to experts. The person who owns the network, a parent or a grandparent, can't act on a port list.

## 2. Our answer: from scan to proof

We built around the brief's four words for "secure":

| Brief | What our tool does |
|---|---|
| **Visibility** | Finds every device on the network you are connected to (IP, masked MAC, vendor, hostname, device type and icon) and draws them on a **network map** coloured by risk |
| **Understanding** | Every finding gets **at most 2 sentences** in **Romanian and English**, an everyday metaphor and a "what could happen" scenario, with no unexplained jargon |
| **Action** | **1–5 ordered fix steps** per finding, the **most dangerous device first**, plus an assistant that answers questions **only from the scan** |
| **Proof** | Every scan is kept. The history shows **score trend, resolved findings, new or removed devices, opened or closed ports**, and a change alert |

## 3. Suggested demo (5–7 minutes)

| Time | Who | What to show |
|---|---|---|
| 0:00 | Speaker 1 | The problem in one sentence + the four words (Visibility, Understanding, Action, Proof) |
| 0:45 | Speaker 1 | **Guardrail:** `python -m backend.scan --target 8.8.8.8 --confirm` gives REFUSED (public IP); the venue subnet gives REFUSED (outside your network); no `--confirm` gives REFUSED |
| 1:45 | Speaker 2 | Open the UI with our **lab "before" scan**: score **0**, the map, the most dangerous device, one finding explained in RO, then EN |
| 3:00 | Speaker 2 | Ask the assistant: *"Which device is the most dangerous and what do I do first?"*. The answer names the device and port from the scan, nothing invented |
| 3:45 | Speaker 3 | Load the **"after" scan**: score **0 → 70**, history lists the **5 resolved findings** and the **closed ports** |
| 4:45 | Speaker 3 | Upload a **broken file**: clear ERROR, no crash. Run **gitleaks**: no leaks |
| 5:30 | Speaker 4 | Numbers, limitations, next steps (sections 7, 9, 10) |

## 4. Architecture

```
 Phone hotspot  RSH-<team>                     Validation / Test Set files
        │                                                │
  Live scan (nmap, admin terminal)                       │
  guardrail: own subnet, private, ≤/24,                  │
  team Wi-Fi, --confirm, ≤100 packets/s                  │
        │  nmap XML                                       │  nmap XML
        ▼                                                ▼
 ┌──────────────────────────── analyzer/ (pure Python, offline, deterministic) ─┐
 │ parser (defusedxml, 20 MB limit) → 15 rules → standard score → CSV export    │
 └───────────────────────────────────────────────────────────────────────────────┘
        │ findings + score                                │ findings.csv / scores.csv
        ▼                                                 ▼  (one command, whole folder)
 ┌── backend/ FastAPI ───────────────────┐       python -m analyzer <folder> --out results/
 │ upload, live-scan jobs, history,       │
 │ diff, change alert, PDF, RO/EN messages│
 │ SQLite (local only)                    │
 └───────────────┬────────────────────────┘
                 │ enrich (no LLM): device type, RO/EN texts, fixes, CIS/OWASP
                 ▼
 ┌── ai/ ──────────────────────────────────────────────────────────────────┐
 │ templates (always available) · fingerprinting · narrator · weighted score │
 │ assistant: local Qwen 2.5 3B (offline) or Groq (opt-in) → template fallback│
 └───────────────┬──────────────────────────────────────────────────────────┘
                 ▼
 ┌── frontend/ React + Vite ────────────────────────────────────────────────┐
 │ traffic-light score · network map · findings · history & diff · assistant │
 │ RO/EN toggle · simple / expert mode · one-page PDF report                 │
 └───────────────────────────────────────────────────────────────────────────┘
```

**Golden rule of the design:** findings, severities and scores come **only from our own rules**,
never from an LLM, so they are identical on every run. AI only writes the explanations,
and there is always a built-in text fallback.

## 5. Technical details

### Analyzer (`analyzer/`)
- **Safe parsing:** `defusedxml` blocks XML external-entity and expansion attacks; files over
  20 MB are refused; every parse problem becomes `ERROR` for that file, and the run continues.
- **15 rules, exactly as the official catalog:** only ports in state `open` count
  (`open|filtered` does not); decisions use the **service name**, never the port number, so Telnet
  on 2323 and Redis on 6380 are still found; UPnP/SNMP only on UDP; HTTP admin only without SSL and
  with a login/admin/config/setup/router/settings title; one SMB finding per device (445, else 139);
  OUTDATED_SERVICE in addition to the service's own finding; UNKNOWN_DEVICE with an empty port.
- **Outdated versions** are compared as numbers, not text (`10.0` > `7.5`): vsftpd 2.3.4,
  OpenSSH < 7.4, Apache httpd ≤ 2.2, IIS ≤ 7.5, Samba ≤ 3.
- **Score:** `max(0, 100 − sum of points)`. Findings are de-duplicated and sorted, so the CSVs
  are byte-identical on every run.
- **One command for a whole folder:** `python -m analyzer data/test_set --out results/`.

### Live scan and guardrail (`backend/`)
- **nmap command:** `-sS -sU -sV --script http-title --max-rate 100`, nmap's **top 1,000 TCP ports**
  (list generated from nmap's own frequency file and committed, so every laptop scans the same 1,003
  ports including MQTT, Redis and MongoDB) plus **UDP 53, 123, 161, 1900, 5353**.
- **Guardrail, checked in this order, and none of the checks can crash:**
  1. the target must be an IPv4 address or subnet (hostnames and IPv6 refused, no DNS lookups);
  2. public ranges are refused;
  3. the network must be detected, otherwise the scan is refused (fails closed);
  4. at most a /24;
  5. inside the allowlist, which defaults to the subnet the laptop is connected to;
  6. the laptop must be on the team Wi-Fi (`RSH…`);
  7. an explicit `--confirm` (or the confirm dialog in the UI).
- **Network detection** works on Windows even with WSL, VirtualBox or Docker adapters: it picks the
  adapter that has a gateway, whatever order Windows lists them in.
- **Live scans run as a background job** with progress and cancel, **one at a time**.

### History and proof
- Every scan is stored **locally** in SQLite as a full snapshot, so a past scan opens exactly as it was.
- The **diff** between two scans lists resolved and new findings, added and removed devices, and
  **opened and closed ports**, plus a **change alert** (new device, new open port).
- Our own scans (lab, live) are kept apart from Validation/Test Set files, so the trend never mixes them.
- **Delete my history** erases the database, the raw scan files and the free space in the database file.

### AI layer (`ai/`)
- **Always available, no LLM needed:** RO/EN explanations (≤ 2 sentences), 1–5 fix steps,
  **CIS Controls / OWASP IoT** references, risk scenarios, device type and icon.
- **Assistant:** specialised agents on a **local Qwen 2.5 3B** model (works offline); **Groq** cloud
  only if the user enters a key. It answers **only from the scan** and says so when the scan can't
  answer. **Web search is off unless the user allows it.** If no model is available, it falls back
  to built-in text.
- **Weighted risk score** shown **beside** the official score (allowed by FR-09): it adds device
  type, dangerous combinations and the gateway, but never replaces the standard score.

### Fix assistance
- Every finding shows the steps and, where it applies, the exact command.
- A command runs **only if the finding is on this laptop** and **only after the Windows UAC
  prompt** ("Yes" from the person). For other devices we show steps or open the device's admin page.

## 6. Hotspot lab

- **Setup:** phone hotspot `RSH-<team>` (WPA2/WPA3), scanner laptop on the hotspot only, targets in
  **Docker** (Redis, Mosquitto, nginx "Admin Login") plus **simulated banners** (fake BusyBox Telnet,
  fake vsftpd 2.3.4, fake OpenSSH). Banners only: no real shell, data or passwords.
- **Before:** score **0**, **8 finding types** (Telnet, DB, HTTP admin, FTP, Outdated, SSH, SMB, Unknown).
- **Fix:** stopped Redis and the fake services.
- **After:** score **70**, **5 findings resolved**, 5 ports closed.
- Lab scans are in the repo with **MAC addresses masked** (`lab/mask_macs.py`), and a test fails if
  an unmasked scan is ever committed.

## 7. Numbers to show

| | |
|---|---|
| Validation Set | **24/24 findings, 0 extra, 8/8 scores, V7 = ERROR**, identical to the answer key |
| Automated tests | **137 passing** (analyzer, rules per trap, guardrail, ports, privacy, security, i18n, history, change alert) |
| Secret scan | **gitleaks: 47 commits on all branches, no leaks** |
| Live scan coverage | **1,003 TCP + 5 UDP ports**, max **100 packets/s** |
| Lab before → after | score **0 → 70**, **5 findings fixed**, **8 finding types** |
| Languages | every user-facing text in **Romanian and English** |

## 8. Security and privacy by design

| Requirement | How we meet it |
|---|---|
| NFR-01 Secrets | no keys in the repo, `.env` ignored, Groq key kept only in memory; gitleaks clean |
| NFR-02 Privacy | MACs masked in all output **and** in committed lab scans; history only local; one-click delete |
| NFR-03 Hostile input | `defusedxml`, size limits, safe file names, strict guardrail input; the UI never renders HTML from scans |
| NFR-04 Least privilege | admin only for the live scan (nmap) and for a fix the person approves in UAC |
| NFR-05 Determinism | same file gives the same findings, severities and scores; fixed port list |
| NFR-06 Grounded AI | assistant uses only scan data, says when the scan can't answer, falls back to templates |
| API hardening | CORS limited to our own UI, trusted-host check (blocks DNS rebinding), one live scan at a time, `/batch` never overwrites the upload CSVs |

## 9. Limitations (say them before the jury asks)

- **Live scans cover the top 1,000 TCP ports.** A service hidden on an unusual port can be missed.
  File analysis has no such limit.
- **Judgement calls in the rules:** a Samba version reported as a range (`3.X - 4.X`) is not flagged
  as outdated; `http-proxy` with an admin title is not flagged (the rule says service `http`).
- **Device type is a guess** from vendor and ports (e.g. a Chromecast may be labelled as a phone).
- **The local model** has to be downloaded once and is slower on weak laptops; the built-in text
  works without it.
- **Old git history** still contains lab scans from before MACs were masked.

## 10. Next steps

- Optional "full check" of one device on all 65,535 ports.
- Reading passive announcements (mDNS, SSDP) for better device names.
- A "check my fix" button that re-scans one device and updates the score instantly.
- A report for an insurer or IT supplier with the before/after comparison.

## 11. Live checks — what we run

| # | Check | Command / action |
|---|---|---|
| 1 | Re-run a Test Set file | `python -m analyzer data/test_set --out results/` |
| 2 | Most dangerous device, first fix | UI → overview map → device marked "most dangerous" → first step |
| 3 | Explain three findings | UI → Findings tab (RO/EN toggle) |
| 4 | Guardrail | `python -m backend.scan --target 8.8.8.8 --confirm`, venue subnet, no `--confirm` |
| 5 | Broken file | upload `V7_broken.xml` in the UI, or run the analyzer: ERROR, no crash |
| 6 | History before/after | UI → History → lab before vs after (0 → 70) |
| 7 | No secrets | `gitleaks git --log-opts="--all" --redact -v .` |

## 12. Likely jury questions

- **"Where does the AI come in, and can it invent findings?"** Findings and scores come only from
  our rules. AI writes explanations and answers questions using only the scan, and falls back to
  built-in text.
- **"What if I give it a public IP?"** Refused, with a clear reason. So is anything outside your
  own subnet, anything bigger than a /24, and any scan without confirmation.
- **"How do you know your results are right?"** 24/24 on the Validation Set with no extra rows,
  a test for every trap in the brief, and identical output on every run.
- **"What data leaves the laptop?"** Nothing by default. Groq and web search are opt-in, and MACs
  are always masked.

---

### Before presenting (demo laptop checklist)
- `frontend/.env.local` contains `VITE_USE_MOCK=0`, otherwise the UI shows example data.
- Vite runs with `host: "127.0.0.1"` (it is `0.0.0.0` now, which exposes the UI to the whole hotspot).
- Backend started on `127.0.0.1` only; live scan from an admin terminal.
- Run the 7 live checks once, end to end.
