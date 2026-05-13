import { useState } from "react";

export function MiniCalendar({ eventDays }: { eventDays: Set<string> }) {
  const [cursor, setCursor] = useState(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), 1);
  });
  const todayKey = new Date().toISOString().slice(0, 10);
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const first = new Date(year, month, 1);
  const startDow = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  const rows: (number | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
  const monthName = cursor.toLocaleString("default", { month: "long", year: "numeric" });

  function key(d: number) {
    return `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  }

  return (
    <div className="minical">
      <div className="cal-head">
        <button className="btn small" onClick={() => setCursor(new Date(year, month - 1, 1))}>
          ‹
        </button>
        <span>{monthName}</span>
        <button className="btn small" onClick={() => setCursor(new Date(year, month + 1, 1))}>
          ›
        </button>
      </div>
      <table>
        <thead>
          <tr>
            {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
              <th key={i} style={{ fontSize: 10, color: "#888" }}>
                {d}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={ri}>
              {r.map((d, ci) => {
                let cls = "";
                if (d !== null) {
                  if (key(d) === todayKey) cls = "today";
                  else if (eventDays.has(key(d))) cls = "has-event";
                }
                return (
                  <td key={ci} className={cls}>
                    {d ?? ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
