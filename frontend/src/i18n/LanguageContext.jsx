import { createContext, useContext, useState, useMemo, useCallback } from "react";
import { setApiLanguage } from "../lib/api";

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
    scan_checking: "Verific la ce retea esti conectat...",
    scan_wifi: "Retea Wi-Fi",
    scan_no_wifi: "nu esti pe Wi-Fi",
    scan_target: "Se scaneaza",
    scan_refused_title: "Scanarea nu este permisa",
    scan_running_title: "Scanez reteaua",
    scan_phase_discovery: "Caut dispozitivele conectate",
    scan_phase_tcp: "Verific usile deschise (porturi TCP)",
    scan_phase_udp: "Verific usile deschise (porturi UDP)",
    scan_phase_services: "Aflu ce programe raspund",
    scan_phase_scripts: "Citesc paginile de administrare",
    scan_remaining: "Timp ramas",
    scan_max_time: "Dureaza de obicei intre 1 si 5 minute.",
    scan_cancel: "Opreste scanarea",
    scan_cancelling: "Se opreste...",
    scan_cancelled: "Scanarea a fost oprita. Nu s-a salvat nimic.",
    scan_failed: "Scanarea nu a reusit",
    scan_close: "Inchide",

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
    history_col_changes: "Schimbari",
    history_diff_button: "Diferente",
    history_first_scan: "primul scan",
    diff_score: "Scor",
    diff_resolved: "Probleme rezolvate",
    diff_new_findings: "Probleme noi",
    diff_devices_added: "Dispozitive noi",
    diff_devices_removed: "Dispozitive disparute",
    diff_ports_opened: "Porturi deschise acum",
    diff_ports_closed: "Porturi inchise acum",
    diff_nothing: "Nimic nu s-a schimbat fata de scanul anterior.",
    alert_title: "Ceva nou in reteaua ta",
    alert_since: "Fata de scanul anterior",
    alert_device_one: "dispozitiv nou",
    alert_devices: "dispozitive noi",
    alert_port_one: "port nou deschis",
    alert_ports: "porturi noi deschise",
    alert_problem_one: "problema noua",
    alert_problems: "probleme noi",
    alert_show: "Vezi toate schimbarile",
    alert_hide: "Ascunde schimbarile",
    history_delete: "Sterge istoricul meu",
    history_delete_confirm: "Esti sigur? Scanurile anterioare vor fi sterse.",

    error_title: "Nu am putut citi fisierul",
    error_broken:
      "Fisierul pare deteriorat sau nu este un XML nmap. Instrumentul nu s-a oprit.",
    error_technical: "Detaliu tehnic",
    loading: "Se incarca...",
    chat_placeholder: "Intreaba-ma: care este cel mai periculos?",
    chat_send: "Trimite",
    chat_disclaimer:
      "Raspunsurile se bazeaza doar pe scanul curent. Daca nu stiu, iti spun.",

    risk_scenario_label: "Ce s-ar putea intampla",
    device_rename: "Redenumeste",
    pdf_download: "Descarca raport PDF",
    diff_title: "Comparatie cu scanul anterior",
    narrator_title: "Rezumatul retelei tale",
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
    scan_checking: "Checking which network you are on...",
    scan_wifi: "Wi-Fi network",
    scan_no_wifi: "not on Wi-Fi",
    scan_target: "Will scan",
    scan_refused_title: "This scan is not allowed",
    scan_running_title: "Scanning your network",
    scan_phase_discovery: "Looking for connected devices",
    scan_phase_tcp: "Checking open doors (TCP ports)",
    scan_phase_udp: "Checking open doors (UDP ports)",
    scan_phase_services: "Finding out which programs answer",
    scan_phase_scripts: "Reading admin pages",
    scan_remaining: "Time left",
    scan_max_time: "This usually takes 1 to 5 minutes.",
    scan_cancel: "Stop the scan",
    scan_cancelling: "Stopping...",
    scan_cancelled: "The scan was stopped. Nothing was saved.",
    scan_failed: "The scan did not work",
    scan_close: "Close",

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
    history_col_changes: "Changes",
    history_diff_button: "Differences",
    history_first_scan: "first scan",
    diff_score: "Score",
    diff_resolved: "Resolved problems",
    diff_new_findings: "New problems",
    diff_devices_added: "New devices",
    diff_devices_removed: "Devices gone",
    diff_ports_opened: "Ports now open",
    diff_ports_closed: "Ports now closed",
    diff_nothing: "Nothing changed since the previous scan.",
    alert_title: "Something new on your network",
    alert_since: "Since the previous scan",
    alert_device_one: "new device",
    alert_devices: "new devices",
    alert_port_one: "newly opened port",
    alert_ports: "newly opened ports",
    alert_problem_one: "new problem",
    alert_problems: "new problems",
    alert_show: "Show all changes",
    alert_hide: "Hide changes",
    history_delete: "Delete my history",
    history_delete_confirm: "Are you sure? Previous scans will be deleted.",

    error_title: "Could not read the file",
    error_broken:
      "The file looks damaged or is not an nmap XML. The tool did not crash.",
    error_technical: "Technical detail",
    loading: "Loading...",
    chat_placeholder: "Ask me: what is the most dangerous?",
    chat_send: "Send",
    chat_disclaimer:
      "Answers use only the current scan. If I don't know, I'll tell you.",

    risk_scenario_label: "What could happen",
    device_rename: "Rename",
    pdf_download: "Download PDF report",
    diff_title: "Comparison with previous scan",
    narrator_title: "Your network summary",
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
  // Set during render (not in an effect) so even the very first API call is answered in this language.
  setApiLanguage(lang);

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
