import { describe, expect, it } from 'vitest'

import type { Track } from '@/types/track'
import {
  activeCountFromSummary,
  buildTrackStageCounts,
  buildTrackStageCountsFromSummary,
  countTracksByStatus,
} from '@/utils/pipelineCounts'

function track(status: Track['status'], id: number): Track {
  return {
    id,
    status,
    source_path: `/watch/${id}.mp3`,
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
  }
}

describe('pipelineCounts', () => {
  it('counts tracks by status', () => {
    const tracks = [track('queued', 1), track('queued', 2), track('failed', 3)]
    expect(countTracksByStatus(tracks).get('queued')).toBe(2)
    expect(countTracksByStatus(tracks).get('failed')).toBe(1)
  })

  it('builds ordered stage counts with zeros', () => {
    const stages = buildTrackStageCounts([track('ingested', 1)])
    expect(stages.find((s) => s.status === 'ingested')?.count).toBe(1)
    expect(stages.find((s) => s.status === 'queued')?.count).toBe(0)
  })

  it('builds stage counts from server summary', () => {
    const stages = buildTrackStageCountsFromSummary({
      total: 150,
      by_status: { ingested: 120, ready: 30 },
    })
    expect(stages.find((s) => s.status === 'ingested')?.count).toBe(120)
    expect(
      activeCountFromSummary({
        total: 150,
        by_status: { ingested: 120, ready: 25, archived: 5 },
      }),
    ).toBe(145)
  })
})
