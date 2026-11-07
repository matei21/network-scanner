// Shape mirrors docs/api_contract.json (team contract — do not drift).
// When backend is live, src/lib/api.js swaps this import for a fetch call.
// Verdict + summary strings are derived in the UI (lib/findings.js) so the
// backend contract stays minimal.

export const mockScan = {
  scan_id: "demo-2026-11-07-001",
  file: "V2_smart_home.xml",
  status: "ok",
  error: null,
  score: 40,
  devices: [
    {
      ip: "192.168.1.1",
      mac: "50:C7:**:**:**:**",
      vendor: "TP-Link",
      hostname: "router.lan",
      type: "router",
      icon: "🌐",
      open_ports: [
        { port: 80, protocol: "tcp", service: "http", product: "lighttpd", version: "1.4" },
        { port: 443, protocol: "tcp", service: "https", product: "lighttpd", version: "1.4" },
        { port: 1900, protocol: "udp", service: "upnp", product: "MiniUPnPd", version: "1.9" },
      ],
      findings: [
        {
          code: "HTTP_ADMIN_CLEARTEXT",
          ip: "192.168.1.1",
          port: 80,
          protocol: "tcp",
          severity: "medium",
          points: 10,
          evidence: "service=http, title='Router Admin Login'",
          explanation_ro:
            "Pagina de administrare a ruterului se deschide fara criptare. Oricine din reteaua ta poate vedea parola cand o scrii.",
          explanation_en:
            "Your router admin page opens without encryption. Anyone on your network can see your password as you type it.",
          fix_steps_ro: [
            "Deschide 192.168.1.1 in browser.",
            "Intra in Setari > Administrare si bifeaza 'Doar HTTPS'.",
            "Salveaza si deconecteaza-te.",
          ],
          fix_steps_en: [
            "Open 192.168.1.1 in your browser.",
            "Go to Settings > Administration and enable 'HTTPS only'.",
            "Save and log out.",
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
            "Cauta 'UPnP' in meniul de retea si dezactiveaza-l.",
            "Reporneste ruterul.",
          ],
          fix_steps_en: [
            "Open the router page.",
            "Find 'UPnP' in the network menu and disable it.",
            "Reboot the router.",
          ],
        },
      ],
    },
    {
      ip: "192.168.1.40",
      mac: "AC:3F:**:**:**:**",
      vendor: "Hikvision",
      hostname: "cam-living-room",
      type: "camera",
      icon: "📹",
      open_ports: [
        { port: 80, protocol: "tcp", service: "http", product: "Hikvision webs", version: "" },
        { port: 554, protocol: "tcp", service: "rtsp", product: "Hikvision RTSP", version: "" },
      ],
      findings: [
        {
          code: "CAMERA_STREAM_EXPOSED",
          ip: "192.168.1.40",
          port: 554,
          protocol: "tcp",
          severity: "high",
          points: 20,
          evidence: "service=rtsp",
          explanation_ro:
            "Camera ta transmite imagine live pe un port deschis. Cineva care gaseste adresa ei poate incerca sa se conecteze.",
          explanation_en:
            "Your camera streams live video on an open port. Someone who finds its address can try to connect.",
          fix_steps_ro: [
            "Intra in aplicatia camerei.",
            "Dezactiveaza accesul RTSP din meniul Retea.",
            "Schimba parola de admin.",
          ],
          fix_steps_en: [
            "Open the camera app.",
            "Disable RTSP access in the Network menu.",
            "Change the admin password.",
          ],
        },
        {
          code: "HTTP_ADMIN_CLEARTEXT",
          ip: "192.168.1.40",
          port: 80,
          protocol: "tcp",
          severity: "medium",
          points: 10,
          evidence: "service=http, title='Camera Admin'",
          explanation_ro:
            "Pagina de setari a camerei este fara criptare. Parola trece in clar prin retea.",
          explanation_en:
            "The camera settings page has no encryption. The password travels in plain text across the network.",
          fix_steps_ro: [
            "Intra in setarile camerei.",
            "Activeaza HTTPS daca modelul suporta.",
            "Altfel, nu folosi camera pe retea publica.",
          ],
          fix_steps_en: [
            "Open the camera settings.",
            "Enable HTTPS if the model supports it.",
            "Otherwise, do not use the camera on public Wi-Fi.",
          ],
        },
      ],
    },
    {
      ip: "192.168.1.41",
      mac: null,
      vendor: null,
      hostname: null,
      type: "iot",
      icon: "🔌",
      open_ports: [
        { port: 1883, protocol: "tcp", service: "mqtt", product: "mosquitto", version: "1.6" },
      ],
      findings: [
        {
          code: "MQTT_EXPOSED",
          ip: "192.168.1.41",
          port: 1883,
          protocol: "tcp",
          severity: "medium",
          points: 10,
          evidence: "service=mqtt",
          explanation_ro:
            "Un dispozitiv smart home trimite comenzi printr-un canal deschis. Cineva din retea poate asculta sau da comenzi.",
          explanation_en:
            "A smart home device sends commands through an open channel. Someone on the network can listen or send commands.",
          fix_steps_ro: [
            "Verifica in aplicatia dispozitivului daca se poate activa parola.",
            "Muta dispozitivul pe o retea de oaspeti separata.",
          ],
          fix_steps_en: [
            "Check in the device app if a password can be enabled.",
            "Move the device to a separate guest network.",
          ],
        },
      ],
    },
  ],
  history: [
    { scan_id: "demo-2026-11-05-001", date: "2026-11-05", score: 20, findings_count: 7 },
    { scan_id: "demo-2026-11-06-001", date: "2026-11-06", score: 30, findings_count: 6 },
    { scan_id: "demo-2026-11-07-001", date: "2026-11-07", score: 40, findings_count: 4 },
  ],
};

export const mockPerfect = {
  ...mockScan,
  scan_id: "demo-after-fixes",
  file: "V6b_after.xml",
  status: "ok",
  error: null,
  score: 100,
  devices: [],
};

export const mockBroken = {
  scan_id: "demo-broken",
  file: "V7_broken.xml",
  status: "error",
  error: "File is truncated or not a valid nmap XML. Tool did not crash.",
  score: null,
  devices: [],
  history: [],
};
