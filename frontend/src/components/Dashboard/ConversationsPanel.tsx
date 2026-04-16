interface Props {
  total: number;
  successful: number;
  failed: number;
  successRate: number;
  uniqueUsers: number;
  avgPerUser: number;
  periodFrom: string | null;
  periodTo: string | null;
}

function fmt(n: number): string {
  return new Intl.NumberFormat("es-CO").format(n);
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface BarProps {
  label: string;
  value: number;
  total: number;
  color: string;
}

function ProgressBar({ label, value, total, color }: BarProps) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-500 dark:text-gray-400">{label}</span>
        <span className="font-semibold text-gray-700 dark:text-gray-300">
          {fmt(value)}{" "}
          <span className="font-normal text-gray-400">({pct}%)</span>
        </span>
      </div>
      <div className="h-2 bg-gray-100 dark:bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function ConversationsPanel({
  total,
  successful,
  failed,
  successRate,
  uniqueUsers,
  avgPerUser,
  periodFrom,
  periodTo,
}: Props) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-gray-100 dark:border-zinc-800 p-6 shadow-sm flex flex-col gap-5">
      <div>
        <h3 className="text-sm font-semibold text-gray-800 dark:text-white">
          Conversaciones
        </h3>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
          {fmtDate(periodFrom)} — {fmtDate(periodTo)}
        </p>
      </div>

      {/* Main stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <p className="text-3xl font-bold text-[#004481] dark:text-blue-400">
            {fmt(total)}
          </p>
          <p className="text-xs text-gray-400 mt-1">Consultas totales</p>
        </div>
        <div className="text-center">
          <p className="text-3xl font-bold text-gray-900 dark:text-white">
            {fmt(uniqueUsers)}
          </p>
          <p className="text-xs text-gray-400 mt-1">Usuarios únicos</p>
        </div>
        <div className="text-center">
          <p
            className={`text-3xl font-bold ${
              successRate >= 0.95
                ? "text-green-600"
                : successRate >= 0.8
                ? "text-amber-600"
                : "text-red-500"
            }`}
          >
            {total > 0 ? `${Math.round(successRate * 100)}%` : "—"}
          </p>
          <p className="text-xs text-gray-400 mt-1">Tasa de éxito</p>
        </div>
      </div>

      {/* Progress bars */}
      <div className="flex flex-col gap-3 pt-2 border-t border-gray-100 dark:border-zinc-800">
        <ProgressBar
          label="Exitosas"
          value={successful}
          total={total}
          color="#004481"
        />
        <ProgressBar
          label="Con error"
          value={failed}
          total={total}
          color="#ef4444"
        />
      </div>

      {/* Avg per user */}
      {uniqueUsers > 0 && (
        <p className="text-xs text-gray-400 pt-1 border-t border-gray-100 dark:border-zinc-800">
          Promedio por usuario:{" "}
          <span className="font-semibold text-gray-700 dark:text-gray-300">
            {avgPerUser.toFixed(1)} consultas
          </span>
        </p>
      )}
    </div>
  );
}
