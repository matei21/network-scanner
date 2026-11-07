// Full-viewport landscape backdrop. Static illustration — no video decode
// or battery cost. Soft white overlay keeps text legible without washing
// out the sky.

export default function VideoBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <img
        src="/landscape-bg.png"
        alt=""
        className="h-full w-full object-cover"
      />
      {/* Very light wash so the illustration shows through and the cards
          (which are nearly solid) still have enough contrast on top. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.18) 60%, rgba(255,255,255,0.28) 100%)",
        }}
      />
    </div>
  );
}
