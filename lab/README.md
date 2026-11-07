# Hotspot lab

Setup **A + C, everything in Docker**: one phone hotspot, one **target** laptop
running Docker, one **scanner** laptop running nmap.

```
          Phone hotspot  RSH-<team name>  (WPA2/WPA3)
                 │
     ┌───────────┴────────────┐
 Scanner laptop          Target laptop (Docker)
 nmap → data/lab/*.xml   ├─ redis      6379  DB_EXPOSED
                         ├─ mqtt       1883  MQTT_EXPOSED
                         ├─ admin      8080  HTTP_ADMIN_CLEARTEXT
                         └─ banners    2323  TELNET_OPEN
                                       2121  FTP_CLEARTEXT + OUTDATED_SERVICE
```

**Golden rule: simulate, do not expose.** Nothing here holds real data, real
passwords or a real shell. Scan only the hotspot subnet. Never the venue Wi-Fi.

## Files

| File | What it is |
|---|---|
| `docker-compose.yml` | starts the 4 containers (5 services) |
| `admin/index.html` | page titled "Admin Login" served by nginx (no real form) |
| `fake_banners.py` | fake telnet (BusyBox) + fake FTP (vsftpd 2.3.4), refuses every login |
| `scan.ps1` | nmap scan with the same flags as the Validation Set, saves to `data/lab/` |

## Steps (the 6 requirements)

### 1. Gateway
- Phone: turn on personal hotspot named **`RSH-<team name>`**.
- Security **WPA2 or WPA3**, strong password (not written in the repo).
- Set a **mobile data limit** (e.g. 500 MB).

### 2. Scanner
- Scanner laptop: **disconnect / forget the venue Wi-Fi**, unplug Ethernet,
  connect **only** to `RSH-<team name>`. Same for the target laptop.
- Install nmap (Windows: https://nmap.org/download.html, includes Npcap).
- Run `ipconfig` on both laptops, then `ping <other laptop IP>` from each.
  If ping fails, the phone isolates clients: try another phone (or Setup D below).

### 3. Targets (target laptop)
```
cd lab
docker compose up -d
docker compose ps        # all 4 should be "running"
```
If Windows asks whether Docker may accept connections, **allow** it
(otherwise the scanner only sees "filtered" ports).

### 4. Variety
The target laptop gives **6 finding types** (minimum is 5):
DB_EXPOSED, MQTT_EXPOSED, HTTP_ADMIN_CLEARTEXT, TELNET_OPEN, FTP_CLEARTEXT, OUTDATED_SERVICE.

### 5. Captures (scanner laptop, PowerShell **as administrator**, in the repo folder)
Find the hotspot subnet with `ipconfig` (iPhone is usually `172.20.10.0/28`,
Android varies - do not guess).
```
powershell -ExecutionPolicy Bypass -File lab\scan.ps1 -Subnet <subnet> -Name scan_01_before -IOwnThisNetwork
```
The script refuses public ranges, ranges bigger than /24, and runs without
`-IOwnThisNetwork`. It runs:
```
nmap -sS -sU -sV --script http-title --max-rate 100 -p T:1-1000,1883,2121,2323,6379,8080,U:53,123,161,1900,5353 -oX data/lab/<Name>.xml <subnet>
```
Without `--script http-title` there is no page title (no HTTP_ADMIN_CLEARTEXT);
without `-sU` there are no UDP results.

### 6. Before / after
1. **Before:** `scan_01_before.xml` with everything running.
   Target laptop alone: 6 findings → score about **10**.
2. **Fix** (target laptop): `docker compose stop redis banners`
   → removes DB_EXPOSED, TELNET_OPEN, FTP_CLEARTEXT, OUTDATED_SERVICE.
3. **After:** run `scan.ps1` again with `-Name scan_02_after`.
   Target laptop alone: 2 findings → score about **80**.
4. Commit **both** XML files in `data/lab/`.
5. When you leave: `docker compose down`.

The phone and the scanner laptop also appear in the scan. That is normal.
A host with open ports but no vendor and no hostname correctly gets UNKNOWN_DEVICE.

## Checklist

- [ ] Hotspot `RSH-<team name>`, WPA2/WPA3, strong password, data limit
- [ ] Both laptops only on the hotspot, ping works both ways
- [ ] `docker compose ps` shows 4 running containers
- [ ] `data/lab/scan_01_before.xml` saved
- [ ] 2+ findings fixed, `data/lab/scan_02_after.xml` saved
- [ ] Both files committed, containers stopped when leaving

## Troubleshooting

| Problem | Fix |
|---|---|
| Ping between laptops fails | Hotspot isolates clients: other phone, or Setup D |
| Ports show as `filtered` | Allow Docker in Windows Firewall on the target laptop |
| No HTTP_ADMIN_CLEARTEXT | Check `--script http-title` was used; open `http://<target-ip>:8080` |
| Telnet/FTP not found | `docker compose logs banners` should say "fake telnet on 0.0.0.0:2323" |

**Setup D (fallback, single laptop):** only if hotspot isolation blocks you -
say so in the pitch. Run the same `docker compose up -d`, then scan the Docker
network from a container on it instead of over Wi-Fi.
