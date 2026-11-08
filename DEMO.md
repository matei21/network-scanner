# Running the app and the live demo (Windows)

Step by step: start the app, start the lab containers, scan, Fix, scan again,
and reset everything before the pitch.

All commands are PowerShell, run from the repo folder `D:\sh2026\network-scanner`
unless the step says otherwise.

## 0. Once per laptop

```
python -m venv backend\venv
backend\venv\Scripts\python.exe -m pip install -r requirements.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
cd frontend
npm install
cd ..
```

Also needed: nmap (https://nmap.org/download.html, includes Npcap) and Docker Desktop.

If `docker` is "not recognized" (Docker Desktop installed only for your user),
add it to PATH once, then close and reopen VS Code / every terminal:

```
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin", "User")
```

Run it only once. After reopening, `docker --version` must work in every new terminal.

## 1. Connect to the team hotspot

Connect the laptop **only** to the `RSH...` hotspot (forget the venue Wi-Fi,
unplug Ethernet). Live scans are refused on any other Wi-Fi.

```
netsh wlan show interfaces      # SSID must start with RSH
ipconfig                        # note the Wi-Fi "IPv4 Address", e.g. 10.74.130.252
```

## 2. Start the lab containers

Docker Desktop must be running.

```
cd lab
docker compose up -d
docker compose ps
cd ..
```

`ps` must show **redis, mqtt, admin, banners** as `running`. If you only see
old containers (camera, telnet, ftp, http-admin...) as `Exited`, the lab is not
started: run `docker compose up -d` again from the `lab` folder.

If Windows asks whether Docker may accept connections, **allow** it.

## 3. Start the backend (terminal 1, as Administrator)

Right click PowerShell → **Run as administrator** (nmap needs it).

```
cd D:\sh2026\network-scanner
backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000
```

Wait for `Application startup complete`. Leave it open.

## 4. Start the frontend (terminal 2)

```
cd D:\sh2026\network-scanner\frontend
npm run dev
```

Open **http://localhost:5173**. Use `localhost`, not the laptop's IP:
other addresses are blocked on purpose (CORS / trusted hosts).

`frontend\.env.local` must contain `VITE_USE_MOCK=0`, otherwise the UI shows mock data.
No `.env` is needed for the backend: every setting has a safe default.
The AI key (optional) is entered in the UI, in the AI settings.

## 5. Scan → Fix → scan again

1. Click **Scan**. As target type your own IP from `ipconfig` (one host is much
   faster than the whole /24). Confirm and wait for the progress bar.
2. You should see DB_EXPOSED (Redis 6379), MQTT, HTTP_ADMIN_CLEARTEXT (8080),
   TELNET_OPEN (2323), FTP_CLEARTEXT + OUTDATED_SERVICE (2121), SSH_OPEN (2222),
   plus whatever else runs on your laptop.
3. Click **Fix** on a finding and accept the Windows (UAC) prompt.
   The Fix adds a firewall rule named `NetScanner block TCP <port>`.
4. Click **Scan** again on the same IP. The finding is gone, the score goes up,
   and the change alert lists it as resolved and the port as closed.
   History → **Diferente** shows the same comparison.

Why this works when the laptop scans itself: nmap on this laptop never passes
through Windows Firewall, so the backend marks ports blocked by our own
`NetScanner block` rules as `filtered`, which is what every other device on the
hotspot sees (`backend/app/self_firewall.py`). nmap's original output stays in
`scans/<id>/live_scan.nmap.xml`.

OUTDATED_SERVICE only gets a read-only Fix (it shows which program to update).
It disappears once FTP_CLEARTEXT on the same port (2121) is fixed.

Other way to show "fixed" without the Fix button:

```
cd lab
docker compose stop redis banners
```

then scan again.

## 6. Fixes stay after a restart

Firewall rules survive a reboot, a backend restart and restarting the
containers, so fixed ports **stay fixed**. To show the problems again (before
every demo or pitch), delete our rules, in PowerShell **as Administrator**:

```
Get-NetFirewallRule -DisplayName 'NetScanner block*'          # see what Fix added
Remove-NetFirewallRule -DisplayName 'NetScanner block*'       # delete only our rules
```

Only rules created by the Fix button start with `NetScanner block`; nothing else
is touched.

## 7. Before the pitch (10 minutes before)

1. Laptop only on the `RSH...` hotspot (step 1).
2. Reset the fixes: `Remove-NetFirewallRule -DisplayName 'NetScanner block*'` (as Administrator).
3. Containers: `cd lab`, `docker compose up -d`, `docker compose ps` → 4 running.
4. Backend (as Administrator) and frontend (steps 3 and 4).
5. Do the **before** scan of your own IP now, so the result is already on screen.
6. Have a recorded video of the whole flow as a backup.

During the pitch: show the score and the findings → **Fix** one (Redis or Telnet)
→ **Scan** again → show the change alert, the higher score and the history.

## 8. When you are done

```
cd lab
docker compose down
```

Stop the backend and the frontend with `Ctrl + C`.

## Saving a lab scan in git

Live scans from the UI are saved in `scans/` (ignored by git). If you copy a
scan XML into `data/lab/` to commit it, mask the MAC addresses first:

```
backend\venv\Scripts\python.exe lab\mask_macs.py data\lab
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker` is not recognized | Step 0, PATH line; then open a new terminal |
| Containers do not show up in the scan | `docker compose ps` in `lab`: the 4 must be `running` |
| Scan refused: not on the team hotspot | Connect only to the `RSH...` Wi-Fi |
| Scan refused: outside your network | Use your own IP or the subnet from `ipconfig` |
| UI shows fake data | `frontend\.env.local` must have `VITE_USE_MOCK=0`, restart `npm run dev` |
| UI cannot reach the API | Open `http://localhost:5173` (not the IP); backend running on port 8000 |
| Fixed port still shows open | Restart the backend (old code), check the rule with `Get-NetFirewallRule -DisplayName 'NetScanner block*'` |
| Problems do not come back for the demo | Step 6: remove the `NetScanner block` rules |
