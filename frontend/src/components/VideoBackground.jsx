export default function VideoBackground({ expert = false }) {
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const src = expert ? "/landscape-dark.png" : "/landscape-bg.png";

  const overlay = expert
    ? "linear-gradient(180deg, rgba(10,20,45,0.25) 0%, rgba(10,20,45,0.45) 100%)"
    : "linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.18) 60%, rgba(255,255,255,0.28) 100%)";

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <img src={src} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0" style={{ background: overlay }} />
    </div>
  );
}