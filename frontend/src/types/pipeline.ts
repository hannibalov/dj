import type { QueueSummary } from './queue'
import type { Track } from './track'

export interface PipelineEvent {
  message: string
  at: string
}

export interface PipelineSnapshot {
  queue: QueueSummary
  tracks: Track[]
  worker_active: boolean
  last_event: PipelineEvent | null
}

export interface PipelineWsMessage {
  type: 'snapshot'
  message?: string | null
  data: PipelineSnapshot
}
