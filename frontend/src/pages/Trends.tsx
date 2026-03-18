import { useState, useEffect } from "react";
import { api, type AnalysisResult } from "../api/client";
import HealthStatusCard from "../components/HealthStatusCard";

// Reuse compact pills in the history list to preview the ranked machines.
const riskPill: Record<string, string> = {
  high: "bg-red-500/20 text-red-400 border border-red-500/30",
  medium: "bg-orange-500/20 text-orange-400 border border-orange-500/30",
  low: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
};

function AnalysisRow({
  result,
  isExpanded,
  onToggle,
}: {
  result: AnalysisResult;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  // Each row can expand into the richer shared health-status card.
  const machines = result.top_machines?.top_3_at_risk ?? [];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Row header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-800/50 transition-colors text-left"
      >
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-sm text-gray-400 font-mono tabular-nums">
            {new Date(result.created_at).toLocaleString()}
          </span>

          {result.status === "error" ? (
            <span className="text-xs bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded-full font-bold uppercase">
              Failed
            </span>
          ) : (
            <div className="flex gap-2 flex-wrap">
              {machines.map((m) => (
                <span
                  key={m.machine_id}
                  className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                    riskPill[m.risk_level] ?? ""
                  }`}
                >
                  {m.machine_id}
                </span>
              ))}
            </div>
          )}

          <span className="text-xs text-gray-500">
            {result.attempt_count} AI attempt{result.attempt_count !== 1 ? "s" : ""}
          </span>
        </div>

        <span className="text-gray-400 ml-4 shrink-0">
          {isExpanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t border-gray-800 px-5 py-5">
          {result.status === "error" ? (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <strong>Error:</strong> {result.error_message}
            </div>
          ) : machines.length > 0 ? (
            <HealthStatusCard
              machines={machines}
              createdAt={result.created_at}
              attemptCount={result.attempt_count}
            />
          ) : (
            <p className="text-gray-500 text-sm">No machine data available.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function Trends() {
  // History page state is intentionally simple: fetch once on mount and expand one row at a time.
  const [history, setHistory] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    // Default to expanding the newest result so the user sees detail immediately.
    api
      .getHistory()
      .then((r) => {
        setHistory(r.results);
        if (r.results.length > 0) setExpandedId(r.results[0].id);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load history");
      })
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: number) =>
    setExpandedId((prev) => (prev === id ? null : id));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Trends</h1>
        <p className="text-gray-400 mt-1">
          Historical AI analysis results — at-risk machines over time
        </p>
      </div>

      {loading && (
        <div className="text-center py-20 text-gray-500">Loading history…</div>
      )}

      {error && (
        <div className="px-4 py-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/30">
          {error}
        </div>
      )}

      {!loading && !error && history.length === 0 && (
        <div className="text-center py-20 text-gray-500 space-y-2">
          <p className="text-4xl">📊</p>
          <p>No analyses yet.</p>
          <p className="text-sm">
            Go to the Dashboard, ingest the CSV, and run an AI analysis.
          </p>
        </div>
      )}

      {!loading && history.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">{history.length} analysis run{history.length !== 1 ? "s" : ""}</p>
          {history.map((result) => (
            <AnalysisRow
              key={result.id}
              result={result}
              isExpanded={expandedId === result.id}
              onToggle={() => toggle(result.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
