export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <div className="center-empty">{label}</div>;
}
