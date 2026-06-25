import { describe, expect, it } from 'vitest'

import type { Track } from '@/types/track'
import { compareNullableStrings, createTrackTableSort } from '@/utils/trackTableSort'

function track(overrides: Partial<Track> = {}): Track {
  return {
    id: 1,
    status: 'ready',
    pipeline_stage: 'ready',
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

describe('trackTableSort', () => {
  it('sorts by basename for filename column', () => {
    const sort = createTrackTableSort({ loudnessThresholds: { lufs: -18, peak: 3 } })
    const a = track({ source_path: '/data/watch/b-track.mp3' })
    const b = track({ source_path: '/data/watch/a-track.mp3' })
    expect(sort.filename(a, b)).toBeGreaterThan(0)
  })

  it('sorts by pipeline stage not raw status', () => {
    const sort = createTrackTableSort({ loudnessThresholds: { lufs: -18, peak: 3 } })
    const awaiting = track({ status: 'ingested', pipeline_stage: 'awaiting_analyze' })
    const ready = track({ status: 'ready', pipeline_stage: 'ready' })
    expect(sort.status(awaiting, ready)).toBeLessThan(0)
  })

  it('sorts quality using track fields', () => {
    const sort = createTrackTableSort({ loudnessThresholds: { lufs: -18, peak: 3 } })
    const wav = track({
      audio_family: 'lossless',
      bits_per_sample: 24,
      sample_rate_hz: 48000,
    })
    const mp3 = track({ audio_family: 'mp3', bitrate_kbps: 320 })
    expect(sort.quality(wav, mp3)).toBeGreaterThan(0)
  })

  it('puts empty strings last when comparing nullable strings', () => {
    expect(compareNullableStrings('House', null)).toBeLessThan(0)
    expect(compareNullableStrings(null, 'House')).toBeGreaterThan(0)
  })

  it('sorts by created_at chronologically', () => {
    const sort = createTrackTableSort({ loudnessThresholds: { lufs: -18, peak: 3 } })
    const older = track({ created_at: '2024-01-01T10:00:00Z' })
    const newer = track({ created_at: '2024-06-01T10:00:00Z' })
    expect(sort.created_at(older, newer)).toBeLessThan(0)
    expect(sort.created_at(newer, older)).toBeGreaterThan(0)
  })
})
