// SafetyProvider — Global safety layer that survives screen transitions
// Manages: shake detection (always-on), fall detection (5-stage pipeline), emergency state recovery
import { useEffect, useRef, useState, useCallback } from 'react';
import { Vibration, Alert } from 'react-native';
import { useEmergencyStore } from '../stores/emergencyStore';
import { useAuthStore } from '../stores/authStore';
import {
  startShakeDetection,
  triggerSilentSOS,
  restoreEmergencyState,
} from '../services/deviceSafety';
import {
  startFallDetection,
  stopFallDetection,
  type FallSignals,
} from '../services/fallDetection';
import { api } from '../services/api';

const AUTO_SOS_COUNTDOWN_S = 10;

export function SafetyProvider({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const isActive = useEmergencyStore((s) => s.isActive);
  const restore = useEmergencyStore((s) => s.restore);
  const activate = useEmergencyStore((s) => s.activate);
  const setTriggering = useEmergencyStore((s) => s.setTriggering);
  const isActiveRef = useRef(isActive);
  const [fallPending, setFallPending] = useState<{
    eventId: string;
    countdown: number;
    confidence: number;
  } | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  // Fall confirmation handler
  const handleFallDetected = useCallback(async (confidence: number, signals: FallSignals) => {
    if (isActiveRef.current) return; // Already in emergency

    try {
      // Report fall to backend
      const res = await api.post('/sensors/fall', {
        lat: 0, lng: 0, // Will be updated with actual location
        ...signals,
      });

      if (res.data?.event_id) {
        setFallPending({
          eventId: res.data.event_id,
          countdown: AUTO_SOS_COUNTDOWN_S,
          confidence,
        });

        // Start countdown
        countdownRef.current = setInterval(() => {
          setFallPending(prev => {
            if (!prev) return null;
            const next = prev.countdown - 1;
            if (next <= 0) {
              // Auto-SOS
              triggerAutoSOS(prev.eventId);
              clearInterval(countdownRef.current!);
              return null;
            }
            return { ...prev, countdown: next };
          });
        }, 1000);
      }
    } catch (err) {
      console.error('Fall report error:', err);
    }
  }, []);

  const triggerAutoSOS = async (eventId: string) => {
    try {
      await api.post(`/sensors/fall/${eventId}/auto-sos`);
      const result = await triggerSilentSOS('1234', 'fall_detection');
      if (result.success && result.eventId) {
        await activate(result.eventId, 'fall_detection');
      }
    } catch (err) {
      console.error('Auto-SOS error:', err);
    }
  };

  const handleUserSafe = async () => {
    if (fallPending) {
      if (countdownRef.current) clearInterval(countdownRef.current);
      try {
        await api.post(`/sensors/fall/${fallPending.eventId}/resolve`, {
          resolved_by: 'user_confirmed_safe',
        });
      } catch {}
      setFallPending(null);
    }
  };

  const handleUserNeedsHelp = async () => {
    if (fallPending) {
      if (countdownRef.current) clearInterval(countdownRef.current);
      try {
        await api.post(`/sensors/fall/${fallPending.eventId}/resolve`, {
          resolved_by: 'user_called_help',
        });
      } catch {}
      const result = await triggerSilentSOS('1234', 'fall_detection');
      if (result.success && result.eventId) {
        await activate(result.eventId, 'fall_detection');
      }
      setFallPending(null);
    }
  };

  useEffect(() => {
    if (!token) return;

    // 1. Restore persisted emergency state
    const init = async () => {
      const restored = await restore();
      if (restored) {
        await restoreEmergencyState();
      }
    };
    init();

    // 2. Start global shake detection — IMMEDIATE SOS on shake
    const shakeCleanup = startShakeDetection(async () => {
      if (isActiveRef.current) return;
      if (useEmergencyStore.getState().isTriggering) return;

      Vibration.vibrate([0, 100, 50, 100]);
      setTriggering(true);

      const result = await triggerSilentSOS('1234', 'shake');
      if (result.success && result.eventId) {
        await activate(result.eventId, 'shake');
      } else if (result.error === 'offline_queued') {
        await activate('pending', 'shake');
      }
      setTriggering(false);
    });

    // 3. Start fall detection (5-stage Apple Watch-style pipeline)
    const fallCleanup = startFallDetection(handleFallDetected);

    return () => {
      shakeCleanup();
      fallCleanup();
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [token, handleFallDetected]);

  // Fall confirmation dialog overlay
  useEffect(() => {
    if (fallPending) {
      Alert.alert(
        'Possible Fall Detected',
        `Are you okay? (${fallPending.countdown}s)\nConfidence: ${(fallPending.confidence * 100).toFixed(0)}%\n\nHelp will be sent automatically if no response.`,
        [
          { text: "I'm OK", style: 'cancel', onPress: handleUserSafe },
          { text: 'Send Help', style: 'destructive', onPress: handleUserNeedsHelp },
        ],
        { cancelable: false }
      );
    }
  }, [fallPending?.countdown]);

  return <>{children}</>;
}
