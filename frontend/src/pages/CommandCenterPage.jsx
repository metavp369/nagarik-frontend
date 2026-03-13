import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api, { createEventSource } from '../api';
import { CommandCenterHeader } from '../components/command-center/CommandCenterHeader';
import { LiveSafetyMap } from '../components/command-center/LiveSafetyMap';
import { IncidentFeed } from '../components/command-center/IncidentFeed';
import { CityRiskRadar } from '../components/command-center/CityRiskRadar';
import { PredictiveAlertBar } from '../components/command-center/PredictiveAlertBar';
import { AIReasoningPanel } from '../components/command-center/AIReasoningPanel';
import { DigitalTwinPanel } from '../components/command-center/DigitalTwinPanel';
import { AITimeline } from '../components/command-center/AITimeline';
import { ThreatAssessment } from '../components/command-center/ThreatAssessment';
import { Shield, AlertTriangle, TrendingUp } from 'lucide-react';

const RISK_COLORS = { critical: 'text-red-400', high: 'text-orange-400', moderate: 'text-amber-400', low: 'text-emerald-400' };

/* AI Risk Intelligence — with click-to-select */
const AIRiskIntelligence = ({ highRiskUsers = [], selectedUserId, onSelectUser }) => (
  <div className="bg-slate-800/40 rounded-lg border border-slate-700/50 flex flex-col h-full" data-testid="ai-risk-intelligence">
    <div className="px-3 py-2 border-b border-slate-700/50 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-1.5">
        <Shield className="w-3.5 h-3.5 text-purple-400" />
        <h3 className="text-[11px] font-semibold text-white">AI Risk Intelligence</h3>
      </div>
      <span className="text-[7px] text-slate-600">Powered by Guardian AI Engine</span>
    </div>
    <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
      {highRiskUsers.length === 0 ? (
        <p className="text-[10px] text-slate-500 text-center py-4">No risk assessments yet</p>
      ) : highRiskUsers.map((u, i) => {
        const isSelected = u.user_id === selectedUserId;
        return (
          <div
            key={i}
            className={`p-2 rounded-lg cursor-pointer transition-all ${isSelected ? 'bg-purple-500/15 border border-purple-500/40 ring-1 ring-purple-500/20' : 'bg-slate-700/20 border border-slate-700/40 hover:bg-slate-700/30'}`}
            onClick={() => onSelectUser(u.user_id)}
            data-testid={`high-risk-user-${i}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-slate-300 truncate max-w-[120px]">{u.user_name}</span>
              <div className="flex items-center gap-1.5">
                <span className={`text-sm font-bold font-mono ${RISK_COLORS[u.risk_level] || RISK_COLORS.low}`}>{(u.final_score * 10).toFixed(1)}</span>
                <span className={`text-[8px] uppercase font-medium ${RISK_COLORS[u.risk_level] || RISK_COLORS.low}`}>{u.risk_level}</span>
              </div>
            </div>
            {u.top_factors?.slice(0, 2).map((f, j) => (
              <div key={j} className="flex items-start gap-1 mt-0.5">
                <AlertTriangle className={`w-2.5 h-2.5 mt-0.5 shrink-0 ${RISK_COLORS[u.risk_level] || 'text-slate-500'}`} />
                <span className="text-[9px] text-slate-400 truncate">{f.description}</span>
              </div>
            ))}
            <div className="mt-1 flex items-center gap-1">
              <TrendingUp className="w-2.5 h-2.5 text-amber-500" />
              <span className="text-[9px] text-amber-400 truncate">{u.action_detail || u.recommended_action}</span>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

export default function CommandCenterPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [metrics, setMetrics] = useState(null);
  const [commandData, setCommandData] = useState(null);
  const [journeys, setJourneys] = useState([]);
  const [queueHealth, setQueueHealth] = useState({});
  const [sseEvents, setSseEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [heatmapData, setHeatmapData] = useState([]);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [highRiskUsers, setHighRiskUsers] = useState([]);

  // Selected user state (drives AI Reasoning, Digital Twin, Timeline)
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [userRiskData, setUserRiskData] = useState(null);
  const [userBaseline, setUserBaseline] = useState(null);
  const [userPredictions, setUserPredictions] = useState([]);
  const [userRiskHistory, setUserRiskHistory] = useState([]);
  const [userDataLoading, setUserDataLoading] = useState(false);

  // Alert system state
  const [headerFlashing, setHeaderFlashing] = useState(false);
  const [newCriticalCount, setNewCriticalCount] = useState(0);
  const [alertsMuted, setAlertsMuted] = useState(false);
  const [mapFocusTarget, setMapFocusTarget] = useState(null);
  const [newIncidentIds, setNewIncidentIds] = useState(new Set());
  const previousIdsRef = useRef(new Set());
  const alertAudioRef = useRef(null);
  const isFirstLoadRef = useRef(true);

  // Demo mode state
  const [demoMode, setDemoMode] = useState(false);
  const [demoStatus, setDemoStatus] = useState(null);
  const demoPollingRef = useRef(null);

  const isAuthorized = user?.role === 'admin' || user?.role === 'operator' ||
    user?.roles?.includes('admin') || user?.roles?.includes('operator');

  // Init audio + notification permission
  useEffect(() => {
    alertAudioRef.current = new Audio('/sounds/alert.wav');
    alertAudioRef.current.volume = 0.8;
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const triggerAlert = useCallback((newCriticals) => {
    if (!alertsMuted && alertAudioRef.current) {
      alertAudioRef.current.currentTime = 0;
      alertAudioRef.current.play().catch(() => {});
    }
    setHeaderFlashing(true);
    setTimeout(() => setHeaderFlashing(false), 3500);
    setNewCriticalCount(newCriticals.length);
    const ids = new Set(newCriticals.map(i => i.id));
    setNewIncidentIds(ids);
    if (newCriticals[0]) {
      const loc = { lat: 19.076 + (Math.random() - 0.5) * 0.04, lng: 72.877 + (Math.random() - 0.5) * 0.04 };
      setMapFocusTarget(loc);
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('COMMAND CENTER — CRITICAL INCIDENT', {
          body: `${newCriticals[0].senior_name || newCriticals[0].user_id || 'Unknown'} — ${newCriticals[0].incident_type || 'Critical'}`,
          icon: '/favicon.ico',
          tag: `cc-${newCriticals[0].id}`,
          requireInteraction: true,
        });
      }
    }
    setTimeout(() => { setNewCriticalCount(0); setNewIncidentIds(new Set()); }, 10000);
  }, [alertsMuted]);

  // Fetch all data in parallel
  const fetchData = useCallback(async () => {
    try {
      const requests = [
        api.get('/admin/monitoring/metrics').catch(() => null),
        api.get('/operator/command-center').catch(() => null),
        api.get('/night-guardian/sessions').catch(() => null),
        api.get('/admin/monitoring/queue-health').catch(() => null),
        api.get('/operator/city-heatmap/live').catch(() => null),
        api.get('/guardian-ai/insights/high-risk?limit=6').catch(() => null),
      ];
      const [metricsRes, cmdRes, journeyRes, queueRes, heatmapRes, hrRes] = await Promise.all(requests);

      if (metricsRes?.data) setMetrics(metricsRes.data);
      if (cmdRes?.data) {
        const incoming = cmdRes.data.active_incidents || [];
        const prevIds = previousIdsRef.current;
        if (!isFirstLoadRef.current && prevIds.size > 0) {
          const newCriticals = incoming.filter(
            i => (i.severity === 'critical' || i.incident_type === 'sos') && !prevIds.has(i.id)
          );
          if (newCriticals.length > 0) triggerAlert(newCriticals);
        }
        isFirstLoadRef.current = false;
        previousIdsRef.current = new Set(incoming.map(i => i.id));
        setCommandData(cmdRes.data);
      }
      if (journeyRes?.data?.sessions) setJourneys(journeyRes.data.sessions);
      if (queueRes?.data) setQueueHealth(queueRes.data);
      if (heatmapRes?.data?.cells) {
        setHeatmapData(heatmapRes.data.cells.map(c => ({
          lat: c.lat, lng: c.lng,
          risk_score: c.composite_score,
          risk_level: c.risk_level?.toUpperCase(),
          grid_id: c.grid_id,
          hotspot: c.hotspot,
          activity: c.activity,
        })));
      }
      if (hrRes?.data?.high_risk_users) {
        setHighRiskUsers(hrRes.data.high_risk_users);
        // Auto-select first user if none selected
        if (!selectedUserId && hrRes.data.high_risk_users.length > 0) {
          setSelectedUserId(hrRes.data.high_risk_users[0].user_id);
        }
      }
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!isAuthorized) { navigate('/family'); return; }
    fetchData();
  }, [isAuthorized, navigate, fetchData]);

  // Auto-refresh every 10s
  useEffect(() => {
    const iv = setInterval(fetchData, 10000);
    return () => clearInterval(iv);
  }, [fetchData]);

  // Demo mode toggle handler
  const toggleDemo = useCallback(async () => {
    try {
      if (demoMode) {
        await api.post('/demo/stop');
        setDemoMode(false);
        setDemoStatus(null);
        clearInterval(demoPollingRef.current);
      } else {
        const res = await api.post('/demo/start');
        if (res.data?.status === 'started' || res.data?.status === 'already_running') {
          setDemoMode(true);
          // Poll demo status every 2s during demo
          demoPollingRef.current = setInterval(async () => {
            try {
              const s = await api.get('/demo/status');
              setDemoStatus(s.data);
              if (!s.data?.running) {
                setDemoMode(false);
                clearInterval(demoPollingRef.current);
                fetchData(); // Refresh command center data
              }
            } catch {}
          }, 2000);
        }
      }
    } catch (err) {
      console.warn('Demo toggle error:', err.message);
    }
  }, [demoMode, fetchData]);

  // Cleanup demo polling on unmount
  useEffect(() => {
    return () => clearInterval(demoPollingRef.current);
  }, []);

  // Fetch user-specific data when selected user changes
  useEffect(() => {
    if (!selectedUserId) {
      setUserRiskData(null);
      setUserBaseline(null);
      setUserPredictions([]);
      setUserRiskHistory([]);
      return;
    }
    setUserDataLoading(true);
    Promise.all([
      api.get(`/guardian-ai/${selectedUserId}/risk-score`).catch(() => null),
      api.get(`/guardian-ai/${selectedUserId}/baseline`).catch(() => null),
      api.get(`/guardian-ai/${selectedUserId}/predictions`).catch(() => null),
      api.get(`/guardian-ai/${selectedUserId}/risk-history?limit=15`).catch(() => null),
    ]).then(([riskRes, baseRes, predRes, histRes]) => {
      setUserRiskData(riskRes?.data || null);
      setUserBaseline(baseRes?.data || null);
      setUserPredictions(predRes?.data?.predictions || []);
      setUserRiskHistory(histRes?.data?.events || []);
    }).finally(() => setUserDataLoading(false));
  }, [selectedUserId]);

  // SSE real-time events
  useEffect(() => {
    if (!isAuthorized) return;
    const sse = createEventSource(
      (eventType, data) => {
        if (['sos_triggered', 'safety_risk_alert', 'fake_call_incoming', 'incident_created'].includes(eventType)) {
          const event = { ...data, type: eventType, timestamp: new Date().toISOString() };
          setSseEvents(prev => [event, ...prev].slice(0, 50));
          if (['sos_triggered', 'incident_created'].includes(eventType)) {
            triggerAlert([event]);
          }
        }
      },
      (err) => console.warn('Command Center SSE error:', err),
      () => {},
    );
    return () => sse?.close();
  }, [isAuthorized]);

  if (!isAuthorized) return null;

  const incidents = commandData?.active_incidents || [];

  // Build map data
  const sosMapEvents = incidents
    .filter(i => i.severity === 'critical' || i.incident_type === 'sos')
    .map(i => ({ ...i, lat: 19.076 + (Math.random() - 0.5) * 0.05, lng: 72.877 + (Math.random() - 0.5) * 0.05 }));

  const journeyMapData = journeys.map(j => ({
    ...j,
    location: j.location || { lat: 19.076 + (Math.random() - 0.5) * 0.08, lng: 72.877 + (Math.random() - 0.5) * 0.08 },
  }));

  if (loading) {
    return (
      <div className="h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-400">Loading Command Center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-slate-900 text-white grid grid-rows-[68px_1fr_280px] overflow-hidden" data-testid="command-center-page">
      {/* Row 1: Header */}
      <CommandCenterHeader
        metrics={metrics}
        incidents={incidents}
        guardianSessions={metrics?.guardian_sessions?.active || journeys.length}
        flashing={headerFlashing}
        newCriticalCount={newCriticalCount}
        alertsMuted={alertsMuted}
        onToggleMute={() => setAlertsMuted(m => !m)}
        demoMode={demoMode}
        onToggleDemo={toggleDemo}
      />

      {/* Demo Mode Status Bar */}
      {demoMode && demoStatus && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-6 py-1.5 flex items-center gap-4" data-testid="demo-status-bar">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Demo Mode Active</span>
          </div>
          <span className="text-[10px] text-amber-300">
            {demoStatus.scenario_user && `Simulating: ${demoStatus.scenario_user}`}
          </span>
          <div className="flex-1" />
          <span className="text-[10px] text-amber-400 font-mono">
            Step {demoStatus.current_step}/{demoStatus.total_steps} · {demoStatus.elapsed_seconds}s
          </span>
          {/* Progress bar */}
          <div className="w-32 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-400 rounded-full transition-all duration-500"
              style={{ width: `${(demoStatus.current_step / demoStatus.total_steps) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Row 2: Map + Right sidebar */}
      <div className="grid grid-cols-[1fr_360px] gap-3 p-3 min-h-0">
        <div className="relative">
          <LiveSafetyMap
            sosEvents={sosMapEvents}
            journeys={journeyMapData}
            heatmapData={showHeatmap ? heatmapData : []}
            focusTarget={mapFocusTarget}
            newIncidentIds={newIncidentIds}
            showHeatmap={showHeatmap}
            onToggleHeatmap={() => setShowHeatmap(h => !h)}
          />
          {/* Map overlays */}
          <CityRiskRadar heatmapData={heatmapData} />
          <PredictiveAlertBar predictions={userPredictions} riskScores={userRiskData} />
          <ThreatAssessment />
        </div>

        {/* Right sidebar: Incident Feed + AI Timeline */}
        <div className="flex flex-col gap-2 min-h-0">
          <div className="flex-1 min-h-0">
            <IncidentFeed
              incidents={incidents}
              sseEvents={sseEvents}
              onSelectIncident={(inc) => console.log('Selected:', inc)}
            />
          </div>
          <div className="h-[220px] shrink-0">
            <AITimeline
              riskHistory={userRiskHistory}
              incidents={incidents}
              loading={userDataLoading}
            />
          </div>
        </div>
      </div>

      {/* Row 3: Intelligence panels */}
      <div className="grid grid-cols-3 gap-3 px-3 pb-3 min-h-0">
        <AIRiskIntelligence
          highRiskUsers={highRiskUsers}
          selectedUserId={selectedUserId}
          onSelectUser={setSelectedUserId}
        />
        <AIReasoningPanel riskData={userRiskData} loading={userDataLoading} />
        <DigitalTwinPanel baseline={userBaseline} riskData={userRiskData} loading={userDataLoading} />
      </div>
    </div>
  );
}
