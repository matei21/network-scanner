import { useEffect, useState, useMemo } from "react";
import { LanguageProvider, useLanguage } from "./i18n/LanguageContext";
import Header from "./components/Header";
import VideoBackground from "./components/VideoBackground";
import ScoreSemaphore from "./components/ScoreSemaphore";
import DeviceList from "./components/DeviceList";
import FindingsList from "./components/FindingsList";
import HistoryView from "./components/HistoryView";
import ErrorBanner from "./components/ErrorBanner";
import MrPotato from "./components/MrPotato";
import { getLatestScan, uploadXml, runLiveScan, deleteHistory } from "./lib/api";
import { flattenFindings, summarySentence } from "./lib/findings";

function AppInner() {
  const { t, lang } = useLanguage();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("overview");
  const [expert, setExpert] = useState(false);

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
    <div className="min-h-full flex flex-col relative" lang={lang}>
      <VideoBackground />
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
            {scan && scan.status !== "error" && (
              <div className="bg-white rounded-2xl border border-gray-200 p-4">
                <p className="text-lg">{summarySentence(scan, lang)}</p>
              </div>
            )}
            {scan && scan.status !== "error" && findingCount > 0 && (
              <div>
                <h3 className="on-video font-semibold mb-2 text-xl">{t("tab_findings")}</h3>
                <FindingsList scan={scan} expert={expert} />
              </div>
            )}
          </div>
        )}

        {tab === "devices" && (
          <DeviceList devices={scan?.devices || []} expert={expert} />
        )}

        {tab === "findings" && (
          <FindingsList scan={scan} expert={expert} />
        )}

        {tab === "history" && (
          <HistoryView scan={scan} onDelete={onDeleteHistory} />
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
