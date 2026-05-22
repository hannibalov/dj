import type { TrackStatusSummary } from '@/types/pipeline'
import type { QueueSummary } from '@/types/queue'
import type { Track } from '@/types/track'
import {
  PIPELINE_STAGE_ORDER,
  type PipelineStage,
  pipelineStageColor,
  pipelineStageLabel,
} from '@/utils/pipelineStage'

export type { TrackStatusSummary }

export interface TrackStageCount {
  status: PipelineStage
  label: string
  count: number
  color: string
}

export function countTracksByPipelineStage(tracks: Track[]): Map<PipelineStage, number> {
  const counts = new Map<PipelineStage, number>()
  for (const track of tracks) {
    const stage = track.pipeline_stage
    counts.set(stage, (counts.get(stage) ?? 0) + 1)
  }
  return counts
}

/** @deprecated use countTracksByPipelineStage */
export function countTracksByStatus(tracks: Track[]): Map<string, number> {
  const counts = new Map<string, number>()
  for (const track of tracks) {
    counts.set(track.status, (counts.get(track.status) ?? 0) + 1)
  }
  return counts
}

export function buildTrackStageCounts(tracks: Track[]): TrackStageCount[] {
  return buildTrackStageCountsFromMap(countTracksByPipelineStage(tracks))
}

export function buildTrackStageCountsFromSummary(
  summary: TrackStatusSummary | null | undefined,
): TrackStageCount[] {
  if (!summary?.by_pipeline_stage) {
    return buildTrackStageCounts([])
  }
  const byStage = new Map<PipelineStage, number>()
  for (const [stage, count] of Object.entries(summary.by_pipeline_stage)) {
    byStage.set(stage as PipelineStage, count)
  }
  return buildTrackStageCountsFromMap(byStage)
}

function buildTrackStageCountsFromMap(byStage: Map<PipelineStage, number>): TrackStageCount[] {
  return PIPELINE_STAGE_ORDER.map((status) => ({
    status,
    label: pipelineStageLabel(status),
    count: byStage.get(status) ?? 0,
    color: pipelineStageColor(status),
  }))
}

export function activeCountFromSummary(summary: TrackStatusSummary | null | undefined): number {
  if (!summary) {
    return 0
  }
  const stages = summary.by_pipeline_stage
  if (stages) {
    return Object.entries(stages).reduce((sum, [stage, count]) => {
      return stage === 'archived' ? sum : sum + count
    }, 0)
  }
  return Object.entries(summary.by_status).reduce((sum, [status, count]) => {
    return status === 'archived' ? sum : sum + count
  }, 0)
}

export function archivedTrackCount(summary: TrackStatusSummary | null | undefined): number {
  return summary?.by_pipeline_stage?.archived ?? summary?.by_status?.archived ?? 0
}

/** Tracks that are still part of the active pipeline (not archived). */
export function activePipelineTracks(tracks: Track[]): Track[] {
  return tracks.filter((t) => t.pipeline_stage !== 'archived')
}

export interface JobQueueSummary {
  pending: number
  running: number
  failed: number
}

export function jobQueueSummary(queue: QueueSummary | null | undefined): JobQueueSummary {
  return {
    pending: queue?.pending ?? 0,
    running: queue?.running ?? 0,
    failed: queue?.failed ?? 0,
  }
}
