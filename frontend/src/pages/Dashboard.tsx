import { useState, useEffect, useCallback } from "react";
import { api, type LogsResponse, type AnalysisResult } from "../api/client";
import LogsTable from "../components/LogsTable";
import HealthStatusCard from "../components/HealthStatusCard";

const PAGE_SIZE = 50;

export default function Dashboard() {
  // Log table state.
  const [logsData, setLogsData] = useState<LogsResponse | null>(null);
  const [page, setPage] = useState(1);
  const [machineFilter, setMachineFilter] = useState("");
  const [machineIds, setMachineIds] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // CSV ingestion state.
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // AI analysis state.
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Load machine IDs for filter dropdown
  useEffect(() => {
    api
      .getMachineIds()
      .then((r) => setMachineIds(r.machine_ids))
      .catch(() => {});
  }, []);

  const fetchLogs = useCallback(
    async (p: number, filter: string) => {
      setLogsLoading(true);
      try {
        // Keep pagination and filtering logic in one place for reuse after ingestion.
        const data = await api.getLogs(p, PAGE_SIZE, filter || undefined);
        setLogsData(data);
      } catch {
        // ignore
      } finally {
        setLogsLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchLogs(page, machineFilter);
  }, [page, machineFilter, fetchLogs]);

  const handleIngest = async () => {
    setIngestLoading(true);
    setIngestMsg(null);
    try {
      const res = await api.ingestCsv();
      setIngestMsg({ type: "success", text: `✓ Ingested ${res.ingested} records from ${res.file}` });
      setPage(1);
      fetchLogs(1, machineFilter);
      // Refresh the filter options in case the ingested file changed the machine set.
      const ids = await api.getMachineIds();
      setMachineIds(ids.machine_ids);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setIngestMsg({ type: "error", text: `✗ Ingestion failed: ${msg}` });
    } finally {
      setIngestLoading(false);
    }
  };

  const handleAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisResult(null);
    setAnalysisError(null);
    try {
      // Clear stale results before showing a fresh analysis response.
      const res = await api.runAnalysis();
      if (res.status === "error") {
        setAnalysisError(res.error_message ?? "Analysis failed");
      } else {
        setAnalysisResult(res);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setAnalysisError(msg);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleFilterChange = (val: string) => {
    setMachineFilter(val);
    setPage(1);
  };

  return (
    <div className="space-y-8">
      {/* Page heading and primary actions. */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Manufacturing floor sensor logs and AI-powered maintenance predictions
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleIngest}
            disabled={ingestLoading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white rounded-lg font-medium transition-colors text-sm"
          >
            {ingestLoading ? (
              <span className="animate-spin">↻</span>
            ) : (
              <span>📥</span>
            )}
            Ingest CSV
          </button>

          <button
            onClick={handleAnalysis}
            disabled={analysisLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors text-sm"
          >
            {analysisLoading ? (
              <span className="animate-spin">⟳</span>
            ) : (
              <span>🤖</span>
            )}
            {analysisLoading ? "Analyzing…" : "Run AI Analysis"}
          </button>
        </div>
      </div>

      {/* Show the latest ingest outcome directly above the data table. */}
      {ingestMsg && (
        <div
          className={`px-4 py-3 rounded-lg text-sm font-medium ${
            ingestMsg.type === "success"
              ? "bg-green-500/10 text-green-400 border border-green-500/30"
              : "bg-red-500/10 text-red-400 border border-red-500/30"
          }`}
        >
          {ingestMsg.text}
        </div>
      )}

      {/* Surface AI failures separately from successful result cards. */}
      {analysisError && (
        <div className="px-4 py-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/30">
          <strong>Analysis Error:</strong> {analysisError}
        </div>
      )}

      {analysisResult?.top_machines?.top_3_at_risk && (
        <HealthStatusCard
          machines={analysisResult.top_machines.top_3_at_risk}
          createdAt={analysisResult.created_at}
          attemptCount={analysisResult.attempt_count}
        />
      )}

      {/* Filter and paginated log table. */}
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-xl font-bold text-white">Sensor Logs</h2>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-400">Filter:</label>
            <select
              value={machineFilter}
              onChange={(e) => handleFilterChange(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Machines</option>
              {machineIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>
        </div>

        <LogsTable
          logs={logsData?.logs ?? []}
          total={logsData?.total ?? 0}
          page={logsData?.page ?? 1}
          pages={logsData?.pages ?? 1}
          onPageChange={setPage}
          loading={logsLoading}
        />
      </div>
    </div>
  );
}
