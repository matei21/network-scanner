// Shape mirrors docs/api_contract.json (team contract - do not drift).
// When backend is live, src/lib/api.js swaps this import for a fetch call.
// Verdict + summary strings are derived in the UI (lib/findings.js) so the
// backend contract stays minimal.
//
// Realistic sample: a small apartment with smart-home gear + a laptop and
// a NAS. Score lands in the "watch" band (40) so the UI exercises every
// severity level: high (camera), medium (several), low (printer + unknown),
// info (ssh). Edit any number here and refresh the browser to see it.

export const mockScan = {
  scan_id: "demo-2026-11-07-001",
  file: "home_evening_scan.xml",
  status: "ok",
  error: null,
  // 100 - (20 + 10 + 10 + 10 + 10 + 5 + 5) = 30
  score: 30,
  devices: [
    // 1. Routerul casei - aproape fiecare retea are HTTP admin + UPnP pornite.
    {
      ip: "192.168.1.1",
      mac: "50:C7:BF:**:**:**",
      vendor: "TP-Link",
      hostname: "Archer-C80",
      type: "router",
      icon: "🌐",
      open_ports: [
        { port: 80, protocol: "tcp", service: "http", product: "lighttpd", version: "1.4.59" },
        { port: 443, protocol: "tcp", service: "https", product: "lighttpd", version: "1.4.59" },
        { port: 1900, protocol: "udp", service: "upnp", product: "MiniUPnPd", version: "2.1" },
      ],
      findings: [
        {
          code: "HTTP_ADMIN_CLEARTEXT",
          ip: "192.168.1.1",
          port: 80,
          protocol: "tcp",
          severity: "medium",
          points: 10,
          evidence: "service=http, title='TP-Link Wireless Router Login'",
          explanation_ro:
            "Pagina de administrare a ruterului se deschide fara criptare. Oricine din reteaua ta poate vedea parola cand o scrii.",
          explanation_en:
            "The router admin page opens without encryption. Anyone on your network can see the password as you type it.",
          fix_steps_ro: [
            "Deschide 192.168.1.1 in browser si intra cu parola de admin.",
            "Mergi la Setari > Administrare si bifeaza 'Doar HTTPS'.",
            "Salveaza si deconecteaza-te.",
          ],
          fix_steps_en: [
            "Open 192.168.1.1 in your browser and sign in as admin.",
            "Go to Settings > Administration and enable 'HTTPS only'.",
            "Save and sign out.",
          ],
        },
        {
          code: "UPNP_EXPOSED",
          ip: "192.168.1.1",
          port: 1900,
          protocol: "udp",
          severity: "medium",
          points: 10,
          evidence: "service=upnp",
          explanation_ro:
            "Ruterul permite altor dispozitive sa deschida singure porturi catre internet. Un program rau poate face asta fara sa stii.",
          explanation_en:
            "The router lets other devices open internet ports on their own. A malicious program can do this without you noticing.",
          fix_steps_ro: [
            "Intra in pagina ruterului.",
            "Cauta 'UPnP' in meniul Advanced > NAT Forwarding si dezactiveaza-l.",
            "Reporneste ruterul.",
          ],
          fix_steps_en: [
            "Open the router page.",
            "Find 'UPnP' in Advanced > NAT Forwarding and disable it.",
            "Reboot the router.",
          ],
        },
      ],
    },

    // 2. Laptopul mamei - Windows cu file sharing pornit din greseala.
    {
      ip: "192.168.1.10",
      mac: "A4:5E:60:**:**:**",
      vendor: "Dell Inc.",
      hostname: "DESKTOP-MAMA",
      type: "pc",
      icon: "💻",
      open_ports: [
        { port: 139, protocol: "tcp", service: "netbios-ssn", product: "Microsoft Windows netbios-ssn", version: "" },
        { port: 445, protocol: "tcp", service: "microsoft-ds", product: "Microsoft Windows 10 microsoft-ds", version: "" },
      ],
      findings: [
        {
          code: "SMB_EXPOSED",
          ip: "192.168.1.10",
          port: 445,
          protocol: "tcp",
          severity: "medium",
          points: 10,
          evidence: "service=microsoft-ds (Windows file sharing)",
          explanation_ro:
            "Laptop-ul partajeaza fisiere cu tot ce e in retea. Cineva conectat la Wi-Fi poate incerca sa deschida dosarele tale.",
          explanation_en:
            "The laptop shares files with everything on the network. Someone on the Wi-Fi can try to open your folders.",
          fix_steps_ro: [
            "Deschide Setari > Retea si Internet > Proprietati Wi-Fi.",
            "Schimba profilul retelei din 'Public' in 'Privat' si dezactiveaza 'File and printer sharing'.",
            "Dezactiveaza SMBv1 din 'Turn Windows features on or off'.",
          ],
          fix_steps_en: [
            "Open Settings > Network & Internet > Wi-Fi properties.",
            "Change the network profile from 'Public' to 'Private' and turn off 'File and printer sharing'.",
            "Disable SMBv1 under 'Turn Windows features on or off'.",
          ],
        },
      ],
    },

    // 3. Printer-ul din living - nimic rau, dar portul jet-direct e deschis.
    {
      ip: "192.168.1.15",
      mac: "B8:27:EB:**:**:**",
      vendor: "HP Inc.",
      hostname: "HPDeskJet-3700",
      type: "printer",
      icon: "🖨️",
      open_ports: [
        { port: 631, protocol: "tcp", service: "ipp", product: "CUPS", version: "2.3" },
        { port: 9100, protocol: "tcp", service: "jetdirect", product: "", version: "" },
      ],
      findings: [
        {
          code: "PRINTER_RAW_EXPOSED",
          ip: "192.168.1.15",
          port: 9100,
          protocol: "tcp",
          severity: "low",
          points: 5,
          evidence: "service=jetdirect on port 9100",
          explanation_ro:
            "Oricine din retea poate trimite comenzi direct la printer. In cel mai rau caz, risipesti cerneala, dar nu iti fura date.",
          explanation_en:
            "Anyone on the network can send print jobs directly. Worst case, you waste ink, but your data isn't stolen.",
          fix_steps_ro: [
            "Intra in setarile printer-ului (de obicei 192.168.1.15 in browser).",
            "Dezactiveaza 'Raw printing' sau 'Port 9100' din meniul Network.",
            "Daca nu gasesti, lasa asa - riscul e mic.",
          ],
          fix_steps_en: [
            "Open the printer settings (usually 192.168.1.15 in a browser).",
            "Disable 'Raw printing' or 'Port 9100' from the Network menu.",
            "If you can't find it, it is fine to leave - the risk is small.",
          ],
        },
      ],
    },

    // 4. Smart TV - listed but no findings; shows "clean" devices still appear.
    {
      ip: "192.168.1.20",
      mac: "F0:72:EA:**:**:**",
      vendor: "Samsung Electronics",
      hostname: "Samsung-TV-Living",
      type: "tv",
      icon: "📺",
      open_ports: [
        { port: 8001, protocol: "tcp", service: "upnp", product: "Samsung AllShare", version: "" },
        { port: 8080, protocol: "tcp", service: "http-alt", product: "", version: "" },
      ],
      findings: [],
    },

    // 5. Camera din hol - highlight-ul demo-ului, "most dangerous".
    {
      ip: "192.168.1.40",
      mac: "AC:3F:A4:**:**:**",
      vendor: "Hikvision Digital Technology",
      hostname: "cam-hol",
      type: "camera",
      icon: "📹",
      open_ports: [
        { port: 80, protocol: "tcp", service: "http", product: "Hikvision webs", version: "" },
        { port: 554, protocol: "tcp", service: "rtsp", product: "Hikvision RTSP", version: "" },
        { port: 8000, protocol: "tcp", service: "http-alt", product: "Hikvision SDK", version: "" },
      ],
      findings: [
        {
          code: "CAMERA_STREAM_EXPOSED",
          ip: "192.168.1.40",
          port: 554,
          protocol: "tcp",
          severity: "high",
          points: 20,
          evidence: "service=rtsp (Real Time Streaming Protocol)",
          explanation_ro:
            "Camera transmite imagine live pe un port deschis. Daca cineva afla adresa ei, poate incerca sa vada ce filmeaza.",
          explanation_en:
            "The camera streams live video on an open port. If someone learns its address, they can try to watch what it films.",
          fix_steps_ro: [
            "Deschide aplicatia Hik-Connect sau pagina 192.168.1.40 in browser.",
            "Mergi la Network > Advanced si dezactiveaza 'RTSP'.",
            "Schimba parola de admin daca e inca cea din fabrica.",
          ],
          fix_steps_en: [
            "Open the Hik-Connect app or the page 192.168.1.40 in a browser.",
            "Go to Network > Advanced and disable 'RTSP'.",
            "Change the admin password if it is still the factory one.",
          ],
        },
        {
          code: "HTTP_ADMIN_CLEARTEXT",
          ip: "192.168.1.40",
          port: 80,
          protocol: "tcp",
          severity: "medium",
          points: 10,
          evidence: "service=http, title='Hikvision Web Login'",
          explanation_ro:
            "Pagina de setari a camerei este fara criptare. Parola trece in clar prin retea.",
          explanation_en:
            "The camera settings page has no encryption. The password travels in plain text across the network.",
          fix_steps_ro: [
            "Intra in setarile camerei.",
            "Activeaza HTTPS din meniul Network > Advanced Settings (daca modelul suporta).",
            "Daca nu se poate, nu accesa camera din cafenele sau retele publice.",
          ],
          fix_steps_en: [
            "Open the camera settings.",
            "Enable HTTPS in Network > Advanced Settings (if the model supports it).",
            "If not possible, do not access the camera from cafes or public networks.",
          ],
        },
      ],
    },

    // 6. Smart hub / IoT - fara MAC detectabil, fara hostname.
    {
      ip: "192.168.1.41",
      mac: null,
      vendor: null,
      hostname: null,
      type: "iot",
      icon: "🔌",
      open_ports: [
        { port: 1883, protocol: "tcp", service: "mqtt", product: "mosquitto", version: "1.6.9" },
      ],
      findings: [
        {
          code: "MQTT_EXPOSED",
          ip: "192.168.1.41",
          port: 1883,
          protocol: "tcp",
          severity: "medium",
          points: 10,
          evidence: "service=mqtt (Mosquitto 1.6.9)",
          explanation_ro:
            "Un dispozitiv smart home trimite comenzi printr-un canal deschis. Cineva din retea poate asculta sau comanda becurile, prizele, etc.",
          explanation_en:
            "A smart home device sends commands through an open channel. Someone on the network can listen or control your bulbs, plugs, etc.",
          fix_steps_ro: [
            "Verifica in aplicatia hub-ului daca se poate activa autentificare pe MQTT.",
            "Muta dispozitivul pe o retea de oaspeti separata, izolata de telefoanele si laptop-urile tale.",
          ],
          fix_steps_en: [
            "Check in the hub app if MQTT authentication can be enabled.",
            "Move the device to a separate guest network, isolated from your phones and laptops.",
          ],
        },
      ],
    },

    // 7. Telefonul tatii - niciun port deschis, apare doar in lista.
    {
      ip: "192.168.1.42",
      mac: "CC:2D:B7:**:**:**",
      vendor: "Apple, Inc.",
      hostname: "iPhone-Tata",
      type: "phone",
      icon: "📱",
      open_ports: [],
      findings: [],
    },

    // 8. NAS-ul vechi din birou - SSH e OK (criptat), dar e doar info.
    {
      ip: "192.168.1.50",
      mac: "00:11:32:**:**:**",
      vendor: "Synology Incorporated",
      hostname: "DS216-NAS",
      type: "nas",
      icon: "🗄️",
      open_ports: [
        { port: 22, protocol: "tcp", service: "ssh", product: "OpenSSH", version: "8.4" },
        { port: 5000, protocol: "tcp", service: "http", product: "Synology DSM", version: "6.2" },
      ],
      findings: [
        {
          code: "SSH_OPEN",
          ip: "192.168.1.50",
          port: 22,
          protocol: "tcp",
          severity: "info",
          points: 0,
          evidence: "service=ssh (OpenSSH 8.4)",
          explanation_ro:
            "NAS-ul accepta conexiuni SSH. SSH este criptat si sigur, dar iti spunem ca sa stii ca portul e deschis.",
          explanation_en:
            "The NAS accepts SSH connections. SSH is encrypted and safe, but we tell you so you know the port is open.",
          fix_steps_ro: [
            "Daca nu folosesti SSH, dezactiveaza-l din DSM > Control Panel > Terminal.",
            "Daca il folosesti, asigura-te ca ai parola puternica si cheie SSH in loc de parola.",
          ],
          fix_steps_en: [
            "If you don't use SSH, disable it in DSM > Control Panel > Terminal.",
            "If you do use it, make sure you have a strong password or an SSH key instead of a password.",
          ],
        },
      ],
    },

    // 9. Dispozitiv necunoscut - MAC-ul nu matchuieste niciun vendor.
    {
      ip: "192.168.1.99",
      mac: null,
      vendor: null,
      hostname: null,
      type: "unknown",
      icon: "❓",
      open_ports: [
        { port: 8080, protocol: "tcp", service: "http-alt", product: "", version: "" },
      ],
      findings: [
        {
          code: "UNKNOWN_DEVICE",
          ip: "192.168.1.99",
          port: null,
          protocol: null,
          severity: "low",
          points: 5,
          evidence: "no MAC vendor match, no hostname",
          explanation_ro:
            "Nu stim ce e acest dispozitiv. Poate fi un dispozitiv al unui prieten, sau ceva care nu ar trebui sa fie acolo.",
          explanation_en:
            "We don't know what this device is. It could be a friend's device, or something that shouldn't be there.",
          fix_steps_ro: [
            "Verifica cine e acasa si ce aparate au conectate.",
            "Daca nu e al nimanui din casa, schimba parola de Wi-Fi.",
            "Dupa schimbare, scaneaza din nou - dispozitivul necunoscut ar trebui sa dispara.",
          ],
          fix_steps_en: [
            "Check who is at home and what devices they have connected.",
            "If it belongs to no one in the house, change the Wi-Fi password.",
            "Rescan after changing - the unknown device should be gone.",
          ],
        },
      ],
    },
  ],
  // Istoricul: Alex a rezolvat cateva probleme de la o scanare la alta.
  history: [
    { scan_id: "demo-2026-11-01-001", date: "2026-11-01", score: 10, findings_count: 9 },
    { scan_id: "demo-2026-11-03-001", date: "2026-11-03", score: 15, findings_count: 8 },
    { scan_id: "demo-2026-11-05-001", date: "2026-11-05", score: 25, findings_count: 7 },
    { scan_id: "demo-2026-11-07-001", date: "2026-11-07", score: 30, findings_count: 7 },
  ],
};

// Versiunea "dupa ce ai reparat tot" - pentru demo-ul before/after din pitch.
export const mockPerfect = {
  ...mockScan,
  scan_id: "demo-after-fixes",
  file: "home_evening_scan_after.xml",
  status: "ok",
  error: null,
  score: 100,
  devices: mockScan.devices.map((d) => ({ ...d, findings: [] })),
  history: [
    ...mockScan.history,
    { scan_id: "demo-after-fixes", date: "2026-11-08", score: 100, findings_count: 0 },
  ],
};

// Fisier corupt - testeaza ca tool-ul nu crapa.
export const mockBroken = {
  scan_id: "demo-broken",
  file: "V7_broken.xml",
  status: "error",
  error: "Fisierul pare trunchiat sau nu este un XML nmap valid. Scanarea nu s-a oprit.",
  score: null,
  devices: [],
  history: [],
};