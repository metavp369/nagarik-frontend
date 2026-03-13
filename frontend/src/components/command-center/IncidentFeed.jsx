import React from 'react';
import { Radio, AlertTriangle, MapPin, Clock, ChevronRight } from 'lucide-react';

const SEVERITY_STYLES = {
  critical: { bg: 'bg-red-500/10', border: 'border-red-500/30', dot: 'bg-red-500', text: 'text-red-400' },
  high: { bg: 'bg-orange-500/10', border: 'border-orange-500/30', dot: 'bg-orange-500', text: 'text-orange-400' },
  medium: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', dot: 'bg-amber-500', text: 'text-amber-400' },
  low: { bg: 'bg-slate-500/10', border: 'border-slate-500/30', dot: 'bg-slate-400', text: 'text-slate-400' },
};

const TYPE_ICONS = {
  sos: Radio,
  fall: AlertTriangle,
  geofence: MapPin,
  default: AlertTriangle,
};

const IncidentItem = ({ incident, onSelect }) => {
  const s = SEVERITY_STYLES[incident.severity] || SEVERITY_STYLES.low;
  const Icon = TYPE_ICONS[incident.incident_type] || TYPE_ICONS.default;
  const time = incident.created_at ? new Date(incident.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  return (
    <button
      onClick={() => onSelect?.(incident)}
      className={`w-full text-left p-3 rounded-lg border ${s.bg} ${s.border} hover:brightness-125 transition-all group`}
      data-testid="cc-incident-item"
    >
      <div className="flex items-start gap-2.5">
        <div className={`w-7 h-7 rounded-md ${s.bg} flex items-center justify-center shrink-0 mt-0.5`}>
          <Icon className={`w-3.5 h-3.5 ${s.text}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className={`text-xs font-semibold uppercase tracking-wider ${s.text}`}>
              {incident.incident_type?.replace('_', ' ') || 'Alert'}
            </span>
            <span className="text-[10px] text-slate-500 flex items-center gap-1"><Clock className="w-2.5 h-2.5" />{time}</span>
          </div>
          <p className="text-sm text-slate-300 truncate mt-0.5">{incident.senior_name || incident.device_identifier || 'Unknown'}</p>
          <div className="flex items-center justify-between mt-1">
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${s.bg} ${s.text} border ${s.border}`}>{incident.severity}</span>
            <ChevronRight className="w-3 h-3 text-slate-600 group-hover:text-slate-400 transition-colors" />
          </div>
        </div>
      </div>
    </button>
  );
};

export const IncidentFeed = ({ incidents = [], sseEvents = [], onSelectIncident }) => {
  // Merge real-time SSE events with DB incidents
  const allEvents = [
    ...sseEvents.map(e => ({
      id: e.sos_id || e.id || `sse-${Date.now()}`,
      incident_type: e.type || 'sos',
      severity: 'critical',
      senior_name: e.user_name || e.user_id,
      created_at: e.timestamp || new Date().toISOString(),
      status: 'active',
      ...e,
    })),
    ...incidents,
  ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 30);

  return (
    <div className="h-full bg-slate-800/40 rounded-lg border border-slate-700/50 flex flex-col" data-testid="cc-incident-feed">
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-red-400" />
          <h3 className="text-sm font-semibold text-white">Incident Feed</h3>
        </div>
        <span className="text-[10px] bg-slate-700/50 text-slate-400 px-2 py-0.5 rounded-full">{allEvents.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin scrollbar-thumb-slate-700">
        {allEvents.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-slate-500">No active incidents</p>
            <p className="text-[10px] text-slate-600 mt-1">System monitoring active</p>
          </div>
        ) : (
          allEvents.map((inc, i) => (
            <IncidentItem key={inc.id || i} incident={inc} onSelect={onSelectIncident} />
          ))
        )}
      </div>
    </div>
  );
};
