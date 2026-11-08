import { useEffect, useRef, useState } from "react";
import { Loader2, Radar, ShieldAlert, Wifi, XCircle } from "lucide-react";
import { useLanguage } from "../i18n/LanguageContext";
import { cancelLiveScan, getLiveScan, getLiveScanPreview, startLiveScan } from "../lib/api";

// Live scan: shows WHAT will be scanned and on WHICH Wi-Fi before asking, then a progress bar with Cancel.
export default function LiveScanDialog({ onClose, onDone }) {
  const { t } = useLanguage();
  const [stage, setStage] = useState("checking"); // checking | confirm | running | failed | cancelled
  const [preview, setPreview] = useState(null);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const timer = useRef(null);
  const running = stage === "running";

  useEffect(() => {
    getLiveScanPreview()
      .then((p) => {
        setPreview(p);
        setStage("confirm");
      })
      .catch((e) => {
        setError(String(e.message || e));
        setStage("failed");
      });
    return () => clearTimeout(timer.current);
  }, []);

  function fail(message) {
    setError(message);
    setStage("failed");
  }

  function poll(jobId) {
    timer.current = setTimeout(async () => {
      try {
        const j = await getLiveScan(jobId);
        setJob(j);
        if (j.status === "running") return poll(jobId);
        if (j.status === "done") return onDone(j.result);
        if (j.status === "cancelled") return setStage("cancelled");
        fail(j.error || t("scan_failed"));
      } catch (e) {
        fail(String(e.message || e));
      }
    }, 1500);
  }

  async function onStart() {
    setStage("running");
    try {
      const j = await startLiveScan();
      setJob(j);
      poll(j.job_id);
    } catch (e) {
      fail(String(e.message || e));
    }
  }

  async function onCancel() {
    if (!job?.job_id) return;
    setCancelling(true);
    try {
      await cancelLiveScan(job.job_id);
    } catch {
      // polling reports the final state anyway
    }
  }

  const percent = Math.round(job?.percent ?? 0);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="live-scan-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !running) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape" && !running) onClose();
      }}
    >
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl text-base">
        <h2 id="live-scan-title" className="text-xl font-semibold flex items-center gap-2">
          <Radar className="w-5 h-5" aria-hidden />
          {running ? t("scan_running_title") : t("scan_confirm_title")}
        </h2>

        {stage === "checking" && (
          <p className="mt-3 flex items-center gap-2 text-gray-800">
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
            {t("scan_checking")}
          </p>
        )}

        {preview && stage !== "checking" && (
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-gray-800">
            <dt className="flex items-center gap-1 font-medium">
              <Wifi className="w-4 h-4" aria-hidden />
              {t("scan_wifi")}
            </dt>
            <dd className="break-all">{preview.ssid || t("scan_no_wifi")}</dd>
            <dt className="font-medium">{t("scan_target")}</dt>
            <dd className="tabular-nums">{preview.target || "-"}</dd>
          </dl>
        )}

        {stage === "confirm" && preview?.allowed && (
          <p className="mt-3 text-gray-800">{t("scan_confirm_body")}</p>
        )}

        {stage === "confirm" && preview && !preview.allowed && (
          <div role="alert" className="mt-3 flex gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-red-900">
            <ShieldAlert className="w-5 h-5 shrink-0" aria-hidden />
            <div>
              <div className="font-semibold">{t("scan_refused_title")}</div>
              <div>{preview.reason}</div>
            </div>
          </div>
        )}

        {running && (
          <div className="mt-4">
            <div className="flex justify-between text-gray-800">
              <span>{t(`scan_phase_${job?.phase || "discovery"}`)}</span>
              <span className="tabular-nums font-semibold">{percent}%</span>
            </div>
            <div
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              aria-label={t("scan_running_title")}
              className="mt-2 h-3 w-full rounded-full bg-gray-200 overflow-hidden"
            >
              <div className="h-full bg-blue-700 transition-all duration-700" style={{ width: `${percent}%` }} />
            </div>
            <p className="mt-2 text-gray-700">
              {job?.remaining ? `${t("scan_remaining")}: ${job.remaining}` : t("scan_max_time")}
            </p>
          </div>
        )}

        {stage === "failed" && (
          <div role="alert" className="mt-3 flex gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-red-900">
            <XCircle className="w-5 h-5 shrink-0" aria-hidden />
            <div>
              <div className="font-semibold">{t("scan_failed")}</div>
              <div className="break-words">{error}</div>
            </div>
          </div>
        )}

        {stage === "cancelled" && <p className="mt-3 text-gray-800">{t("scan_cancelled")}</p>}

        <div className="mt-5 flex gap-3 justify-end">
          {running ? (
            <button
              type="button"
              onClick={onCancel}
              disabled={cancelling || !job?.job_id}
              className="px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 disabled:opacity-60"
            >
              {cancelling ? t("scan_cancelling") : t("scan_cancel")}
            </button>
          ) : (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50"
            >
              {stage === "confirm" ? t("scan_confirm_no") : t("scan_close")}
            </button>
          )}
          {stage === "confirm" && (
            <button
              type="button"
              onClick={onStart}
              disabled={!preview?.allowed}
              className="px-4 py-2 rounded-lg bg-red-700 text-white hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("scan_confirm_yes")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
