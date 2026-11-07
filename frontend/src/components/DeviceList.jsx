import { useLanguage } from "../i18n/LanguageContext";
import { deviceIcon } from "../lib/findings";

function maskedMac(mac) {
  return mac || null;
}

function DeviceCard({ device, expert }) {
  const { t } = useLanguage();
  const findingsCount = device.findings?.length || 0;
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex gap-4 items-start">
      <div
        className="w-14 h-14 shrink-0 rounded-full bg-gray-100 flex items-center justify-center text-3xl"
        aria-hidden
      >
        {deviceIcon(device.icon || device.type)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <span className="font-semibold text-lg">
            {device.hostname || t("no_hostname")}
          </span>
          <span className="text-gray-600 tabular-nums">{device.ip}</span>
        </div>
        <div className="mt-1 text-sm text-gray-700 flex flex-wrap gap-x-4 gap-y-1">
          <span>{device.vendor || t("no_vendor")}</span>
          <span className="tabular-nums">
            {maskedMac(device.mac) || t("no_mac")}
          </span>
          <span>
            {(device.open_ports?.length || 0)} {t("open_ports")}
          </span>
        </div>
        {expert && device.open_ports?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {device.open_ports.map((p) => (
              <span
                key={`${p.protocol}/${p.port}`}
                className="text-xs px-2 py-0.5 bg-gray-100 rounded border border-gray-200 tabular-nums"
                title={[p.service, p.product, p.version].filter(Boolean).join(" ")}
              >
                {p.port}/{p.protocol}
                {p.service ? ` · ${p.service}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>
      {findingsCount > 0 && (
        <span
          className="shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-50 text-risk-high border border-red-200 text-sm"
          aria-label={`${findingsCount} ${t("findings_count")}`}
        >
          <span className="w-2 h-2 rounded-full bg-risk-high" aria-hidden />
          {findingsCount} {t("findings_count")}
        </span>
      )}
    </div>
  );
}

export default function DeviceList({ devices, expert }) {
  const { t } = useLanguage();
  // Dedupe by ip+mac (backend may repeat a device per findings group).
  const seen = new Map();
  for (const d of devices || []) {
    const key = `${d.ip}|${d.mac || ""}`;
    const prev = seen.get(key);
    if (prev) {
      const portKey = (p) => `${p.protocol}/${p.port}`;
      const existing = new Set((prev.open_ports || []).map(portKey));
      for (const p of d.open_ports || []) {
        if (!existing.has(portKey(p))) prev.open_ports.push(p);
      }
      prev.findings = [...(prev.findings || []), ...(d.findings || [])];
    } else {
      seen.set(key, {
        ...d,
        open_ports: [...(d.open_ports || [])],
        findings: [...(d.findings || [])],
      });
    }
  }
  const list = Array.from(seen.values());

  return (
    <div className="space-y-3">
      <div className="text-sm text-gray-700">
        {list.length} {list.length === 1 ? t("device_count_one") : t("devices_count")}
      </div>
      {list.map((d) => (
        <DeviceCard key={`${d.ip}|${d.mac || ""}`} device={d} expert={expert} />
      ))}
    </div>
  );
}
