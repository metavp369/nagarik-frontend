// Guardian / Share Tab — Guardian Family Dashboard for guardians, Share Safety for users
import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, Alert, Share, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/stores/authStore';
import { guardianDashboardService, guardianService, safetyScoreService } from '@/services/endpoints';
import { colors, spacing, fontSize, radius, shadows, riskColor, scoreColor, scoreLabel } from '@/theme';

export default function GuardianScreen() {
  const { user, logout } = useAuthStore();
  const isGuardian = user?.role === 'guardian';

  return isGuardian ? <GuardianDashboard /> : <ShareSafety />;
}

// ===== GUARDIAN DASHBOARD =====
function GuardianDashboard() {
  const { user, logout } = useAuthStore();
  const [lovedOnes, setLovedOnes] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tab, setTab] = useState<'overview' | 'alerts' | 'history' | 'settings'>('overview');

  const fetchData = useCallback(async () => {
    try {
      const [loRes, alRes, sesRes] = await Promise.all([
        guardianDashboardService.getLovedOnes().catch(() => ({ data: [] })),
        guardianDashboardService.getAlerts(20).catch(() => ({ data: [] })),
        guardianDashboardService.getSessions().catch(() => ({ data: [] })),
      ]);
      setLovedOnes(Array.isArray(loRes.data) ? loRes.data : loRes.data?.loved_ones || []);
      setAlerts(Array.isArray(alRes.data) ? alRes.data : alRes.data?.alerts || []);
      setSessions(Array.isArray(sesRes.data) ? sesRes.data : sesRes.data?.sessions || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = async () => { setRefreshing(true); await fetchData(); setRefreshing(false); };

  const requestCheck = async (userId: string) => {
    try {
      await guardianDashboardService.requestCheck(userId);
      Alert.alert('Check Requested', 'A safety check has been sent to your loved one.');
    } catch (e: any) {
      Alert.alert('Error', e.response?.data?.detail || 'Failed to request check');
    }
  };

  return (
    <SafeAreaView style={styles.safe} testID="guardian-dashboard">
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
      >
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Family Safety</Text>
            <Text style={styles.subtitle}>Monitor your loved ones</Text>
          </View>
          <TouchableOpacity onPress={logout} style={styles.logoutBtn} testID="logout-btn">
            <Ionicons name="log-out-outline" size={22} color={colors.textMuted} />
          </TouchableOpacity>
        </View>

        {/* Tabs */}
        <View style={styles.tabs}>
          {(['overview', 'alerts', 'history', 'settings'] as const).map((t) => (
            <TouchableOpacity
              key={t} style={[styles.tab, tab === t && styles.tabActive]}
              onPress={() => setTab(t)} testID={`guardian-tab-${t}`}
            >
              <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {loading ? (
          <ActivityIndicator size="large" color={colors.primary} style={{ marginTop: spacing['4xl'] }} />
        ) : (
          <>
            {tab === 'overview' && (
              <>
                {/* Active Sessions */}
                {sessions.length > 0 && (
                  <>
                    <Text style={styles.sectionTitle}>Active Journeys</Text>
                    {sessions.map((s: any, i: number) => (
                      <View key={i} style={styles.sessionCard} testID={`session-card-${i}`}>
                        <View style={styles.liveRow}>
                          <View style={styles.liveDot} />
                          <Text style={styles.liveText}>LIVE</Text>
                        </View>
                        <Text style={styles.sessionId}>Session: {s.session_id?.slice(0, 12)}...</Text>
                        <Text style={styles.sessionTime}>Started: {formatTime(s.start_time)}</Text>
                      </View>
                    ))}
                  </>
                )}

                {/* Loved Ones */}
                <Text style={styles.sectionTitle}>Loved Ones</Text>
                {lovedOnes.length === 0 ? (
                  <View style={styles.emptyCard}>
                    <Ionicons name="people-outline" size={40} color={colors.textMuted} />
                    <Text style={styles.emptyText}>No linked loved ones yet</Text>
                  </View>
                ) : (
                  lovedOnes.map((person: any, i: number) => (
                    <View key={i} style={styles.personCard} testID={`loved-one-${i}`}>
                      <View style={styles.personAvatar}>
                        <Ionicons name="person" size={24} color={colors.primary} />
                      </View>
                      <View style={styles.personInfo}>
                        <Text style={styles.personName}>{person.name || person.full_name || 'User'}</Text>
                        <Text style={styles.personStatus}>{person.status || 'Safe'}</Text>
                      </View>
                      <TouchableOpacity
                        style={styles.checkBtn}
                        onPress={() => requestCheck(person.user_id || person.id)}
                        testID={`check-btn-${i}`}
                      >
                        <Text style={styles.checkBtnText}>Check In</Text>
                      </TouchableOpacity>
                    </View>
                  ))
                )}
              </>
            )}

            {tab === 'alerts' && (
              <>
                <Text style={styles.sectionTitle}>Recent Alerts</Text>
                {alerts.length === 0 ? (
                  <View style={styles.emptyCard}>
                    <Ionicons name="shield-checkmark" size={40} color={colors.safe} />
                    <Text style={styles.emptyText}>No alerts</Text>
                  </View>
                ) : (
                  alerts.map((alert: any, i: number) => (
                    <View key={i} style={styles.alertCard} testID={`alert-item-${i}`}>
                      <View style={[styles.alertDot, { backgroundColor: riskColor(alert.severity || 'moderate') }]} />
                      <View style={styles.alertInfo}>
                        <Text style={styles.alertType}>{alert.type || 'Alert'}</Text>
                        <Text style={styles.alertTime}>{formatTime(alert.created_at || alert.timestamp)}</Text>
                      </View>
                    </View>
                  ))
                )}
              </>
            )}

            {tab === 'history' && (
              <>
                <Text style={styles.sectionTitle}>Journey History</Text>
                <HistorySection />
              </>
            )}

            {tab === 'settings' && (
              <View style={styles.settingsSection}>
                <Text style={styles.sectionTitle}>Account</Text>
                <View style={styles.settingCard}>
                  <Ionicons name="person" size={20} color={colors.primary} />
                  <Text style={styles.settingLabel}>{user?.full_name || 'User'}</Text>
                </View>
                <View style={styles.settingCard}>
                  <Ionicons name="mail" size={20} color={colors.primary} />
                  <Text style={styles.settingLabel}>{user?.email || ''}</Text>
                </View>
                <View style={styles.settingCard}>
                  <Ionicons name="shield" size={20} color={colors.primary} />
                  <Text style={styles.settingLabel}>Role: {user?.role}</Text>
                </View>
                <TouchableOpacity
                  style={styles.logoutFullBtn}
                  onPress={logout}
                  testID="settings-logout-btn"
                >
                  <Ionicons name="log-out" size={20} color={colors.critical} />
                  <Text style={styles.logoutFullText}>Sign Out</Text>
                </TouchableOpacity>
              </View>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function HistorySection() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    guardianDashboardService.getHistory()
      .then((res) => setHistory(Array.isArray(res.data) ? res.data : res.data?.sessions || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <ActivityIndicator color={colors.primary} />;
  if (history.length === 0) {
    return (
      <View style={styles.emptyCard}>
        <Ionicons name="time-outline" size={40} color={colors.textMuted} />
        <Text style={styles.emptyText}>No journey history</Text>
      </View>
    );
  }

  return (
    <>
      {history.map((h: any, i: number) => (
        <View key={i} style={styles.historyCard} testID={`history-item-${i}`}>
          <Ionicons name="navigate-circle" size={20} color={colors.primary} />
          <View style={styles.historyInfo}>
            <Text style={styles.historyId}>{h.session_id?.slice(0, 12)}...</Text>
            <Text style={styles.historyTime}>
              {formatTime(h.start_time)} — {h.end_time ? formatTime(h.end_time) : 'ongoing'}
            </Text>
          </View>
          <Text style={[styles.historyStatus, { color: h.status === 'completed' ? colors.safe : colors.warning }]}>
            {h.status || 'unknown'}
          </Text>
        </View>
      ))}
    </>
  );
}

// ===== SHARE SAFETY =====
function ShareSafety() {
  const { user, logout } = useAuthStore();
  const [score, setScore] = useState<any>(null);

  useEffect(() => {
    safetyScoreService.getLocationScore(12.9716, 77.5946)
      .then(res => setScore(res.data))
      .catch(() => {});
  }, []);

  const shareMyStatus = async () => {
    try {
      const s = score?.score?.toFixed(1) || '?';
      await Share.share({
        message: `I'm using Nagarik for safety monitoring. My current area safety score: ${s}/10 (${scoreLabel(score?.score || 0)}). Stay safe! Nagarik.care`,
      });
    } catch {}
  };

  return (
    <SafeAreaView style={styles.safe} testID="share-safety-screen">
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Share Safety</Text>
            <Text style={styles.subtitle}>Let your network know you're safe</Text>
          </View>
          <TouchableOpacity onPress={logout} style={styles.logoutBtn} testID="logout-btn">
            <Ionicons name="log-out-outline" size={22} color={colors.textMuted} />
          </TouchableOpacity>
        </View>

        {/* Share Card */}
        <View style={styles.shareCard} testID="share-card">
          <View style={styles.shareLogo}>
            <Ionicons name="shield-checkmark" size={32} color={colors.primary} />
          </View>
          <Text style={styles.shareTitle}>Nagarik</Text>
          {score && (
            <>
              <View style={[styles.shareScoreCircle, { borderColor: scoreColor(score.score) }]}>
                <Text style={[styles.shareScoreNum, { color: scoreColor(score.score) }]}>
                  {score.score.toFixed(1)}
                </Text>
                <Text style={styles.shareScoreOf}>/10</Text>
              </View>
              <Text style={[styles.shareLabel, { color: scoreColor(score.score) }]}>
                {scoreLabel(score.score)}
              </Text>
            </>
          )}
          <TouchableOpacity style={styles.shareSendBtn} onPress={shareMyStatus} testID="share-send-btn">
            <Ionicons name="share-social" size={20} color={colors.white} />
            <Text style={styles.shareSendText}>Share My Safety Status</Text>
          </TouchableOpacity>
        </View>

        {/* Guardian Management */}
        <Text style={styles.sectionTitle}>Your Guardians</Text>
        <View style={styles.emptyCard}>
          <Ionicons name="people-outline" size={40} color={colors.textMuted} />
          <Text style={styles.emptyText}>Guardian management coming soon</Text>
          <Text style={styles.emptyDesc}>Add trusted contacts who will receive your safety updates</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
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
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: spacing.lg },
  title: { fontSize: fontSize['2xl'], fontWeight: '800', color: colors.textPrimary },
  subtitle: { fontSize: fontSize.sm, color: colors.textSecondary },
  logoutBtn: { padding: spacing.sm },
  tabs: { flexDirection: 'row', gap: spacing.xs, marginBottom: spacing.xl },
  tab: { flex: 1, paddingVertical: spacing.sm, borderRadius: radius.lg, backgroundColor: colors.bgCard, alignItems: 'center', borderWidth: 1, borderColor: colors.border },
  tabActive: { backgroundColor: colors.primary + '20', borderColor: colors.primary },
  tabText: { fontSize: fontSize.xs, fontWeight: '600', color: colors.textMuted },
  tabTextActive: { color: colors.primary },
  sectionTitle: { fontSize: fontSize.lg, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.md, marginTop: spacing.lg },
  sessionCard: { backgroundColor: colors.bgCard, borderRadius: radius.lg, padding: spacing.lg, borderWidth: 1, borderColor: colors.safe + '30', marginBottom: spacing.md },
  liveRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.sm },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.safe },
  liveText: { fontSize: fontSize.xs, fontWeight: '800', color: colors.safe, letterSpacing: 2 },
  sessionId: { fontSize: fontSize.sm, fontWeight: '600', color: colors.textPrimary },
  sessionTime: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 2 },
  personCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.bgCard, borderRadius: radius.lg, padding: spacing.lg, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.md },
  personAvatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.primary + '20', justifyContent: 'center', alignItems: 'center', marginRight: spacing.md },
  personInfo: { flex: 1 },
  personName: { fontSize: fontSize.md, fontWeight: '700', color: colors.textPrimary },
  personStatus: { fontSize: fontSize.sm, color: colors.safe, marginTop: 2 },
  checkBtn: { backgroundColor: colors.primary + '20', paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, borderRadius: radius.full },
  checkBtnText: { fontSize: fontSize.sm, fontWeight: '600', color: colors.primary },
  emptyCard: { backgroundColor: colors.bgCard, borderRadius: radius.xl, padding: spacing['3xl'], alignItems: 'center', gap: spacing.sm, borderWidth: 1, borderColor: colors.border },
  emptyText: { fontSize: fontSize.md, color: colors.textMuted },
  emptyDesc: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: 'center' },
  alertCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.bgCard, borderRadius: radius.md, padding: spacing.md, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm },
  alertDot: { width: 8, height: 8, borderRadius: 4, marginRight: spacing.md },
  alertInfo: { flex: 1 },
  alertType: { fontSize: fontSize.sm, fontWeight: '600', color: colors.textPrimary, textTransform: 'capitalize' },
  alertTime: { fontSize: fontSize.xs, color: colors.textMuted },
  historyCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.bgCard, borderRadius: radius.md, padding: spacing.md, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm },
  historyInfo: { flex: 1 },
  historyId: { fontSize: fontSize.sm, fontWeight: '600', color: colors.textPrimary },
  historyTime: { fontSize: fontSize.xs, color: colors.textMuted },
  historyStatus: { fontSize: fontSize.xs, fontWeight: '700', textTransform: 'capitalize' },
  settingsSection: { gap: spacing.md },
  settingCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.bgCard, borderRadius: radius.md, padding: spacing.lg, borderWidth: 1, borderColor: colors.border },
  settingLabel: { fontSize: fontSize.md, color: colors.textPrimary },
  logoutFullBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.sm, backgroundColor: colors.critical + '15', borderRadius: radius.lg, padding: spacing.lg, marginTop: spacing.xl, borderWidth: 1, borderColor: colors.critical + '30' },
  logoutFullText: { fontSize: fontSize.md, fontWeight: '700', color: colors.critical },
  shareCard: { backgroundColor: colors.bgCard, borderRadius: radius.xl, padding: spacing['3xl'], alignItems: 'center', borderWidth: 1, borderColor: colors.border, ...shadows.lg, marginTop: spacing.lg },
  shareLogo: { marginBottom: spacing.md },
  shareTitle: { fontSize: fontSize.xl, fontWeight: '800', color: colors.textPrimary, letterSpacing: 3, marginBottom: spacing.xl },
  shareScoreCircle: { width: 100, height: 100, borderRadius: 50, borderWidth: 4, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.bgElevated, marginBottom: spacing.md },
  shareScoreNum: { fontSize: fontSize['3xl'], fontWeight: '900' },
  shareScoreOf: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: -4 },
  shareLabel: { fontSize: fontSize.lg, fontWeight: '700', marginBottom: spacing.xl },
  shareSendBtn: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.primary, borderRadius: radius.full, paddingHorizontal: spacing['2xl'], paddingVertical: spacing.md },
  shareSendText: { color: colors.white, fontSize: fontSize.md, fontWeight: '700' },
});
