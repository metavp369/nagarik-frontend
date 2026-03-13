import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, CheckCircle, AlertTriangle, Clock, ChevronDown, ChevronUp } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const MODULE_UPTIMES = {
  'AI Safety Brain': 99.97,
  'Command Center': 99.94,
  'Guardian Network': 99.91,
  'Notification System': 99.96,
  'Location Intelligence': 99.93,
  'Incident Replay Engine': 99.92,
  'Risk Prediction Engine': 99.95,
  'Telemetry Pipeline': 99.98,
};

// Generate 90-day uptime history (simulated)
function generate90DayHistory() {
  const days = [];
  const now = new Date();
  for (let i = 89; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    // Simulate: ~97% green, ~2% yellow, ~1% red
    const rand = Math.random();
    let status = 'operational';
    if (rand > 0.98) status = 'incident';
    else if (rand > 0.96) status = 'degraded';
    days.push({ date: d, status });
  }
  return days;
}

const PAST_INCIDENTS = [
  { date: 'Mar 8, 2026', title: 'Notification delivery delay', duration: '3 min', module: 'Notification System', status: 'resolved', description: 'Brief delay in push notification delivery due to FCM queue backlog. Resolved automatically.' },
  { date: 'Mar 3, 2026', title: 'Telemetry ingestion slowdown', duration: '7 min', module: 'Telemetry Pipeline', status: 'resolved', description: 'Elevated latency in telemetry signal processing. Auto-scaled processing nodes resolved the issue.' },
  { date: 'Feb 25, 2026', title: 'Scheduled maintenance', duration: '12 min', module: 'Risk Prediction Engine', status: 'maintenance', description: 'Planned model update and retraining cycle. No safety coverage impact during maintenance window.' },
  { date: 'Feb 18, 2026', title: 'Guardian network reconnection', duration: '5 min', module: 'Guardian Network', status: 'resolved', description: 'Temporary WebSocket reconnection cycle following infrastructure update. All guardians reconnected within SLA.' },
];

const STATUS_COLORS = {
  operational: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400', label: 'Operational' },
  degraded: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', dot: 'bg-amber-400', label: 'Degraded' },
  incident: { bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-400', dot: 'bg-red-400', label: 'Incident' },
  maintenance: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-400', dot: 'bg-blue-400', label: 'Maintenance' },
};

const DAY_COLORS = {
  operational: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  incident: 'bg-red-500',
};

export default function SystemStatusPage() {
  const navigate = useNavigate();
  const [systems, setSystems] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [expandedModule, setExpandedModule] = useState(null);
  const [uptimeHistories] = useState(() => {
    const h = {};
    Object.keys(MODULE_UPTIMES).forEach(m => { h[m] = generate90DayHistory(); });
    return h;
  });

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API}/api/status/platform`);
        const data = await res.json();
        setSystems(data.systems || []);
        setLastUpdated(new Date());
      } catch (e) {
        console.error('Status fetch error:', e);
      }
    };
    fetchStatus();
    const iv = setInterval(fetchStatus, 30000);
    return () => clearInterval(iv);
  }, []);

  const allOperational = systems.length > 0 && systems.every(s => s.status === 'operational');

  if (systems.length === 0) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] text-slate-200 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-10 h-10 text-teal-400 mx-auto mb-3 animate-pulse" />
          <p className="text-sm text-slate-400">Loading system status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-slate-200">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0a0e1a]/80 backdrop-blur-xl border-b border-slate-800/40">
        <div className="max-w-3xl mx-auto px-6 h-14 flex items-center justify-between">
          <button onClick={() => navigate('/')} className="flex items-center gap-2" data-testid="status-page-logo">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center">
              <Shield className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-bold tracking-tight">Nagarik</span>
            <span className="text-xs text-slate-500 ml-1">System Status</span>
          </button>
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/telemetry')} className="text-xs text-slate-500 hover:text-white transition-colors">Telemetry</button>
            <button onClick={() => navigate('/safety-dashboard')} className="text-xs text-slate-500 hover:text-white transition-colors">Dashboard</button>
          </div>
        </div>
      </nav>

      <div className="pt-24 pb-16 px-6 max-w-3xl mx-auto">
        {/* ── 1. Overall Status Banner ── */}
        <div className={`rounded-2xl p-6 mb-8 border ${allOperational ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-amber-500/5 border-amber-500/20'}`} data-testid="status-banner">
          <div className="flex items-center gap-3">
            {allOperational ? (
              <CheckCircle className="w-7 h-7 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-7 h-7 text-amber-400" />
            )}
            <div>
              <h1 className="text-xl font-bold text-white">
                {allOperational ? 'All Systems Operational' : 'Some Systems Degraded'}
              </h1>
              {lastUpdated && (
                <p className="text-xs text-slate-500 mt-0.5">
                  Last checked: {lastUpdated.toLocaleTimeString()} &middot; Auto-refreshes every 30s
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ── 2. Platform Modules ── */}
        <div className="mb-10" data-testid="status-modules">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Platform Modules</h2>
          <div className="space-y-2">
            {systems.map((sys, i) => {
              const st = STATUS_COLORS[sys.status] || STATUS_COLORS.operational;
              const uptime = MODULE_UPTIMES[sys.name] || sys.uptime || 99.9;
              const isExpanded = expandedModule === i;
              const history = uptimeHistories[sys.name] || [];
              const lastIncident = PAST_INCIDENTS.find(inc => inc.module === sys.name);

              return (
                <div key={i} className="rounded-xl border border-slate-800/40 bg-white/[0.01] overflow-hidden">
                  <button
                    onClick={() => setExpandedModule(isExpanded ? null : i)}
                    className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/[0.01] transition-colors"
                    data-testid={`module-${i}`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`w-2.5 h-2.5 rounded-full ${st.dot}`} />
                      <span className="text-sm font-semibold text-white">{sys.name}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`text-xs font-medium ${st.text}`}>{st.label}</span>
                      <span className="text-xs text-slate-500 font-mono">{uptime}%</span>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-600" /> : <ChevronDown className="w-4 h-4 text-slate-600" />}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="px-5 pb-4 border-t border-slate-800/20 pt-3">
                      {/* 90-day uptime bars */}
                      <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-2">90-Day Uptime</p>
                      <div className="flex gap-[2px] mb-3" data-testid={`uptime-chart-${i}`}>
                        {history.map((day, j) => (
                          <div
                            key={j}
                            className={`flex-1 h-6 rounded-[1px] ${DAY_COLORS[day.status]} opacity-80 hover:opacity-100 transition-opacity`}
                            title={`${day.date.toLocaleDateString()} — ${day.status}`}
                          />
                        ))}
                      </div>
                      <div className="flex items-center justify-between text-[9px] text-slate-600 mb-3">
                        <span>90 days ago</span>
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-500" /> Operational</span>
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-amber-500" /> Degraded</span>
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-500" /> Incident</span>
                        </div>
                        <span>Today</span>
                      </div>
                      {/* Last incident */}
                      {lastIncident ? (
                        <div className="rounded-lg bg-white/[0.02] border border-slate-800/30 p-3">
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-[10px] font-semibold text-white">{lastIncident.title}</p>
                            <span className="text-[9px] text-slate-500">{lastIncident.date}</span>
                          </div>
                          <p className="text-[10px] text-slate-400 leading-relaxed">{lastIncident.description}</p>
                          <p className="text-[9px] text-slate-600 mt-1">Duration: {lastIncident.duration}</p>
                        </div>
                      ) : (
                        <p className="text-[10px] text-slate-600">No recent incidents for this module.</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── 3. Overall 90-Day Uptime ── */}
        <div className="mb-10" data-testid="status-overall-uptime">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Overall Platform Uptime</h2>
          <div className="rounded-xl border border-slate-800/40 bg-white/[0.01] p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-2xl font-bold text-white">99.95%</span>
              <span className="text-xs text-slate-500">Last 90 days</span>
            </div>
            <div className="flex gap-[2px]" data-testid="overall-uptime-chart">
              {(uptimeHistories['AI Safety Brain'] || []).map((day, j) => (
                <div
                  key={j}
                  className={`flex-1 h-8 rounded-[1px] ${DAY_COLORS[day.status]} opacity-70 hover:opacity-100 transition-opacity`}
                  title={`${day.date.toLocaleDateString()} — ${day.status}`}
                />
              ))}
            </div>
            <div className="flex items-center justify-between text-[9px] text-slate-600 mt-2">
              <span>90 days ago</span>
              <span>Today</span>
            </div>
          </div>
        </div>

        {/* ── 4. Recent Incidents ── */}
        <div className="mb-10" data-testid="status-incidents-log">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Recent Incidents</h2>
          <div className="space-y-3">
            {PAST_INCIDENTS.map((inc, i) => {
              const st = STATUS_COLORS[inc.status] || STATUS_COLORS.operational;
              return (
                <div key={i} className="rounded-xl border border-slate-800/40 bg-white/[0.01] p-4" data-testid={`past-incident-${i}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${st.dot}`} />
                      <span className="text-sm font-semibold text-white">{inc.title}</span>
                    </div>
                    <span className="text-[10px] text-slate-500">{inc.date}</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed mb-2">{inc.description}</p>
                  <div className="flex items-center gap-4 text-[10px] text-slate-600">
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {inc.duration}</span>
                    <span>{inc.module}</span>
                    <span className={`font-semibold uppercase ${st.text}`}>{st.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <footer className="border-t border-slate-800/40 pt-6" data-testid="status-page-footer">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-4">
              <button onClick={() => navigate('/')} className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors">Home</button>
              <button onClick={() => navigate('/telemetry')} className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors">Telemetry</button>
              <button onClick={() => navigate('/safety-dashboard')} className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors">Dashboard</button>
              <a href="mailto:support@Nagarik.app" className="text-[10px] text-slate-600 hover:text-teal-400 transition-colors">support@Nagarik.app</a>
            </div>
            <p className="text-[9px] text-slate-700">&copy; 2026 Nagarik Technologies &middot; System Status</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
