const HEALTH_COLORS: Record<string, string> = {
  minor: "bg-green-100 text-green-800",
  moderate: "bg-yellow-100 text-yellow-800",
  serious: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const MAINT_COLORS: Record<string, string> = {
  advisory: "bg-blue-100 text-blue-800",
  degraded: "bg-yellow-100 text-yellow-800",
  critical: "bg-orange-100 text-orange-800",
  down: "bg-red-100 text-red-800",
};

export function SeverityBadge({
  severity,
  type = "health",
}: {
  severity: string;
  type?: "health" | "maintenance";
}) {
  const palette = type === "health" ? HEALTH_COLORS : MAINT_COLORS;
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wide ${
        palette[severity] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {severity}
    </span>
  );
}
