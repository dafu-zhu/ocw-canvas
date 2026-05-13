/**
 * The OCW Canvas brand mark — an open "C" arc with a filled square inset.
 *
 * Visual logic: the "C" is for Courseware (and the open arc reads as "open"),
 * the inset square is the canvas. Geometric, single-color, currentColor-driven
 * so it inherits the surrounding text color. Sits at a similar weight to
 * Canvas LMS's wordmark glyph without copying its compass-rose shape.
 */
export function BrandMark({ size = 28 }: { size?: number }) {
  // Arc geometry: a 270° "C" opening to the right. With viewBox 24×24, center (12,12),
  // outer radius 9; the two arc endpoints sit at angles −45° and +45°.
  // (12 + 9·cos(−45°), 12 + 9·sin(−45°)) ≈ (18.36, 5.64) etc.
  const stroke = Math.max(1.6, size * 0.085);
  // Inner square: 6×6 centered, with a tiny corner radius for refinement at large sizes.
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      role="img"
      aria-label="OCW Canvas"
      style={{ display: "inline-block", verticalAlign: "middle" }}
    >
      <path
        d="M 18.36 5.64 A 9 9 0 1 0 18.36 18.36"
        stroke="currentColor"
        strokeWidth={stroke}
        fill="none"
        strokeLinecap="round"
      />
      <rect x="9" y="9" width="6" height="6" rx="0.6" fill="currentColor" />
    </svg>
  );
}

/** The wordmark used at the top of the login/reset pages. */
export function BrandWordmark({ size = 28 }: { size?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 14 }}>
      <BrandMark size={size} />
      <span style={{ fontWeight: 700, letterSpacing: "0.04em" }}>OCW CANVAS</span>
    </span>
  );
}
