import { describe, expect, it } from 'vitest'

import type { Track } from '@/types/track'
import { loudnessStatus, formatLoudnessSummary } from '@/utils/loudness'

const baseTrack = {
  id: 1,
  status: 'ingested',
  source_path: '/a.mp3',
  processing_path: null,
  final_path: null,
  artist: null,
  title: null,
  album: null,
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
  created_at: '',
  updated_at: '',
} satisfies Track

describe('loudness utils', () => {
  it('detects too quiet', () => {
    expect(
      loudnessStatus({ ...baseTrack, integrated_lufs: -22, true_peak_db: -2 }),
    ).toBe('quiet')
  })

  it('detects clipping', () => {
    expect(
      loudnessStatus({ ...baseTrack, integrated_lufs: -12, true_peak_db: 0.2 }),
    ).toBe('clipped')
  })

  it('formats summary with LUFS and peak', () => {
    expect(
      formatLoudnessSummary({ ...baseTrack, integrated_lufs: -14.2, true_peak_db: -1.1 }),
    ).toBe('-14.2 LUFS · peak -1.1 dBTP')
  })
})
