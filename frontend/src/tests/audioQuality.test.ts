import { describe, expect, it } from 'vitest'

import type { Track } from '@/types/track'
import {
  compareBitrateTracks,
  compareQualityTracks,
  formatAudioQualityLabel,
  formatBitrateLabel,
  formatExtensionLabel,
  qualitySortKey,
} from '@/utils/audioQuality'

function track(overrides: Partial<Track> = {}): Track {
  return {
    id: 1,
    status: 'ready',
    source_path: '/data/watch/song.mp3',
    processing_path: null,
    final_path: null,
    artist: null,
    title: null,
    album: null,
    genre: null,
    subgenre: null,
    mix_version: null,
    tag_confidence: null,
    needs_metadata_review: false,
    bpm: null,
    musical_key: null,
    camelot: null,
    energy: null,
    scale: null,
    bpm_confidence: null,
    key_confidence: null,
    integrated_lufs: null,
    true_peak_db: null,
    format_extension: null,
    audio_family: null,
    bitrate_kbps: null,
    sample_rate_hz: null,
    bits_per_sample: null,
    created_at: '',
    updated_at: '',
    ...overrides,
  }
}

describe('audioQuality', () => {
  it('formats extension without dot', () => {
    expect(formatExtensionLabel('.wav')).toBe('WAV')
  })

  it('formats mp3 bitrate', () => {
    expect(formatBitrateLabel(320, 'mp3')).toBe('320 kbps')
  })

  it('shows dash for lossless bitrate', () => {
    expect(formatBitrateLabel(null, 'lossless')).toBe('—')
  })

  it('formats lossless quality', () => {
    expect(
      formatAudioQualityLabel(
        track({
          audio_family: 'lossless',
          bits_per_sample: 24,
          sample_rate_hz: 48000,
        }),
      ),
    ).toBe('24-bit / 48 kHz')
  })

  it('sorts lossless quality higher than mp3', () => {
    const wav = track({
      audio_family: 'lossless',
      bits_per_sample: 16,
      sample_rate_hz: 44100,
    })
    const mp3 = track({ audio_family: 'mp3', bitrate_kbps: 320 })
    expect(compareQualityTracks(wav, mp3)).toBeGreaterThan(0)
    expect(qualitySortKey(wav)).toBeGreaterThan(qualitySortKey(mp3))
  })

  it('sorts mp3 by bitrate', () => {
    const low = track({ audio_family: 'mp3', bitrate_kbps: 128 })
    const high = track({ audio_family: 'mp3', bitrate_kbps: 320 })
    expect(compareBitrateTracks(high, low)).toBeGreaterThan(0)
  })
})
