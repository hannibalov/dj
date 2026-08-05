import { describe, expect, it } from 'vitest'

import type { Track } from '@/types/track'
import { loudnessStatus, formatLoudnessSummary } from '@/utils/loudness'

const baseTrack = {
  id: 1,
  status: 'ingested',
  pipeline_stage: 'awaiting_fingerprint',
  source_path: '/a.mp3',
  processing_path: null,
  final_path: null,
  artist: null,
  title: null,
  album: null,
  genre: null,
  subgenre: null,
  metadata_issue: null,
  mix_version: null,
  format_extension: null,
  audio_family: null,
  bitrate_kbps: null,
  sample_rate_hz: null,
  bits_per_sample: null,
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

  it('detects high peak above threshold', () => {
    expect(
      loudnessStatus(
        { ...baseTrack, integrated_lufs: -12, true_peak_db: 4.0 },
        { lufs: -18, peak: 3.0 },
      ),
    ).toBe('clipped')
  })

  it('passes typical mp3 inter-sample peak', () => {
    expect(
      loudnessStatus(
        { ...baseTrack, integrated_lufs: -8.6, true_peak_db: 1.5 },
        { lufs: -18, peak: 3.0 },
      ),
    ).toBe('ok')
  })

  it('formats summary with LUFS and peak', () => {
    expect(
      formatLoudnessSummary({ ...baseTrack, integrated_lufs: -14.2, true_peak_db: -1.1 }),
    ).toBe('-14.2 LUFS · peak -1.1 dBTP')
  })
})
