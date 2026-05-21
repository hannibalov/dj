import type { TrackStatusSummary } from '@/types/pipeline'
import type { QueueSummary } from '@/types/queue'
import type { Track, TrackStatus } from '@/types/track'

export type { TrackStatusSummary }

export interface TrackStageCount {
  status: TrackStatus
  label: string
  count: number
  color: string
}

/** Pipeline stages in processing order (excludes archived). */
export const TRACK_PIPELINE_STAGES: TrackStageCount['status'][] = [
  'queued',
  'processing',
  'ingested',
  'ready',
  'review',
  'duplicate',
  'failed',
]

const STAGE_LABELS: Record<TrackStatus, string> = {
  queued: 'Queued',
  processing: 'Ingesting',
  ingested: 'In pipeline',
  ready: 'Ready',
  review: 'Review',
  duplicate: 'Duplicate',
  archived: 'Archived',
  failed: 'Failed',
}

const STAGE_COLORS: Record<TrackStatus, string> = {
  queued: 'warning',
  processing: 'info',
  ingested: 'primary',
  ready: 'success',
  review: 'warning',
  duplicate: 'secondary',
  archived: 'default',
  failed: 'error',
}

export function countTracksByStatus(tracks: Track[]): Map<TrackStatus, number> {
  const counts = new Map<TrackStatus, number>()
  for (const track of tracks) {
    counts.set(track.status, (counts.get(track.status) ?? 0) + 1)
  }
  return counts
}

export function buildTrackStageCounts(tracks: Track[]): TrackStageCount[] {
  const byStatus = countTracksByStatus(tracks)
  return buildTrackStageCountsFromMap(byStatus)
}

export function buildTrackStageCountsFromSummary(
  summary: TrackStatusSummary | null | undefined,
): TrackStageCount[] {
  if (!summary) {
    return buildTrackStageCounts([])
  }
  const byStatus = new Map<TrackStatus, number>()
  for (const [status, count] of Object.entries(summary.by_status)) {
    byStatus.set(status as TrackStatus, count)
  }
  return buildTrackStageCountsFromMap(byStatus)
}

function buildTrackStageCountsFromMap(byStatus: Map<TrackStatus, number>): TrackStageCount[] {
  return TRACK_PIPELINE_STAGES.map((status) => ({
    status,
    label: STAGE_LABELS[status],
    count: byStatus.get(status) ?? 0,
    color: STAGE_COLORS[status],
  }))
}

export function activeCountFromSummary(summary: TrackStatusSummary | null | undefined): number {
  if (!summary) {
    return 0
  }
  return Object.entries(summary.by_status).reduce((sum, [status, count]) => {
    return status === 'archived' ? sum : sum + count
  }, 0)
}

export function archivedTrackCount(tracks: Track[]): number {
  return tracks.filter((t) => t.status === 'archived').length
}

/** Tracks that are still part of the active pipeline (not archived). */
export function activePipelineTracks(tracks: Track[]): Track[] {
  return tracks.filter((t) => t.status !== 'archived')
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
