import type { AtRiskMachine } from "../api/client";

// Map each risk level to a consistent visual treatment across the UI.
const riskColors: Record<string, { badge: string; border: string; glow: string }> = {
  high: {
    badge: "bg-red-500/20 text-red-400 border border-red-500/40",
    border: "border-red-500/40",
    glow: "shadow-red-900/30",
  },
  medium: {
    badge: "bg-orange-500/20 text-orange-400 border border-orange-500/40",
    border: "border-orange-500/40",
    glow: "shadow-orange-900/30",
  },
  low: {
    badge: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40",
    border: "border-yellow-500/40",
    glow: "shadow-yellow-900/20",
  },
};

function RiskBadge({ level }: { level: string }) {
  // Unknown values fall back to the lowest-risk styling instead of crashing the UI.
  const color = riskColors[level] ?? riskColors.low;
  return (
    <span className={`text-xs font-bold uppercase tracking-widest px-2 py-1 rounded-full ${color.badge}`}>
      {level} risk
    </span>
  );
}

function MachineCard({ machine, rank }: { machine: AtRiskMachine; rank: number }) {
  // Reuse the same palette for the card frame and the risk badge.
  const color = riskColors[machine.risk_level] ?? riskColors.low;

  return (
    <div
      className={`bg-gray-800 border ${color.border} rounded-xl p-5 shadow-lg ${color.glow} flex flex-col gap-3`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center font-bold text-sm text-gray-300">
            #{rank}
          </div>
          <h3 className="text-lg font-bold text-white">{machine.machine_id}</h3>
        </div>
        <RiskBadge level={machine.risk_level} />
      </div>

      <p className="text-gray-300 text-sm leading-relaxed">{machine.reason}</p>

      <div className="flex flex-wrap gap-2">
        {machine.affected_sensors.map((sensor) => (
          <span
            key={sensor}
            className="bg-gray-700 text-gray-300 text-xs px-2 py-1 rounded-md font-mono"
          >
            {sensor}
          </span>
        ))}
      </div>
    </div>
  );
}

interface Props {
  machines: AtRiskMachine[];
  createdAt?: string;
  attemptCount?: number;
}

export default function HealthStatusCard({ machines, createdAt, attemptCount }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <span>🤖</span> AI Health Status
        </h2>
        <div className="flex items-center gap-4 text-xs text-gray-400">
          {attemptCount !== undefined && (
            <span>AI attempts: {attemptCount}</span>
          )}
          {createdAt && (
            <span>
              {new Date(createdAt).toLocaleString()}
            </span>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-400">
        Top 3 machines identified as at-risk by AI analysis of sensor patterns:
      </p>
      {/* The backend guarantees three items on success, but this still renders safely for fewer. */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {machines.map((m, i) => (
          <MachineCard key={m.machine_id} machine={m} rank={i + 1} />
        ))}
      </div>
    </div>
  );
}
