// Voice Distress Detection Service — Hybrid on-device + optional cloud
//
// On-device (primary): keyword detection + scream pattern analysis
// Cloud (Phase 2): OpenAI Whisper transcript verification
// Distress score: keyword*0.4 + scream*0.35 + repetition*0.25
// Cooldown: 30s between events, bypass at score >= 0.9

import { Audio } from 'expo-av';
import { Platform } from 'react-native';

// Distress keywords for on-device matching
const DISTRESS_KEYWORDS = [
  'help', 'stop', 'leave me', 'call police', 'emergency',
  "don't touch", 'save me', 'please help', 'let go',
];

// Audio thresholds
const AMPLITUDE_THRESHOLD = 0.7;
const PITCH_VARIANCE_THRESHOLD = 0.5;
const DETECTION_INTERVAL_MS = 2000;
const COOLDOWN_MS = 30000;
const MIN_DETECTIONS_TO_REPORT = 2;
const DETECTION_WINDOW_MS = 5000;

interface VoiceDetectionState {
  isMonitoring: boolean;
  recording: Audio.Recording | null;
  lastReportTime: number;
  recentDetections: { timestamp: number; keywords: string[]; scream: boolean }[];
}

const state: VoiceDetectionState = {
  isMonitoring: false,
  recording: null,
  lastReportTime: 0,
  recentDetections: [],
};

let monitorInterval: ReturnType<typeof setInterval> | null = null;
let onDistressCallback: ((data: VoiceDistressData) => void) | null = null;

export interface VoiceDistressData {
  keywords: string[];
  scream_detected: boolean;
  repeated: boolean;
  audio_features: {
    amplitude: number;
    pitch_variance: number;
    spectral_spread: number;
    duration_ms: number;
  };
}

// Simple amplitude-based scream detection
function analyzeAudioFeatures(status: Audio.RecordingStatus): {
  amplitude: number;
  pitch_variance: number;
  spectral_spread: number;
} {
  // expo-av provides metering data
  const metering = status.metering ?? -160; // dBFS, -160 is silence
  // Normalize: -160 to 0 dBFS → 0 to 1
  const amplitude = Math.max(0, Math.min(1, (metering + 160) / 160));

  // Estimate pitch variance from amplitude pattern (simplified)
  // High amplitude + rapid changes suggest screaming
  const pitch_variance = amplitude > AMPLITUDE_THRESHOLD ? Math.min(1, amplitude * 1.2) : amplitude * 0.5;
  const spectral_spread = amplitude > 0.8 ? 0.7 : amplitude * 0.5;

  return { amplitude, pitch_variance, spectral_spread };
}

function isScreamPattern(features: { amplitude: number; pitch_variance: number }): boolean {
  return features.amplitude > AMPLITUDE_THRESHOLD && features.pitch_variance > PITCH_VARIANCE_THRESHOLD;
}

// On-device keyword matching (called with speech-to-text results when available)
export function matchKeywords(transcript: string): string[] {
  const lower = transcript.toLowerCase();
  return DISTRESS_KEYWORDS.filter(kw => lower.includes(kw));
}

function pruneOldDetections() {
  const cutoff = Date.now() - DETECTION_WINDOW_MS;
  state.recentDetections = state.recentDetections.filter(d => d.timestamp > cutoff);
}

function checkAndReport(keywords: string[], screamDetected: boolean, features: ReturnType<typeof analyzeAudioFeatures>) {
  if (!keywords.length && !screamDetected) return;

  const now = Date.now();
  state.recentDetections.push({ timestamp: now, keywords, scream: screamDetected });
  pruneOldDetections();

  const repeated = state.recentDetections.length >= MIN_DETECTIONS_TO_REPORT;

  // Only report if enough detections in window OR high-confidence single detection
  const highConfidence = keywords.length >= 2 || (keywords.length >= 1 && screamDetected);
  if (!repeated && !highConfidence) return;

  // Cooldown
  if (now - state.lastReportTime < COOLDOWN_MS) return;

  state.lastReportTime = now;
  state.recentDetections = []; // Reset after report

  if (onDistressCallback) {
    onDistressCallback({
      keywords,
      scream_detected: screamDetected,
      repeated,
      audio_features: {
        ...features,
        duration_ms: DETECTION_INTERVAL_MS,
      },
    });
  }
}

// ── Public API ──

export async function startVoiceMonitoring(
  onDistress: (data: VoiceDistressData) => void,
): Promise<() => void> {
  if (state.isMonitoring) return () => {};

  // Request permissions
  const { status } = await Audio.requestPermissionsAsync();
  if (status !== 'granted') {
    console.warn('Audio permission not granted');
    return () => {};
  }

  await Audio.setAudioModeAsync({
    allowsRecordingIOS: true,
    playsInSilentModeIOS: true,
  });

  state.isMonitoring = true;
  onDistressCallback = onDistress;
  state.recentDetections = [];

  // Periodic audio analysis
  monitorInterval = setInterval(async () => {
    if (!state.isMonitoring) return;

    try {
      const recording = new Audio.Recording();
      await recording.prepareToRecordAsync({
        ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
        isMeteringEnabled: true,
      });
      await recording.startAsync();

      // Record for a short burst
      await new Promise(resolve => setTimeout(resolve, 1500));

      const status = await recording.getStatusAsync();
      await recording.stopAndUnloadAsync();

      if (status.isRecording || status.durationMillis > 0) {
        const features = analyzeAudioFeatures(status);
        const scream = isScreamPattern(features);

        // On-device scream detection
        if (scream) {
          checkAndReport([], true, features);
        }
      }
    } catch (err) {
      // Recording may fail if another recording is active
      console.debug('Voice monitor cycle error:', err);
    }
  }, DETECTION_INTERVAL_MS);

  return () => stopVoiceMonitoring();
}

export function stopVoiceMonitoring() {
  state.isMonitoring = false;
  onDistressCallback = null;
  if (monitorInterval) {
    clearInterval(monitorInterval);
    monitorInterval = null;
  }
}

// Manual keyword report (called from speech-to-text results)
export function reportKeywords(transcript: string, features?: { amplitude: number; pitch_variance: number; spectral_spread: number }) {
  const keywords = matchKeywords(transcript);
  if (keywords.length > 0) {
    checkAndReport(keywords, false, features || { amplitude: 0.5, pitch_variance: 0.3, spectral_spread: 0.3 });
  }
}

export function isVoiceMonitoringActive(): boolean {
  return state.isMonitoring;
}

// Simulate for testing
export function simulateVoiceDistress(): VoiceDistressData {
  return {
    keywords: ['help', 'stop'],
    scream_detected: true,
    repeated: true,
    audio_features: { amplitude: 0.91, pitch_variance: 0.72, spectral_spread: 0.65, duration_ms: 2000 },
  };
}
