// Journey Screen — Start Journey, Live Safety, Safe Routes
import { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  TextInput, Alert, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { guardianService, safeRouteService, nightGuardianService } from '@/services/endpoints';
import { useAuthStore } from '@/stores/authStore';
import { colors, spacing, fontSize, radius, shadows, scoreColor } from '@/theme';

type Tab = 'start' | 'active' | 'routes';

export default function JourneyScreen() {
  const { user } = useAuthStore();
  const [tab, setTab] = useState<Tab>('start');
  const [activeSession, setActiveSession] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Start Journey state
  const [destLat, setDestLat] = useState('12.9352');
  const [destLng, setDestLng] = useState('77.6245');

  // Safe Routes state
  const [startLat, setStartLat] = useState('12.9716');
  const [startLng, setStartLng] = useState('77.5946');
  const [endLat, setEndLat] = useState('12.9352');
  const [endLng, setEndLng] = useState('77.6245');
  const [routes, setRoutes] = useState<any>(null);
  const [routeLoading, setRouteLoading] = useState(false);

  useEffect(() => {
    checkActiveSession();
  }, []);

  const checkActiveSession = async () => {
    try {
      const res = await guardianService.listActive();
      const sessions = res.data?.sessions || res.data || [];
      if (sessions.length > 0) {
        setActiveSession(sessions[0]);
        setTab('active');
      }
    } catch {}
  };

  const startJourney = async () => {
    if (!user?.id) return;
    setLoading(true);
    try {
      const res = await guardianService.startSession(user.id);
      setActiveSession(res.data);
      setTab('active');
      Alert.alert('Journey Started', 'Your guardians have been notified. Stay safe!');
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to start journey');
    }
    setLoading(false);
  };

  const stopJourney = async () => {
    if (!activeSession?.session_id) return;
    setLoading(true);
    try {
      await guardianService.stopSession(activeSession.session_id);
      setActiveSession(null);
      setTab('start');
      Alert.alert('Journey Ended', 'You have arrived safely.');
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to stop journey');
    }
    setLoading(false);
  };

  const fetchRoutes = async () => {
    setRouteLoading(true);
    try {
      const res = await safeRouteService.generateRoutes(
        parseFloat(startLat), parseFloat(startLng),
        parseFloat(endLat), parseFloat(endLng),
      );
      setRoutes(res.data);
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to generate routes');
    }
    setRouteLoading(false);
  };

  return (
    <SafeAreaView style={styles.safe} testID="journey-screen">
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <Text style={styles.title}>Journey</Text>

        {/* Tab Switcher */}
        <View style={styles.tabs}>
          {(['start', 'active', 'routes'] as Tab[]).map((t) => (
            <TouchableOpacity
              key={t}
              style={[styles.tab, tab === t && styles.tabActive]}
              onPress={() => setTab(t)}
              testID={`journey-tab-${t}`}
            >
              <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
                {t === 'start' ? 'Start' : t === 'active' ? 'Live Status' : 'Safe Routes'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {tab === 'start' && (
          <View style={styles.section}>
            <View style={styles.card}>
              <Ionicons name="location" size={48} color={colors.primary} style={{ alignSelf: 'center', marginBottom: spacing.lg }} />
              <Text style={styles.cardTitle}>Start a Safety Journey</Text>
              <Text style={styles.cardDesc}>
                Your location will be shared with guardians in real-time.
                They'll receive alerts if anything seems unusual.
              </Text>

              <Text style={styles.inputLabel}>Destination (optional)</Text>
              <View style={styles.coordRow}>
                <View style={styles.coordInput}>
                  <Text style={styles.coordLabel}>Lat</Text>
                  <TextInput style={styles.input} value={destLat} onChangeText={setDestLat}
                    keyboardType="numeric" placeholderTextColor={colors.textMuted} testID="journey-dest-lat" />
                </View>
                <View style={styles.coordInput}>
                  <Text style={styles.coordLabel}>Lng</Text>
                  <TextInput style={styles.input} value={destLng} onChangeText={setDestLng}
                    keyboardType="numeric" placeholderTextColor={colors.textMuted} testID="journey-dest-lng" />
                </View>
              </View>

              <TouchableOpacity
                style={[styles.startBtn, loading && styles.btnDisabled]}
                onPress={startJourney}
                disabled={loading}
                testID="start-journey-btn"
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <Ionicons name="play-circle" size={22} color={colors.white} />
                    <Text style={styles.startBtnText}>Start Journey</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        )}

        {tab === 'active' && (
          <View style={styles.section}>
            {activeSession ? (
              <View style={styles.card}>
                <View style={styles.liveHeader}>
                  <View style={styles.liveDot} />
                  <Text style={styles.liveText}>LIVE</Text>
                </View>
                <Text style={styles.cardTitle}>Journey Active</Text>
                <Text style={styles.cardDesc}>
                  Session: {activeSession.session_id?.slice(0, 12)}...
                </Text>

                <View style={styles.statusGrid}>
                  <StatusItem icon="time" label="Started" value={formatTime(activeSession.start_time)} />
                  <StatusItem icon="pulse" label="Status" value={activeSession.status || 'active'} />
                </View>

                <TouchableOpacity
                  style={[styles.stopBtn, loading && styles.btnDisabled]}
                  onPress={stopJourney}
                  disabled={loading}
                  testID="stop-journey-btn"
                >
                  {loading ? (
                    <ActivityIndicator color={colors.white} />
                  ) : (
                    <>
                      <Ionicons name="stop-circle" size={22} color={colors.white} />
                      <Text style={styles.stopBtnText}>End Journey</Text>
                    </>
                  )}
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.emptyCard}>
                <Ionicons name="navigate-outline" size={48} color={colors.textMuted} />
                <Text style={styles.emptyText}>No active journey</Text>
                <TouchableOpacity onPress={() => setTab('start')}>
                  <Text style={styles.emptyLink}>Start one now</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        )}

        {tab === 'routes' && (
          <View style={styles.section}>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Safe Route Finder</Text>
              <Text style={styles.cardDesc}>Compare routes by safety score</Text>

              <Text style={styles.inputLabel}>Origin</Text>
              <View style={styles.coordRow}>
                <View style={styles.coordInput}>
                  <Text style={styles.coordLabel}>Lat</Text>
                  <TextInput style={styles.input} value={startLat} onChangeText={setStartLat}
                    keyboardType="numeric" placeholderTextColor={colors.textMuted} testID="route-start-lat" />
                </View>
                <View style={styles.coordInput}>
                  <Text style={styles.coordLabel}>Lng</Text>
                  <TextInput style={styles.input} value={startLng} onChangeText={setStartLng}
                    keyboardType="numeric" placeholderTextColor={colors.textMuted} testID="route-start-lng" />
                </View>
              </View>

              <Text style={styles.inputLabel}>Destination</Text>
              <View style={styles.coordRow}>
                <View style={styles.coordInput}>
                  <Text style={styles.coordLabel}>Lat</Text>
                  <TextInput style={styles.input} value={endLat} onChangeText={setEndLat}
                    keyboardType="numeric" placeholderTextColor={colors.textMuted} testID="route-end-lat" />
                </View>
                <View style={styles.coordInput}>
                  <Text style={styles.coordLabel}>Lng</Text>
                  <TextInput style={styles.input} value={endLng} onChangeText={setEndLng}
                    keyboardType="numeric" placeholderTextColor={colors.textMuted} testID="route-end-lng" />
                </View>
              </View>

              <TouchableOpacity
                style={[styles.startBtn, routeLoading && styles.btnDisabled]}
                onPress={fetchRoutes}
                disabled={routeLoading}
                testID="find-routes-btn"
              >
                {routeLoading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <Ionicons name="map" size={20} color={colors.white} />
                    <Text style={styles.startBtnText}>Find Safe Routes</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>

            {routes?.routes && routes.routes.map((route: any, i: number) => (
              <RouteCard key={i} route={route} index={i} />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function StatusItem({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <View style={styles.statusItem}>
      <Ionicons name={icon as any} size={18} color={colors.textMuted} />
      <Text style={styles.statusLabel}>{label}</Text>
      <Text style={styles.statusValue}>{value}</Text>
    </View>
  );
}

function RouteCard({ route, index }: { route: any; index: number }) {
  const typeColors: Record<string, string> = { safest: colors.safe, balanced: colors.primary, shortest: colors.warning };
  const color = typeColors[route.type] || colors.textMuted;
  return (
    <View style={[styles.routeCard, { borderLeftColor: color, borderLeftWidth: 3 }]} testID={`route-card-${index}`}>
      <View style={styles.routeHeader}>
        <Text style={[styles.routeType, { color }]}>{route.type?.toUpperCase()}</Text>
        <Text style={[styles.routeScore, { color: scoreColor(route.safety_score || 5) }]}>
          {(route.safety_score || 0).toFixed(1)}/10
        </Text>
      </View>
      <View style={styles.routeStats}>
        <Text style={styles.routeStat}>{((route.distance || 0) / 1000).toFixed(1)} km</Text>
        <Text style={styles.routeStat}>{Math.round((route.duration || 0) / 60)} min</Text>
        <Text style={styles.routeStat}>{route.danger_count || 0} risks</Text>
      </View>
    </View>
  );
}

function formatTime(ts: string | null) {
  if (!ts) return '--';
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: spacing['5xl'] },
  title: { fontSize: fontSize['2xl'], fontWeight: '800', color: colors.textPrimary, marginBottom: spacing.lg },
  tabs: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.xl },
  tab: { flex: 1, paddingVertical: spacing.md, borderRadius: radius.lg, backgroundColor: colors.bgCard, alignItems: 'center', borderWidth: 1, borderColor: colors.border },
  tabActive: { backgroundColor: colors.primary + '20', borderColor: colors.primary },
  tabText: { fontSize: fontSize.sm, fontWeight: '600', color: colors.textMuted },
  tabTextActive: { color: colors.primary },
  section: { gap: spacing.lg },
  card: { backgroundColor: colors.bgCard, borderRadius: radius.xl, padding: spacing.xl, borderWidth: 1, borderColor: colors.border, ...shadows.md },
  cardTitle: { fontSize: fontSize.xl, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.xs },
  cardDesc: { fontSize: fontSize.sm, color: colors.textSecondary, marginBottom: spacing.xl },
  inputLabel: { fontSize: fontSize.sm, fontWeight: '600', color: colors.textSecondary, marginBottom: spacing.sm, marginTop: spacing.md },
  coordRow: { flexDirection: 'row', gap: spacing.md },
  coordInput: { flex: 1 },
  coordLabel: { fontSize: fontSize.xs, color: colors.textMuted, marginBottom: 4 },
  input: { backgroundColor: colors.bgInput, borderRadius: radius.md, paddingHorizontal: spacing.md, height: 44, color: colors.textPrimary, fontSize: fontSize.md, borderWidth: 1, borderColor: colors.border },
  startBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.sm, backgroundColor: colors.primary, borderRadius: radius.lg, height: 52, marginTop: spacing.xl },
  startBtnText: { color: colors.white, fontSize: fontSize.lg, fontWeight: '700' },
  btnDisabled: { opacity: 0.6 },
  stopBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.sm, backgroundColor: colors.critical, borderRadius: radius.lg, height: 52, marginTop: spacing.xl },
  stopBtnText: { color: colors.white, fontSize: fontSize.lg, fontWeight: '700' },
  liveHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.lg },
  liveDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.safe },
  liveText: { fontSize: fontSize.sm, fontWeight: '800', color: colors.safe, letterSpacing: 2 },
  statusGrid: { flexDirection: 'row', gap: spacing.lg, marginTop: spacing.md },
  statusItem: { flex: 1, alignItems: 'center', gap: 4 },
  statusLabel: { fontSize: fontSize.xs, color: colors.textMuted },
  statusValue: { fontSize: fontSize.md, fontWeight: '700', color: colors.textPrimary, textTransform: 'capitalize' },
  emptyCard: { backgroundColor: colors.bgCard, borderRadius: radius.xl, padding: spacing['4xl'], alignItems: 'center', gap: spacing.md, borderWidth: 1, borderColor: colors.border },
  emptyText: { fontSize: fontSize.md, color: colors.textMuted },
  emptyLink: { fontSize: fontSize.md, color: colors.primary, fontWeight: '600' },
  routeCard: { backgroundColor: colors.bgCard, borderRadius: radius.lg, padding: spacing.lg, borderWidth: 1, borderColor: colors.border, marginTop: spacing.md },
  routeHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  routeType: { fontSize: fontSize.sm, fontWeight: '800', letterSpacing: 1 },
  routeScore: { fontSize: fontSize.lg, fontWeight: '800' },
  routeStats: { flexDirection: 'row', gap: spacing.xl },
  routeStat: { fontSize: fontSize.sm, color: colors.textSecondary },
});
