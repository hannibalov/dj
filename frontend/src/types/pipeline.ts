import type { QueueSummary } from './queue'
import type { Track } from './track'

export interface TrackStatusSummary {
  total: number
  by_status: Record<string, number>
}

export interface PipelineEvent {
  message: string
  at: string
}

export interface PipelineSnapshot {
  queue: QueueSummary
  tracks: Track[]
  track_summary: TrackStatusSummary
  worker_active: boolean
  queue_stalled: boolean
  queue_backlogged: boolean
  last_event: PipelineEvent | null
}

export interface PipelineWsMessage {
  type: 'snapshot'
  message?: string | null
  data: PipelineSnapshot
}
