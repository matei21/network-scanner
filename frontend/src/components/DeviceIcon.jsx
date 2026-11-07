import { useState } from "react";
import { deviceIconSrc, deviceEmoji } from "../lib/findings";

// Renders a device icon. Prefers /public/devices/<type>.png the user supplied;
// if the image fails to load (file missing), falls back to the emoji so the
// UI never shows a broken-image box.
export default function DeviceIcon({ type, size = 56 }) {
  const [broken, setBroken] = useState(false);
  if (broken) {
    return (
      <span
        aria-hidden
        style={{ fontSize: Math.round(size * 0.6), lineHeight: 1 }}
      >
        {deviceEmoji(type)}
      </span>
    );
  }
  return (
    <img
      src={deviceIconSrc(type)}
      alt=""
      aria-hidden
      width={size}
      height={size}
      style={{ width: size, height: size, objectFit: "contain" }}
      onError={() => setBroken(true)}
    />
  );
}
