import { createContext, useContext, useState, useMemo, useCallback } from "react";

// UI chrome strings only. Finding explanations and fix steps come from the
// backend (person D's templates / LLM) already translated, in two fields
// explanation_ro / explanation_en etc.
const dict = {
  ro: {
    app_title: "Scaner de retea",
    app_subtitle: "Retele mai sigure, pe intelesul tuturor",
    lang_toggle: "EN",
    lang_toggle_aria: "Schimba limba in engleza",
    mode_simple: "Simplu",
    mode_expert: "Avansat",
    mode_toggle_aria: "Comuta modul simplu / avansat",

    tab_overview: "Rezumat",
    tab_devices: "Dispozitive",
    tab_findings: "Probleme",
    tab_history: "Istoric",

    upload_button: "Incarca scan (XML)",
    upload_hint: "Trage un fisier nmap XML aici sau fa click.",
    scan_button: "Scaneaza reteaua ta",
    scan_confirm_title: "Confirma scanarea live",
    scan_confirm_body:
      "Vei scana subreteaua la care este conectat laptopul tau. Nu vei scana retele publice sau ale altora.",
    scan_confirm_yes: "Da, scaneaza",
    scan_confirm_no: "Anuleaza",

    score_label: "Scor de siguranta",
    score_of_100: "din 100",
    verdict_safe: "In regula",
    verdict_watch: "Atentie",
    verdict_at_risk: "Risc mare",
    verdict_safe_desc: "Nu am gasit probleme importante.",
    verdict_watch_desc: "Cateva lucruri de rezolvat. Incepe cu cel mai de sus.",
    verdict_at_risk_desc: "Rezolva problemele rosii cat mai repede.",

    devices_count: "dispozitive",
    device_count_one: "dispozitiv",
    open_ports: "porturi deschise",
    findings_count: "probleme",
    finding_count_one: "problema",
    no_mac: "fara MAC",
    no_vendor: "producator necunoscut",
    no_hostname: "fara nume",

    severity_high: "Mare",
    severity_medium: "Medie",
    severity_low: "Mica",
    severity_info: "Info",
    severity_safe: "Sigur",

    finding_port: "Port",
    finding_evidence: "Dovada",
    finding_fix_title: "Cum rezolvi",
    finding_expand: "Vezi pasii",
    finding_collapse: "Ascunde pasii",
    finding_most_dangerous: "Cel mai periculos",

    history_title: "Istoric scanuri",
    history_empty: "Nu exista scanuri anterioare inca.",
    history_resolved: "Probleme rezolvate",
    history_new: "Probleme noi",
    history_devices_new: "Dispozitive noi",
    history_score_trend: "Evolutia scorului",
    history_col_file: "Fisier",
    history_col_date: "Data",
    history_col_findings: "Probleme",
    history_col_score: "Scor",
    history_unreadable: "EROARE",
    history_delete: "Sterge istoricul meu",
    history_delete_confirm: "Esti sigur? Scanurile anterioare vor fi sterse.",

    error_title: "Nu am putut citi fisierul",
    error_broken:
      "Fisierul pare deteriorat sau nu este un XML nmap. Instrumentul nu s-a oprit.",
    loading: "Se incarca...",
    chat_placeholder: "Intreaba-ma: care este cel mai periculos?",
    chat_send: "Trimite",
    chat_disclaimer:
      "Raspunsurile se bazeaza doar pe scanul curent. Daca nu stiu, iti spun.",
  },
  en: {
    app_title: "Network scanner",
    app_subtitle: "Secure networks, simply explained",
    lang_toggle: "RO",
    lang_toggle_aria: "Switch language to Romanian",
    mode_simple: "Simple",
    mode_expert: "Expert",
    mode_toggle_aria: "Toggle simple / expert mode",

    tab_overview: "Overview",
    tab_devices: "Devices",
    tab_findings: "Problems",
    tab_history: "History",

    upload_button: "Upload scan (XML)",
    upload_hint: "Drop an nmap XML file here or click.",
    scan_button: "Scan your network",
    scan_confirm_title: "Confirm live scan",
    scan_confirm_body:
      "You will scan the subnet your laptop is on. You will not scan public or other people's networks.",
    scan_confirm_yes: "Yes, scan",
    scan_confirm_no: "Cancel",

    score_label: "Safety score",
    score_of_100: "out of 100",
    verdict_safe: "OK",
    verdict_watch: "Watch out",
    verdict_at_risk: "High risk",
    verdict_safe_desc: "No important problems found.",
    verdict_watch_desc: "A few things to fix. Start with the top one.",
    verdict_at_risk_desc: "Fix the red problems as soon as you can.",

    devices_count: "devices",
    device_count_one: "device",
    open_ports: "open ports",
    findings_count: "problems",
    finding_count_one: "problem",
    no_mac: "no MAC",
    no_vendor: "unknown vendor",
    no_hostname: "no name",

    severity_high: "High",
    severity_medium: "Medium",
    severity_low: "Low",
    severity_info: "Info",
    severity_safe: "Safe",

    finding_port: "Port",
    finding_evidence: "Evidence",
    finding_fix_title: "How to fix",
    finding_expand: "Show steps",
    finding_collapse: "Hide steps",
    finding_most_dangerous: "Most dangerous",

    history_title: "Scan history",
    history_empty: "No previous scans yet.",
    history_resolved: "Resolved problems",
    history_new: "New problems",
    history_devices_new: "New devices",
    history_score_trend: "Score trend",
    history_col_file: "File",
    history_col_date: "Date",
    history_col_findings: "Problems",
    history_col_score: "Score",
    history_unreadable: "ERROR",
    history_delete: "Delete my history",
    history_delete_confirm: "Are you sure? Previous scans will be deleted.",

    error_title: "Could not read the file",
    error_broken:
      "The file looks damaged or is not an nmap XML. The tool did not crash.",
    loading: "Loading...",
    chat_placeholder: "Ask me: what is the most dangerous?",
    chat_send: "Send",
    chat_disclaimer:
      "Answers use only the current scan. If I don't know, I'll tell you.",
  },
};

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      return localStorage.getItem("lang") || "ro";
    } catch {
      return "ro";
    }
  });

  const toggle = useCallback(() => {
    setLang((prev) => {
      const next = prev === "ro" ? "en" : "ro";
      try {
        localStorage.setItem("lang", next);
      } catch {
        // ignore private-window / blocked storage
      }
      return next;
    });
  }, []);

  const t = useCallback((key) => dict[lang][key] ?? key, [lang]);

  const value = useMemo(() => ({ lang, t, toggle }), [lang, t, toggle]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside LanguageProvider");
  return ctx;
}
