import React, { useEffect, useState, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, Circle } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../../api';
import { X, Shield, TrendingUp, Activity, Radio, Eye, MapPin, Crosshair, AlertTriangle } from 'lucide-react';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const sosIcon = new L.DivIcon({ className: '', html: `<div style="width:24px;height:24px;border-radius:50%;background:#ef4444;border:3px solid #fff;box-shadow:0 0 12px #ef4444;animation:pulse 1.5s infinite"></div>`, iconSize: [24, 24], iconAnchor: [12, 12] });
const journeyIcon = new L.DivIcon({ className: '', html: `<div style="width:16px;height:16px;border-radius:50%;background:#3b82f6;border:2px solid #93c5fd;box-shadow:0 0 8px #3b82f6"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] });
const newCriticalIcon = new L.DivIcon({ className: '', html: `<div style="width:28px;height:28px;border-radius:50%;background:#ef4444;border:3px solid #fca5a5;box-shadow:0 0 24px #ef4444,0 0 48px rgba(239,68,68,0.4);animation:newIncidentPulse 1.5s infinite"></div>`, iconSize: [28, 28], iconAnchor: [14, 14] });

const RISK_COLORS = {
  SAFE: { fill: '#22c55e', stroke: '#16a34a' },
  LOW: { fill: '#84cc16', stroke: '#65a30d' },
  MODERATE: { fill: '#f59e0b', stroke: '#d97706' },
  HIGH: { fill: '#ef4444', stroke: '#dc2626' },
  CRITICAL: { fill: '#dc2626', stroke: '#b91c1c' },
};

const SIGNAL_ICONS = {
  forecast: TrendingUp, hotspot: Radio, trend: TrendingUp,
  activity: Activity, patrol: Crosshair, environment: Eye,
  session_density: MapPin, mobility_anomaly: AlertTriangle,
};

if (typeof document !== 'undefined' && !document.getElementById('cc-map-styles')) {
  const s = document.createElement('style');
  s.id = 'cc-map-styles';
  s.textContent = `
    @keyframes newIncidentPulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.6);opacity:.7}}
    @keyframes heatPulse{0%,100%{opacity:.18}50%{opacity:.35}}
    .heat-zone-critical{animation:heatPulse 2.5s ease-in-out infinite}
    .heat-zone-high{animation:heatPulse 3.5s ease-in-out infinite}
    .heat-zone-selected{stroke-dasharray:6 4!important;stroke-width:2px!important;stroke-opacity:1!important}
  `;
  document.head.appendChild(s);
}

const FitBounds = ({ markers }) => {
  const map = useMap();
  useEffect(() => {
    if (markers.length > 0) {
      map.fitBounds(L.latLngBounds(markers.map(m => [m.lat, m.lng])), { padding: [40, 40], maxZoom: 13 });
    }
  }, [markers, map]);
  return null;
};

const MapFlyTo = ({ target }) => {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo([target.lat, target.lng], 15, { duration: 1.2 });
  }, [target, map]);
  return null;
};

/* Signal bar component */
const SignalBar = ({ signal }) => {
  const Icon = SIGNAL_ICONS[signal.key] || Activity;
  const pct = Math.min(100, (signal.score / 10) * 100);
  const color = signal.score >= 7 ? '#ef4444' : signal.score >= 4 ? '#f59e0b' : '#22c55e';
  return (
    <div className="flex items-center gap-2.5 py-1.5">
      <Icon className="w-3.5 h-3.5 text-slate-500 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-0.5">
          <span className="text-[10px] text-slate-300 truncate">{signal.name}</span>
          <span className="text-[10px] font-mono" style={{ color }}>{signal.score.toFixed(1)}</span>
        </div>
        <div className="h-1 bg-slate-700/50 rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
        </div>
        {signal.category && <span className="text-[8px] text-slate-600">{signal.category}</span>}
        {signal.status && <span className="text-[8px] text-slate-600">{signal.status}</span>}
      </div>
      <span className="text-[9px] text-slate-600 w-8 text-right">{(signal.weight * 100).toFixed(0)}%</span>
    </div>
  );
};

/* Zone Intelligence Panel */
const ZoneIntelPanel = ({ data, onClose }) => {
  if (!data) return null;
  const rc = RISK_COLORS[data.risk_level?.toUpperCase()] || RISK_COLORS.MODERATE;
  const topSignal = data.signals?.reduce((a, b) => a.weighted > b.weighted ? a : b, { weighted: 0 });
  const recommendation = data.risk_level === 'critical' ? 'Immediate patrol deployment recommended' :
    data.risk_level === 'high' ? 'Increase caregiver presence in this zone' :
    data.risk_level === 'moderate' ? 'Monitor zone — elevated activity detected' : 'Zone within normal parameters';

  return (
    <div className="absolute top-0 right-0 bottom-0 w-[320px] z-[1001] bg-slate-900/95 backdrop-blur-md border-l border-slate-700/50 flex flex-col overflow-hidden" data-testid="zone-intel-panel">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: `${rc.fill}20`, border: `1px solid ${rc.fill}40` }}>
            <Shield className="w-4 h-4" style={{ color: rc.fill }} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Zone Intelligence</h3>
            <p className="text-[9px] text-slate-500">{data.grid_id}</p>
          </div>
        </div>
        <button onClick={onClose} className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700/50 flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-colors" data-testid="zone-intel-close">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Risk Score */}
      <div className="px-4 py-3 border-b border-slate-700/30">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-slate-500 uppercase">Composite Risk</span>
          <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: `${rc.fill}20`, color: rc.fill }}>
            {data.risk_level?.toUpperCase()}
          </span>
        </div>
        <div className="flex items-end gap-2">
          <span className="text-3xl font-bold font-mono" style={{ color: rc.fill }}>{data.composite_score?.toFixed(1)}</span>
          <span className="text-[10px] text-slate-500 mb-1">/10</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full mt-2 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, (data.composite_score / 10) * 100)}%`, background: `linear-gradient(90deg, ${rc.stroke}, ${rc.fill})` }} />
        </div>
      </div>

      {/* Location */}
      <div className="px-4 py-2 border-b border-slate-700/30 flex items-center gap-2">
        <MapPin className="w-3 h-3 text-slate-500" />
        <span className="text-[10px] text-slate-400">{data.lat?.toFixed(4)}, {data.lng?.toFixed(4)}</span>
      </div>

      {/* Signals */}
      <div className="flex-1 overflow-y-auto px-4 py-2">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-slate-500 uppercase font-medium">AI Signal Breakdown</span>
          <span className="text-[9px] text-slate-600">score / weight</span>
        </div>
        {(data.signals || []).map((sig, i) => <SignalBar key={i} signal={sig} />)}
        {topSignal?.name && (
          <div className="mt-2 px-2.5 py-1.5 rounded bg-slate-800/50 border border-slate-700/40">
            <span className="text-[9px] text-slate-500">Dominant Signal</span>
            <p className="text-[10px] text-white font-medium">{topSignal.name} ({topSignal.weighted?.toFixed(2)} weighted)</p>
          </div>
        )}
      </div>

      {/* Recommendation */}
      <div className="px-4 py-3 border-t border-slate-700/50 shrink-0">
        <span className="text-[9px] text-slate-500 uppercase">Recommended Action</span>
        <p className="text-xs text-amber-400 mt-1">{recommendation}</p>
      </div>
    </div>
  );
};

/* Heatmap zone with click handler */
const HeatmapZone = ({ zone, selected, onClick }) => {
  const rc = RISK_COLORS[zone.risk_level] || RISK_COLORS.SAFE;
  if (zone.risk_level === 'SAFE') return null;

  const radius = zone.risk_level === 'CRITICAL' ? 350 : zone.risk_level === 'HIGH' ? 280 : zone.risk_level === 'MODERATE' ? 200 : 140;
  const opacity = zone.risk_level === 'CRITICAL' ? 0.3 : zone.risk_level === 'HIGH' ? 0.22 : 0.12;
  const parts = [];
  if (zone.risk_level === 'CRITICAL') parts.push('heat-zone-critical');
  else if (zone.risk_level === 'HIGH') parts.push('heat-zone-high');
  if (selected) parts.push('heat-zone-selected');
  const cssClass = parts.join(' ') || undefined;

  return (
    <>
      <Circle center={[zone.lat, zone.lng]} radius={radius * 1.4}
        pathOptions={{ fillColor: rc.fill, fillOpacity: opacity * 0.4, color: 'transparent', className: cssClass }} />
      <Circle center={[zone.lat, zone.lng]} radius={radius}
        pathOptions={{ fillColor: rc.fill, fillOpacity: selected ? opacity * 1.8 : opacity, color: selected ? '#fff' : rc.stroke, weight: selected ? 2 : 1, opacity: selected ? 0.8 : 0.4, className: cssClass }}
        eventHandlers={{ click: () => onClick(zone) }}
      />
    </>
  );
};

export const LiveSafetyMap = ({ sosEvents = [], journeys = [], heatmapData = [], onSelectIncident, focusTarget, newIncidentIds, showHeatmap, onToggleHeatmap }) => {
  const [selectedZone, setSelectedZone] = useState(null);
  const [zoneDetail, setZoneDetail] = useState(null);
  const [loadingZone, setLoadingZone] = useState(false);

  const handleZoneClick = useCallback(async (zone) => {
    setSelectedZone(zone.grid_id);
    setLoadingZone(true);
    try {
      const res = await api.get(`/operator/city-heatmap/cell/${zone.grid_id}`);
      setZoneDetail(res.data);
    } catch {
      setZoneDetail({ grid_id: zone.grid_id, lat: zone.lat, lng: zone.lng, composite_score: zone.risk_score || 0, risk_level: zone.risk_level?.toLowerCase(), signals: [] });
    }
    setLoadingZone(false);
  }, []);

  const closePanel = () => { setSelectedZone(null); setZoneDetail(null); };

  const allMarkers = [
    ...sosEvents.map(s => ({ lat: s.lat || 19.076, lng: s.lng || 72.877 })),
    ...journeys.map(j => ({ lat: j.location?.lat || 19.076, lng: j.location?.lng || 72.877 })),
    ...heatmapData.filter(h => h.risk_level !== 'SAFE').slice(0, 5).map(h => ({ lat: h.lat, lng: h.lng })),
  ];
  const center = allMarkers.length > 0 ? [allMarkers[0].lat, allMarkers[0].lng] : [19.076, 72.877];
  const heatStats = {
    critical: heatmapData.filter(z => z.risk_level === 'CRITICAL').length,
    high: heatmapData.filter(z => z.risk_level === 'HIGH').length,
    moderate: heatmapData.filter(z => z.risk_level === 'MODERATE').length,
    total: heatmapData.length,
  };

  return (
    <div className="h-full w-full rounded-lg overflow-hidden border border-slate-700/50 relative" data-testid="cc-live-map">
      <MapContainer center={center} zoom={12} className="h-full w-full" style={{ background: '#0f172a' }} zoomControl={false} attributionControl={false}>
        <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution='Nagarik' />
        {allMarkers.length > 0 && <FitBounds markers={allMarkers} />}
        <MapFlyTo target={focusTarget} />

        {heatmapData.filter(z => z.risk_level !== 'SAFE').map((zone, i) => (
          <HeatmapZone key={`heat-${i}`} zone={zone} selected={selectedZone === zone.grid_id} onClick={handleZoneClick} />
        ))}

        {sosEvents.map((sos, i) => (
          <Marker key={`sos-${i}`} position={[sos.lat || 19.076, sos.lng || 72.877]}
            icon={newIncidentIds?.has(sos.id) ? newCriticalIcon : sosIcon}
            eventHandlers={{ click: () => onSelectIncident?.(sos) }}>
            <Popup><div className="text-xs"><p className="font-bold text-red-600">SOS Alert</p><p>{sos.senior_name || sos.user_id || 'Unknown'}</p></div></Popup>
          </Marker>
        ))}

        {journeys.map((j, i) => (
          <Marker key={`journey-${i}`} position={[j.location?.lat || 19.076, j.location?.lng || 72.877]} icon={journeyIcon}>
            <Popup><div className="text-xs"><p className="font-bold text-blue-600">Guardian Journey</p><p>Risk: {j.risk_level || 'SAFE'}</p></div></Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Controls overlay */}
      <div className="absolute top-3 right-3 z-[1000] flex flex-col gap-2" data-testid="heatmap-controls" style={{ right: zoneDetail ? '332px' : '12px', transition: 'right 0.3s ease' }}>
        <button onClick={onToggleHeatmap}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-medium border backdrop-blur-md transition-all ${showHeatmap ? 'bg-red-500/20 border-red-500/40 text-red-300 hover:bg-red-500/30' : 'bg-slate-800/60 border-slate-700/50 text-slate-400 hover:bg-slate-700/60'}`}
          data-testid="heatmap-toggle">
          {showHeatmap ? 'RISK HEATMAP ON' : 'RISK HEATMAP OFF'}
        </button>
        {showHeatmap && heatStats.total > 0 && (
          <div className="bg-slate-900/80 backdrop-blur-md border border-slate-700/50 rounded-lg p-2.5 space-y-1" data-testid="heatmap-legend">
            <p className="text-[9px] text-slate-500 uppercase font-medium mb-1.5">Risk Zones</p>
            {heatStats.critical > 0 && <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-600 heat-zone-critical" /><span className="text-[10px] text-red-400">{heatStats.critical} Critical</span></div>}
            {heatStats.high > 0 && <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500 heat-zone-high" /><span className="text-[10px] text-orange-400">{heatStats.high} High Risk</span></div>}
            {heatStats.moderate > 0 && <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-amber-500" /><span className="text-[10px] text-amber-400">{heatStats.moderate} Moderate</span></div>}
            <p className="text-[9px] text-slate-600 pt-0.5">{heatStats.total} zones analyzed</p>
          </div>
        )}
      </div>

      {/* Loading indicator */}
      {loadingZone && (
        <div className="absolute top-1/2 right-[160px] z-[1001] -translate-y-1/2">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Zone Intelligence Panel */}
      <ZoneIntelPanel data={zoneDetail} onClose={closePanel} />
    </div>
  );
};
