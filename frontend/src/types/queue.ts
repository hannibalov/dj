export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type JobType = 'ingest' | 'analyze' | 'fingerprint' | 'tag' | 'route'

export interface Job {
  id: number
  job_type: JobType
  status: JobStatus
  source_path: string
  attempts: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface QueueSummary {
  pending: number
  running: number
  failed: number
  completed: number
  jobs: Job[]
}

export interface RescanResult {
  status: string
  enqueued: number
  skipped: number
}

/** Same shape as rescan — used for analyze-backlog. */
export type AnalyzeBacklogResult = RescanResult
