import type { LogEntry } from "../api/client";

// Keep status chip colors aligned with the backend's log status values.
const statusStyles: Record<string, string> = {
  OPERATIONAL: "bg-green-500/20 text-green-400 border border-green-500/30",
  WARNING: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  ERROR: "bg-red-500/20 text-red-400 border border-red-500/30",
};

interface Props {
  logs: LogEntry[];
  total: number;
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
  loading: boolean;
}

export default function LogsTable({
  logs,
  total,
  page,
  pages,
  onPageChange,
  loading,
}: Props) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm text-gray-400">
        <span>{total.toLocaleString()} total records</span>
        <span>
          Page {page} of {pages}
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-800 text-gray-400 text-left">
              <th className="px-4 py-3 font-semibold">Timestamp</th>
              <th className="px-4 py-3 font-semibold">Machine ID</th>
              <th className="px-4 py-3 font-semibold">Temperature (°C)</th>
              <th className="px-4 py-3 font-semibold">Vibration</th>
              <th className="px-4 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {loading ? (
              <tr>
                <td colSpan={5} className="text-center py-12 text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-12 text-gray-500">
                  No logs found. Ingest the CSV to get started.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr
                  key={log.id}
                  className="hover:bg-gray-800/50 transition-colors even:bg-gray-900"
                >
                  <td className="px-4 py-2.5 text-gray-300 font-mono text-xs">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 font-semibold text-blue-400">
                    {log.machine_id}
                  </td>
                  <td className="px-4 py-2.5 text-gray-200">{log.temperature.toFixed(1)}</td>
                  <td className="px-4 py-2.5 text-gray-200">{log.vibration.toFixed(4)}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`text-xs font-bold uppercase px-2 py-1 rounded-full ${
                        statusStyles[log.status] ?? ""
                      }`}
                    >
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Hide pagination controls when the dataset fits on one page. */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-sm transition-colors"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-400 tabular-nums">
            {page} / {pages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
            className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-sm transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
