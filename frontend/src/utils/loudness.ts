import type { Track } from '@/types/track'

/** Match backend defaults (DJ_REVIEW_*). */
export const DEFAULT_REVIEW_LUFS_THRESHOLD = -18
export const DEFAULT_REVIEW_PEAK_THRESHOLD = 3.0

export interface LoudnessThresholds {
  lufs: number
  peak: number
}

export const DEFAULT_LOUDNESS_THRESHOLDS: LoudnessThresholds = {
  lufs: DEFAULT_REVIEW_LUFS_THRESHOLD,
  peak: DEFAULT_REVIEW_PEAK_THRESHOLD,
}

export type LoudnessStatus = 'unknown' | 'ok' | 'quiet' | 'clipped'

export function loudnessStatus(
  track: Track,
  thresholds: LoudnessThresholds = DEFAULT_LOUDNESS_THRESHOLDS,
): LoudnessStatus {
  if (track.integrated_lufs == null && track.true_peak_db == null) {
    return 'unknown'
  }
  const quiet =
    track.integrated_lufs != null && track.integrated_lufs < thresholds.lufs
  const clipped =
    track.true_peak_db != null && track.true_peak_db > thresholds.peak
  if (clipped) {
    return 'clipped'
  }
  if (quiet) {
    return 'quiet'
  }
  return 'ok'
}

export function loudnessStatusLabel(status: LoudnessStatus): string {
  switch (status) {
    case 'ok':
      return 'OK'
    case 'quiet':
      return 'Too quiet'
    case 'clipped':
      return 'High peak'
    default:
      return 'Not analyzed'
  }
}

export function loudnessStatusColor(status: LoudnessStatus): string {
  switch (status) {
    case 'ok':
      return 'success'
    case 'quiet':
      return 'warning'
    case 'clipped':
      return 'error'
    default:
      return 'default'
  }
}

export function formatIntegratedLufs(value: number | null): string {
  if (value == null) {
    return '—'
  }
  return `${value.toFixed(1)} LUFS`
}

export function formatTruePeak(value: number | null): string {
  if (value == null) {
    return '—'
  }
  return `${value.toFixed(1)} dBTP`
}

export function formatLoudnessSummary(track: Track): string {
  const parts: string[] = []
  if (track.integrated_lufs != null) {
    parts.push(formatIntegratedLufs(track.integrated_lufs))
  }
  if (track.true_peak_db != null) {
    parts.push(`peak ${formatTruePeak(track.true_peak_db)}`)
  }
  return parts.length > 0 ? parts.join(' · ') : '—'
}
