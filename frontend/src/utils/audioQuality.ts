import type { Track } from '@/types/track'

export function formatExtensionLabel(extension: string | null | undefined): string {
  if (!extension) {
    return '—'
  }
  return extension.replace(/^\./, '').toUpperCase()
}

export function formatBitrateLabel(
  bitrateKbps: number | null | undefined,
  audioFamily: string | null | undefined,
): string {
  if (audioFamily !== 'mp3' || bitrateKbps == null) {
    return '—'
  }
  return `${bitrateKbps} kbps`
}

function formatSampleRate(hz: number): string {
  if (hz >= 1000 && hz % 1000 === 0) {
    return `${hz / 1000} kHz`
  }
  if (hz >= 1000) {
    return `${(hz / 1000).toFixed(1)} kHz`
  }
  return `${hz} Hz`
}

export function formatAudioQualityLabel(track: Track): string {
  if (track.audio_family !== 'lossless') {
    return '—'
  }
  const parts: string[] = []
  if (track.bits_per_sample != null) {
    parts.push(`${track.bits_per_sample}-bit`)
  }
  if (track.sample_rate_hz != null) {
    parts.push(formatSampleRate(track.sample_rate_hz))
  }
  return parts.length > 0 ? parts.join(' / ') : 'Lossless'
}

/** Higher is better; non-lossless tracks sort below lossless. */
export function qualitySortKey(track: Track): number {
  if (track.audio_family !== 'lossless') {
    return -1
  }
  const bits = track.bits_per_sample ?? 0
  const rate = track.sample_rate_hz ?? 0
  return bits * 1_000_000 + rate
}

export function compareQualityTracks(a: Track, b: Track): number {
  return qualitySortKey(a) - qualitySortKey(b)
}

export function compareBitrateTracks(a: Track, b: Track): number {
  const aRate = a.audio_family === 'mp3' ? (a.bitrate_kbps ?? -1) : -1
  const bRate = b.audio_family === 'mp3' ? (b.bitrate_kbps ?? -1) : -1
  return aRate - bRate
}
