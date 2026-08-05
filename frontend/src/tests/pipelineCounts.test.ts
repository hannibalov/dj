import { describe, expect, it } from 'vitest'

import type { Track } from '@/types/track'
import {
  activeCountFromSummary,
  activePipelineTracks,
  archivedTrackCount,
  buildTrackStageCounts,
  buildTrackStageCountsFromSummary,
  countTracksByPipelineStage,
} from '@/utils/pipelineCounts'
import { PIPELINE_STAGE_ORDER, type PipelineStage } from '@/utils/pipelineStage'

function track(stage: PipelineStage, id: number): Track {
  const status =
    stage === 'ingesting'
      ? 'processing'
      : stage === 'awaiting_analyze' ||
          stage === 'awaiting_fingerprint' ||
          stage === 'awaiting_tag' ||
          stage === 'awaiting_route'
        ? 'ingested'
        : stage

  return {
    id,
    status,
    pipeline_stage: stage,
    source_path: `/watch/${id}.mp3`,
    processing_path: null,
    final_path: null,
    artist: null,
    title: null,
    album: null,
    genre: null,
    subgenre: null,
    metadata_issue: null,
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
  }
}

describe('pipelineCounts', () => {
  it('counts tracks by pipeline_stage from API field', () => {
    const tracks = [
      track('awaiting_analyze', 1),
      track('awaiting_fingerprint', 2),
      track('failed', 3),
    ]
    expect(countTracksByPipelineStage(tracks).get('awaiting_analyze')).toBe(1)
    expect(countTracksByPipelineStage(tracks).get('awaiting_fingerprint')).toBe(1)
    expect(countTracksByPipelineStage(tracks).get('failed')).toBe(1)
  })

  it('returns dashboard stages in worker order with labels and colors', () => {
    const stages = buildTrackStageCounts([track('awaiting_tag', 1)])

    expect(stages.map((s) => s.status)).toEqual(PIPELINE_STAGE_ORDER)
    expect(stages.find((s) => s.status === 'awaiting_tag')).toMatchObject({
      count: 1,
      label: 'Awaiting tag',
      color: 'primary',
    })
    expect(stages.find((s) => s.status === 'queued')?.count).toBe(0)
  })

  it('builds stage counts from server by_pipeline_stage', () => {
    const stages = buildTrackStageCountsFromSummary({
      total: 150,
      by_status: { ingested: 120, ready: 30 },
      by_pipeline_stage: {
        awaiting_fingerprint: 40,
        awaiting_tag: 50,
        awaiting_route: 30,
        ready: 30,
      },
    })

    expect(stages.find((s) => s.status === 'awaiting_fingerprint')?.count).toBe(40)
    expect(stages.find((s) => s.status === 'awaiting_tag')?.count).toBe(50)
    expect(stages.find((s) => s.status === 'awaiting_route')?.count).toBe(30)
  })

  it('returns zero counts when summary is missing pipeline stages', () => {
    const stages = buildTrackStageCountsFromSummary(null)
    expect(stages.every((s) => s.count === 0)).toBe(true)
    expect(stages).toHaveLength(PIPELINE_STAGE_ORDER.length)
  })

  it('activeCountFromSummary excludes archived using by_pipeline_stage', () => {
    expect(
      activeCountFromSummary({
        total: 150,
        by_status: { ingested: 120, ready: 25, archived: 5 },
        by_pipeline_stage: { ready: 25, archived: 5, awaiting_fingerprint: 120 },
      }),
    ).toBe(145)
  })

  it('activeCountFromSummary falls back to by_status when by_pipeline_stage is missing', () => {
    const legacySummary = {
      total: 10,
      by_status: { ready: 8, archived: 2 },
    } as unknown as import('@/types/pipeline').TrackStatusSummary

    expect(activeCountFromSummary(legacySummary)).toBe(8)
  })

  it('archivedTrackCount prefers by_pipeline_stage then by_status', () => {
    expect(
      archivedTrackCount({
        total: 3,
        by_status: { archived: 1 },
        by_pipeline_stage: { archived: 2 },
      }),
    ).toBe(2)
    expect(
      archivedTrackCount({
        total: 1,
        by_status: { archived: 1 },
        by_pipeline_stage: {},
      }),
    ).toBe(1)
  })

  it('activePipelineTracks excludes archived by pipeline_stage', () => {
    const tracks = [track('ready', 1), track('archived', 2), track('awaiting_fingerprint', 3)]
    expect(activePipelineTracks(tracks).map((t) => t.id)).toEqual([1, 3])
  })
})
