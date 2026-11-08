import { useEffect, useState, useMemo } from "react";
import { LanguageProvider, useLanguage } from "./i18n/LanguageContext";
import Header from "./components/Header";
import VideoBackground from "./components/VideoBackground";
import ScoreSemaphore from "./components/ScoreSemaphore";
import DeviceList from "./components/DeviceList";
import FindingsList from "./components/FindingsList";
import NetworkMap from "./components/NetworkMap";
import MapLegend from "./components/MapLegend";
import HistoryView from "./components/HistoryView";
import ErrorBanner from "./components/ErrorBanner";
import MrPotato from "./components/MrPotato";
import ScanNarrator from "./components/ScanNarrator";
import DiffNarrator from "./components/DiffNarrator";
import PdfDownload from "./components/PdfDownload";
import AISettings from "./components/AISettings";
import { getLatestScan, uploadXml, runLiveScan, deleteHistory, getDeviceNames, suggestDeviceNames } from "./lib/api";
import { flattenFindings, summarySentence } from "./lib/findings";

function AppInner() {
  const { t, lang } = useLanguage();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("overview");
  const [expert, setExpert] = useState(false);
  const [deviceNames, setDeviceNames] = useState({});
  const [suggestedNames, setSuggestedNames] = useState({});

  useEffect(() => {
    let cancelled = false;
    getLatestScan()
      .then((s) => !cancelled && setScan(s))
      .catch((e) =>
        !cancelled &&
        setScan({ status: "error", error: String(e.message || e), devices: [], history: [] })
      )
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!scan?.scan_id) return;
    getDeviceNames().then(setDeviceNames).catch(() => {});
    suggestDeviceNames(scan.scan_id, lang).then(setSuggestedNames).catch(() => {});
  }, [scan?.scan_id, lang]);

  function handleNameSaved(ip, name) {
    setDeviceNames((prev) => ({ ...prev, [ip]: { ...prev[ip], custom_name: name } }));
  }

  async function onUpload(file) {
    setBusy(true);
    try {
      const s = await uploadXml(file);
      setScan(s);
      setTab("overview");
    } catch (e) {
      setScan({ status: "error", error: String(e.message || e), devices: [], history: [] });
    } finally {
      setBusy(false);
    }
  }

  async function onLiveScan() {
    setBusy(true);
    try {
      const s = await runLiveScan({ confirm: true });
      setScan(s);
      setTab("overview");
    } catch (e) {
      setScan({ status: "error", error: String(e.message || e), devices: [], history: [] });
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteHistory() {
    await deleteHistory();
    setScan((s) => (s ? { ...s, history: [] } : s));
  }

  const findingCount = useMemo(() => flattenFindings(scan).length, [scan]);
  const deviceCount = useMemo(() => {
    const seen = new Set();
    for (const d of scan?.devices || []) seen.add(`${d.ip}|${d.mac || ""}`);
    return seen.size;
  }, [scan]);

  const tabs = [
    { id: "overview", label: t("tab_overview") },
    { id: "devices", label: t("tab_devices"), count: deviceCount },
    { id: "findings", label: t("tab_findings"), count: findingCount },
    { id: "history", label: t("tab_history") },
  ];

  return (
    <div className="min-h-full flex flex-col relative" lang={lang} data-mode={expert ? "expert" : "simple"}>
      <VideoBackground expert={expert} />
      <Header
        expert={expert}
        onToggleExpert={() => setExpert((v) => !v)}
        tab={tab}
        onTabChange={setTab}
        tabs={tabs}
        onUpload={onUpload}
        onLiveScan={onLiveScan}
        busy={busy}
      />
      <main className="max-w-6xl w-full mx-auto px-4 py-5 flex-1 space-y-5">
        <ErrorBanner scan={scan} />

        {tab === "overview" && (
          <div className="space-y-5">
            <ScoreSemaphore score={scan?.score} scan={scan} loading={loading} />
            {scan && scan.status !== "error" && scan.scan_id && (
              <ScanNarrator scanId={scan.scan_id} />
            )}
            {scan && scan.status !== "error" && (
              <NetworkMap devices={scan?.devices || []} />
          )}
          {scan && scan.status !== "error" && (
              <MapLegend devices={scan?.devices || []} />
          )}
          </div>
        )}

        {tab === "devices" && (
          <DeviceList
            devices={scan?.devices || []}
            expert={expert}
            deviceNames={deviceNames}
            onNameSaved={handleNameSaved}
            suggestedNames={suggestedNames}
          />
        )}

        {tab === "findings" && (
          <FindingsList scan={scan} expert={expert} />
        )}

        {tab === "history" && (
          <>
            {scan?.scan_id && <DiffNarrator scanId={scan.scan_id} />}
            <HistoryView scan={scan} onDelete={onDeleteHistory} />
          </>
        )}
        {/* Bottom section: PDF download + AI settings */}
        {scan && scan.status !== "error" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div className="flex items-center">
              <PdfDownload scanId={scan.scan_id} />
            </div>
            <AISettings />
          </div>
        )}
      </main>
      <footer className="text-center text-xs py-4">
        R Systems Hackathon 2026 · Secure Networks, Simply Explained
      </footer>
      <MrPotato scanId={scan?.scan_id} />
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AppInner />
    </LanguageProvider>
  );
}
