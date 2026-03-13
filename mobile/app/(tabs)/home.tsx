// Home Safety Dashboard — with Silent SOS integration
// Shake detection is handled by SafetyProvider (global, survives screen transitions)
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, Alert, TextInput, Modal, Vibration, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuthStore } from '@/stores/authStore';
import { useEmergencyStore } from '@/stores/emergencyStore';
import { safetyScoreService, guardianService } from '@/services/endpoints';
import { emergencyService } from '@/services/emergency';
import { triggerSilentSOS, cancelSOS } from '@/services/deviceSafety';
import { colors, spacing, fontSize, radius, shadows, scoreColor, scoreLabel } from '@/theme';

const PROFILE_LABELS: Record<string, string> = {
  women: 'Women Safety', kids: 'Kids Safety', parents: 'Parents Care',
};
const PROFILE_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  women: 'shield-half-outline', kids: 'happy-outline', parents: 'heart-outline',
};

// Hidden trigger: 5 taps in 3 seconds on greeting text
const HIDDEN_TAP_COUNT = 5;
const HIDDEN_TAP_WINDOW = 3000;

export default function HomeScreen() {
  const { user, profileMode } = useAuthStore();
  const { isActive, eventId, isTriggering, activate, deactivate, setTriggering } = useEmergencyStore();
  const router = useRouter();

  const [refreshing, setRefreshing] = useState(false);
  const [safetyScore, setSafetyScore] = useState<any>(null);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [showSOSConfirm, setShowSOSConfirm] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelPin, setCancelPin] = useState('');
  const [sosPin, setSosPin] = useState('1234');

  // Hidden trigger tap tracking
  const tapTimestamps = useRef<number[]>([]);

  // Pulse animation for emergency banner
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!isActive) return;
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.4, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [isActive]);

  const fetchData = useCallback(async () => {
    try {
      const scoreRes = await safetyScoreService.getLocationScore(12.9716, 77.5946);
      setSafetyScore(scoreRes.data);
    } catch {}
    try {
      const sessRes = await guardianService.listActive();
      const sessions = sessRes.data?.sessions || sessRes.data || [];
      setActiveSession(sessions.length > 0 ? sessions[0] : null);
    } catch {}

    // Sync with backend active emergencies
    if (!isActive) {
      try {
        const emergRes = await emergencyService.getActive();
        const events = emergRes.data?.events || [];
        if (events.length > 0) {
          await activate(events[0].event_id, 'restored');
        }
      } catch {}
    }

    setLoading(false);
  }, [isActive]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  // Hidden trigger: multi-tap on greeting
  const handleHiddenTap = async () => {
    if (isActive || isTriggering) return;
    const now = Date.now();
    tapTimestamps.current.push(now);
    tapTimestamps.current = tapTimestamps.current.filter((t) => now - t < HIDDEN_TAP_WINDOW);

    if (tapTimestamps.current.length >= HIDDEN_TAP_COUNT) {
      tapTimestamps.current = [];
      // Trigger SOS immediately — no confirmation
      Vibration.vibrate([0, 100, 50, 100]);
      setTriggering(true);
      const result = await triggerSilentSOS('1234', 'hidden_tap');
      if (result.success && result.eventId) {
        await activate(result.eventId, 'hidden_tap');
      } else if (result.error === 'offline_queued') {
        await activate('pending', 'hidden_tap');
      }
      setTriggering(false);
    }
  };

  // Manual SOS via button — uses confirmation modal
  const handleTriggerSOS = async () => {
    setTriggering(true);
    setShowSOSConfirm(false);
    const result = await triggerSilentSOS(sosPin, 'manual_button');

    if (result.success && result.eventId) {
      await activate(result.eventId, 'manual_button');
      Alert.alert('SOS Sent', 'Emergency alert sent to your guardians immediately.');
    } else if (result.error === 'offline_queued') {
      await activate('pending', 'manual_button');
      Alert.alert('SOS Queued', 'No internet. SOS will be sent when connection is available.');
    } else {
      Alert.alert('Error', result.error || 'Failed to trigger SOS');
    }
    setTriggering(false);
  };

  const handleCancelSOS = async () => {
    if (!cancelPin) {
      Alert.alert('PIN Required', 'Enter your cancellation PIN');
      return;
    }
    const result = await cancelSOS(cancelPin);
    if (result.success) {
      await deactivate();
      setShowCancelModal(false);
      setCancelPin('');
      Alert.alert('Cancelled', 'Emergency cancelled. Guardians notified.');
    } else {
      Alert.alert('Error', result.error || 'Invalid PIN');
    }
  };

  const score = safetyScore?.score ?? 0;
  const greeting = getGreeting();

  return (
    <SafeAreaView style={styles.safe} testID="home-dashboard">
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
        }
      >
        {/* Emergency Active Banner */}
        {isActive && (
          <TouchableOpacity
            style={styles.emergencyBanner}
            onPress={() => setShowCancelModal(true)}
            testID="emergency-active-banner"
            activeOpacity={0.8}
          >
            <Animated.View style={[styles.emergencyPulse, { opacity: pulseAnim }]} />
            <View style={styles.emergencyInfo}>
              <Text style={styles.emergencyTitle}>EMERGENCY ACTIVE</Text>
              <Text style={styles.emergencySub}>Live tracking enabled</Text>
              <Text style={styles.emergencyAction}>Cancel with PIN</Text>
            </View>
            <Ionicons name="close-circle" size={28} color={colors.white} />
          </TouchableOpacity>
        )}

        {/* Triggering indicator */}
        {isTriggering && !isActive && (
          <View style={styles.triggeringBanner} testID="sos-triggering-banner">
            <Ionicons name="radio" size={20} color={colors.warning} />
            <Text style={styles.triggeringText}>Sending SOS...</Text>
          </View>
        )}

        {/* Header — greeting is hidden SOS trigger (5 taps in 3s) */}
        <View style={styles.header}>
          <TouchableOpacity onPress={handleHiddenTap} activeOpacity={1} testID="hidden-sos-trigger">
            <Text style={styles.greeting}>{greeting}</Text>
            <Text style={styles.userName}>{user?.full_name || 'User'}</Text>
          </TouchableOpacity>
          <View style={styles.profileBadge}>
            <Ionicons name={PROFILE_ICONS[profileMode]} size={16} color={colors.primary} />
            <Text style={styles.profileText}>{PROFILE_LABELS[profileMode]}</Text>
          </View>
        </View>

        {/* Safety Score Ring */}
        <TouchableOpacity
          style={styles.scoreCard}
          onPress={() => router.push('/(tabs)/safety-score')}
          testID="home-score-card"
        >
          <View style={styles.scoreRing}>
            <View style={[styles.scoreCircle, { borderColor: scoreColor(score) }]}>
              <Text style={[styles.scoreNum, { color: scoreColor(score) }]}>
                {loading ? '--' : score.toFixed(1)}
              </Text>
              <Text style={styles.scoreOf}>/10</Text>
            </View>
          </View>
          <View style={styles.scoreMeta}>
            <Text style={[styles.scoreLabel, { color: scoreColor(score) }]}>
              {loading ? 'Loading...' : scoreLabel(score)}
            </Text>
            <Text style={styles.scoreDesc}>Your area safety score</Text>
            {safetyScore?.trend && (
              <View style={styles.trendRow}>
                <Ionicons
                  name={
                    safetyScore.trend === 'rising'
                      ? 'trending-up'
                      : safetyScore.trend === 'falling'
                        ? 'trending-down'
                        : 'remove'
                  }
                  size={16}
                  color={
                    safetyScore.trend === 'rising'
                      ? colors.safe
                      : safetyScore.trend === 'falling'
                        ? colors.critical
                        : colors.textMuted
                  }
                />
                <Text style={styles.trendText}>{safetyScore.trend} trend</Text>
              </View>
            )}
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
        </TouchableOpacity>

        {/* Quick Actions */}
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          <ActionCard
            icon="navigate-circle" label="Start Journey" color={colors.primary}
            onPress={() => router.push('/(tabs)/journey')} testID="action-start-journey"
          />
          <ActionCard
            icon="map" label="Safe Routes" color={colors.verySafe}
            onPress={() => router.push('/(tabs)/journey')} testID="action-safe-routes"
          />
          <ActionCard
            icon="warning" label="Alerts" color={colors.warning}
            onPress={() => router.push('/(tabs)/alerts')} testID="action-alerts"
          />
          <ActionCard
            icon="share-social" label="Share Safety" color={colors.accent}
            onPress={() => router.push('/(tabs)/guardian')} testID="action-share-safety"
          />
        </View>

        {/* Active Session */}
        {activeSession && (
          <View style={styles.sessionCard} testID="active-session-card">
            <View style={styles.sessionDot} />
            <View style={styles.sessionInfo}>
              <Text style={styles.sessionTitle}>Active Journey</Text>
              <Text style={styles.sessionSub}>
                Session: {activeSession.session_id?.slice(0, 8)}...
              </Text>
            </View>
            <TouchableOpacity
              style={styles.sessionBtn}
              onPress={() => router.push('/(tabs)/journey')}
            >
              <Text style={styles.sessionBtnText}>View</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* SOS Button */}
        <TouchableOpacity
          style={[styles.sosBtn, isActive && styles.sosBtnActive]}
          onLongPress={() => {
            if (!isActive) {
              Vibration.vibrate([0, 100, 50, 100]);
              setShowSOSConfirm(true);
            } else {
              setShowCancelModal(true);
            }
          }}
          delayLongPress={1500}
          disabled={isTriggering}
          testID="sos-trigger-btn"
        >
          <Ionicons
            name={isActive ? 'pulse' : 'alert-circle'}
            size={28}
            color={isActive ? colors.white : colors.critical}
          />
          <Text style={[styles.sosText, isActive && styles.sosTextActive]}>
            {isActive ? 'SOS ACTIVE — TAP TO CANCEL' : 'SILENT SOS'}
          </Text>
          <Text style={[styles.sosHint, isActive && styles.sosHintActive]}>
            {isActive ? 'Long press to cancel' : 'Long press 1.5s or shake phone 3x'}
          </Text>
        </TouchableOpacity>
      </ScrollView>

      {/* SOS Confirm Modal (for manual button only) */}
      <Modal visible={showSOSConfirm} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard} testID="sos-confirm-modal">
            <Ionicons name="alert-circle" size={48} color={colors.critical} />
            <Text style={styles.modalTitle}>Trigger Silent SOS?</Text>
            <Text style={styles.modalDesc}>
              Your guardians will be alerted IMMEDIATELY with your location.
            </Text>
            <Text style={styles.modalLabel}>Set Cancel PIN (4 digits)</Text>
            <TextInput
              style={styles.pinInput}
              value={sosPin}
              onChangeText={setSosPin}
              keyboardType="numeric"
              maxLength={4}
              secureTextEntry
              placeholder="1234"
              placeholderTextColor={colors.textMuted}
              testID="sos-pin-input"
            />
            <View style={styles.modalBtns}>
              <TouchableOpacity
                style={styles.modalCancelBtn}
                onPress={() => setShowSOSConfirm(false)}
                testID="sos-dismiss-btn"
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalConfirmBtn, isTriggering && { opacity: 0.6 }]}
                onPress={handleTriggerSOS}
                disabled={isTriggering}
                testID="sos-confirm-btn"
              >
                <Text style={styles.modalConfirmText}>
                  {isTriggering ? 'Sending...' : 'SEND SOS'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Cancel Modal */}
      <Modal visible={showCancelModal} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard} testID="cancel-sos-modal">
            <Ionicons name="shield-checkmark" size={48} color={colors.safe} />
            <Text style={styles.modalTitle}>Cancel Emergency?</Text>
            <Text style={styles.modalDesc}>Enter your PIN to confirm you are safe.</Text>
            <TextInput
              style={styles.pinInput}
              value={cancelPin}
              onChangeText={setCancelPin}
              keyboardType="numeric"
              maxLength={4}
              secureTextEntry
              placeholder="Enter PIN"
              placeholderTextColor={colors.textMuted}
              testID="cancel-pin-input"
            />
            <View style={styles.modalBtns}>
              <TouchableOpacity
                style={styles.modalCancelBtn}
                onPress={() => {
                  setShowCancelModal(false);
                  setCancelPin('');
                }}
              >
                <Text style={styles.modalCancelText}>Back</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalSafeBtn}
                onPress={handleCancelSOS}
                testID="cancel-confirm-btn"
              >
                <Text style={styles.modalConfirmText}>I'm Safe</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function ActionCard({ icon, label, color, onPress, testID }: any) {
  return (
    <TouchableOpacity style={styles.actionCard} onPress={onPress} testID={testID}>
      <View style={[styles.actionIcon, { backgroundColor: color + '20' }]}>
        <Ionicons name={icon} size={24} color={color} />
      </View>
      <Text style={styles.actionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: spacing['5xl'] },

  // Emergency Banner
  emergencyBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.critical,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.xl,
    gap: spacing.md,
  },
  emergencyPulse: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.white,
  },
  emergencyInfo: { flex: 1 },
  emergencyTitle: {
    fontSize: fontSize.md,
    fontWeight: '800',
    color: colors.white,
    letterSpacing: 2,
  },
  emergencySub: {
    fontSize: fontSize.xs,
    color: colors.white + 'CC',
    marginTop: 2,
  },
  emergencyAction: {
    fontSize: fontSize.xs,
    color: colors.white + '99',
    marginTop: 1,
    fontStyle: 'italic',
  },

  // Triggering banner
  triggeringBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.warning + '20',
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.lg,
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.warning + '40',
  },
  triggeringText: {
    fontSize: fontSize.sm,
    fontWeight: '700',
    color: colors.warning,
  },

  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing['2xl'],
  },
  greeting: { fontSize: fontSize.md, color: colors.textSecondary },
  userName: {
    fontSize: fontSize['2xl'],
    fontWeight: '800',
    color: colors.textPrimary,
    marginTop: 2,
  },
  profileBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.bgElevated,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.border,
  },
  profileText: { fontSize: fontSize.xs, color: colors.primary, fontWeight: '600' },

  // Score Card
  scoreCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bgCard,
    borderRadius: radius.xl,
    padding: spacing.xl,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing['2xl'],
    ...shadows.md,
  },
  scoreRing: { marginRight: spacing.xl },
  scoreCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.bgElevated,
  },
  scoreNum: { fontSize: fontSize['2xl'], fontWeight: '900' },
  scoreOf: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: -2 },
  scoreMeta: { flex: 1 },
  scoreLabel: { fontSize: fontSize.lg, fontWeight: '700' },
  scoreDesc: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: 2 },
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginTop: spacing.xs,
  },
  trendText: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    textTransform: 'capitalize',
  },

  // Actions
  sectionTitle: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginBottom: spacing['2xl'],
  },
  actionCard: {
    width: '47%',
    backgroundColor: colors.bgCard,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    gap: spacing.sm,
  },
  actionIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionLabel: { fontSize: fontSize.sm, fontWeight: '600', color: colors.textPrimary },

  // Session
  sessionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bgCard,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.safe + '40',
    marginBottom: spacing['2xl'],
  },
  sessionDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.safe,
    marginRight: spacing.md,
  },
  sessionInfo: { flex: 1 },
  sessionTitle: { fontSize: fontSize.md, fontWeight: '700', color: colors.textPrimary },
  sessionSub: { fontSize: fontSize.sm, color: colors.textSecondary, marginTop: 2 },
  sessionBtn: {
    backgroundColor: colors.primary + '20',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
  },
  sessionBtnText: { fontSize: fontSize.sm, fontWeight: '600', color: colors.primary },

  // SOS Button
  sosBtn: {
    backgroundColor: colors.critical + '15',
    borderRadius: radius.xl,
    padding: spacing.xl,
    alignItems: 'center',
    gap: spacing.xs,
    borderWidth: 2,
    borderColor: colors.critical + '30',
  },
  sosBtnActive: {
    backgroundColor: colors.critical,
    borderColor: colors.critical,
  },
  sosText: { fontSize: fontSize.lg, fontWeight: '800', color: colors.critical },
  sosTextActive: { color: colors.white },
  sosHint: { fontSize: fontSize.xs, color: colors.textMuted },
  sosHintActive: { color: colors.white + 'AA' },

  // Modals
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing['3xl'],
  },
  modalCard: {
    backgroundColor: colors.bgCard,
    borderRadius: radius.xl,
    padding: spacing['3xl'],
    width: '100%',
    alignItems: 'center',
    gap: spacing.lg,
    ...shadows.lg,
  },
  modalTitle: { fontSize: fontSize.xl, fontWeight: '800', color: colors.textPrimary },
  modalDesc: { fontSize: fontSize.sm, color: colors.textSecondary, textAlign: 'center' },
  modalLabel: {
    fontSize: fontSize.sm,
    fontWeight: '600',
    color: colors.textSecondary,
    alignSelf: 'flex-start',
  },
  pinInput: {
    backgroundColor: colors.bgInput,
    borderRadius: radius.lg,
    width: '100%',
    height: 52,
    textAlign: 'center',
    fontSize: fontSize['2xl'],
    fontWeight: '800',
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
    letterSpacing: 10,
  },
  modalBtns: { flexDirection: 'row', gap: spacing.md, width: '100%' },
  modalCancelBtn: {
    flex: 1,
    height: 48,
    borderRadius: radius.lg,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.bgElevated,
    borderWidth: 1,
    borderColor: colors.border,
  },
  modalCancelText: { fontSize: fontSize.md, fontWeight: '600', color: colors.textSecondary },
  modalConfirmBtn: {
    flex: 1,
    height: 48,
    borderRadius: radius.lg,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.critical,
  },
  modalSafeBtn: {
    flex: 1,
    height: 48,
    borderRadius: radius.lg,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.safe,
  },
  modalConfirmText: { fontSize: fontSize.md, fontWeight: '700', color: colors.white },
});
