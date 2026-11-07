# frontend — persoana C

React + Vite + Tailwind. Interfata web pentru scaner.

## Rulare locala

```bash
cd frontend
npm install
npm run dev
```

Deschizi `http://localhost:5173/`.

Implicit UI-ul foloseste date mock (`src/data/mockScan.js`) deci merge
fara backend. Cand backend-ul lui B e viu pe `:8000`, pune intr-un fisier
nou `frontend/.env.local`:

```
VITE_USE_MOCK=0
```

si reporneste `npm run dev`. `vite.config.js` proxy-eaza `/api/*` catre
backend.

## Structura

```
src/
  App.jsx                  layout + state principal
  main.jsx                 entry
  index.css                Tailwind + focus rings
  components/
    Header.jsx             logo, RO/EN toggle, Simplu/Avansat toggle
    Tabs.jsx               navigare (Rezumat / Dispozitive / Probleme / Istoric)
    ScoreSemaphore.jsx     cerc 0-100 + verdict (icon + culoare + text)
    DeviceList.jsx         cards cu iconite per tip
    FindingsList.jsx       sortat high->info, "Cel mai periculos" marcat
    HistoryView.jsx        trend SVG + lista scanuri
    ScanControls.jsx       upload XML + buton Scan live (cu modal --confirm)
    ErrorBanner.jsx        pentru status: "error" (V7_broken.xml)
    AssistantPanel.jsx     chat wrapper peste /api/assistant/ask (D)
  data/mockScan.js         date demo (shape = docs/api_contract.json)
  lib/
    api.js                 fetch wrapper; VITE_USE_MOCK=0 ca sa dea pe real
    findings.js            sortare, culori, iconite, verdict din scor
  i18n/LanguageContext.jsx RO/EN toggle (localStorage)
```

## Decizii

- **Contract**: mock-ul respecta `docs/api_contract.json`. Backend-ul lui B
  trebuie sa returneze exact aceasta forma din `/api/scan/latest`,
  `/api/scan/upload`, `/api/scan/live`.
- **Verdict + summary**: calculate in UI (`lib/findings.js`) din scor si
  lista de findings, deci backend-ul nu trebuie sa le umple.
- **Accessibility** (NFR-08): text minim 16px, culoarea nu e singurul semnal
  (icon + eticheta + numar), focus rings vizibile, `role="tab"`,
  `aria-pressed`, `aria-live`.
- **RO + EN** (NFR-09): tot chrome-ul UI are ambele limbi; explicatiile
  findings-urilor vin pre-traduse de la backend (campurile
  `explanation_ro/en`, `fix_steps_ro/en`).
- **Securitate** (NFR-03): evidence-ul este randat ca text in `{}`, nu
  `dangerouslySetInnerHTML`. Niciun input nu se evalueaza.
