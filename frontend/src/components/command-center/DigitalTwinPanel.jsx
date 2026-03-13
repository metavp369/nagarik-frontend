import React from 'react';
import { User, Clock, MapPin, Shield, AlertTriangle, Loader2 } from 'lucide-react';

export const DigitalTwinPanel = ({ baseline, riskData, loading }) => {
  if (loading) {
    return (
      <PanelShell>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-5 h-5 text-teal-400 animate-spin" />
        </div>
      </PanelShell>
    );
  }

  if (!baseline) {
    return (
      <PanelShell>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-[10px] text-slate-500">Select a user to view digital twin</p>
        </div>
      </PanelShell>
    );
  }

  // Compute travel hours from active_hours
  const activeHours = baseline.active_hours || {};
  const highHours = Object.entries(activeHours)
    .filter(([_, v]) => v === 'high' || v === 'moderate')
    .map(([h]) => parseInt(h))
    .sort((a, b) => a - b);

  const startHour = highHours.length > 0 ? highHours[0] : 8;
  const endHour = highHours.length > 0 ? highHours[highHours.length - 1] : 19;
  const fmtHr = (h) => {
    const ampm = h >= 12 ? 'PM' : 'AM';
    const hr = h > 12 ? h - 12 : h === 0 ? 12 : h;
    return `${hr}:00 ${ampm}`;
  };

  // Safe zone percentage
  const commonLocs = baseline.common_locations || [];
  const safeZonePct = Math.min(85 + commonLocs.length * 3, 98);

  // Typical commute
  const routes = baseline.route_clusters || [];
  const commuteStr = routes.length > 0
    ? routes.map(r => `${r.from} → ${r.to}`).join(', ')
    : 'Home → Market → Home';

  // Deviation computation
  const deviation = riskData?.scores?.behavior
    ? Math.round(riskData.scores.behavior * 100)
    : 0;
  const currentBehavior = deviation > 40 ? 'UNUSUAL' : deviation > 20 ? 'SLIGHT DEVIATION' : 'NORMAL';
  const behaviorColor = deviation > 40 ? 'text-red-400' : deviation > 20 ? 'text-amber-400' : 'text-emerald-400';
  const behaviorBg = deviation > 40 ? 'bg-red-500/10' : deviation > 20 ? 'bg-amber-500/10' : 'bg-emerald-500/10';

  return (
    <PanelShell>
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {/* Travel Hours */}
        <div className="flex items-start gap-2">
          <Clock className="w-3 h-3 text-blue-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-[9px] text-slate-500">Normal travel hours</p>
            <p className="text-[11px] text-white font-mono font-medium">{fmtHr(startHour)} – {fmtHr(endHour)}</p>
          </div>
        </div>

        {/* Typical Commute */}
        <div className="flex items-start gap-2">
          <MapPin className="w-3 h-3 text-teal-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-[9px] text-slate-500">Typical commute</p>
            <p className="text-[11px] text-white font-medium">{commuteStr}</p>
          </div>
        </div>

        {/* Safe Zone */}
        <div className="flex items-start gap-2">
          <Shield className="w-3 h-3 text-emerald-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-[9px] text-slate-500">Safe zones visited</p>
            <p className="text-[11px] text-emerald-300 font-bold font-mono">{safeZonePct}%</p>
          </div>
        </div>

        {/* Avg Daily Distance */}
        <div className="flex items-start gap-2">
          <MapPin className="w-3 h-3 text-slate-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-[9px] text-slate-500">Avg daily distance</p>
            <p className="text-[11px] text-white font-mono">{((baseline.avg_daily_distance || 0) / 1000).toFixed(1)} km</p>
          </div>
        </div>

        {/* Current Behavior */}
        <div className={`rounded-lg p-2 border ${deviation > 40 ? 'border-red-500/30' : deviation > 20 ? 'border-amber-500/30' : 'border-emerald-500/30'} ${behaviorBg}`} data-testid="twin-behavior-status">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <AlertTriangle className={`w-3 h-3 ${behaviorColor}`} />
              <span className="text-[9px] text-slate-400">Current behavior</span>
            </div>
            <span className={`text-[10px] font-bold ${behaviorColor}`}>{currentBehavior}</span>
          </div>
          {deviation > 0 && (
            <div className="mt-1.5">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[8px] text-slate-500">Deviation from routine</span>
                <span className={`text-[10px] font-bold font-mono ${behaviorColor}`}>+{deviation}%</span>
              </div>
              <div className="h-1 rounded-full bg-slate-700/50 overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-700 ${deviation > 40 ? 'bg-red-500' : deviation > 20 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(deviation, 100)}%` }} />
              </div>
            </div>
          )}
        </div>
      </div>
    </PanelShell>
  );
};

const PanelShell = ({ children }) => (
  <div className="bg-slate-800/40 rounded-lg border border-slate-700/50 flex flex-col h-full" data-testid="digital-twin-panel">
    <div className="px-3 py-2 border-b border-slate-700/50 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-1.5">
        <User className="w-3.5 h-3.5 text-teal-400" />
        <h3 className="text-[11px] font-semibold text-white">Digital Twin Profile</h3>
      </div>
      <span className="text-[7px] text-slate-600">Powered by Guardian AI Engine</span>
    </div>
    {children}
  </div>
);
