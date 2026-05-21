import type { JobStatus, JobType } from '@/types/queue'
import type { TrackStatus } from '@/types/track'

const TRACK_STATUS_LABELS: Record<TrackStatus, string> = {
  queued: 'Queued',
  processing: 'Ingesting…',
  ingested: 'In pipeline',
  ready: 'Ready',
  review: 'Needs review',
  duplicate: 'Duplicate',
  archived: 'Archived',
  failed: 'Failed',
}

const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export function trackStatusLabel(status: TrackStatus): string {
  return TRACK_STATUS_LABELS[status] ?? status
}

export function jobStatusLabel(status: JobStatus): string {
  return JOB_STATUS_LABELS[status] ?? status
}

export function jobTypeLabel(type: JobType): string {
  return type.charAt(0).toUpperCase() + type.slice(1)
}

export function basename(path: string): string {
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1] ?? path
}

export function trackStatusColor(status: TrackStatus): string {
  switch (status) {
    case 'processing':
      return 'info'
    case 'ingested':
      return 'success'
    case 'ready':
      return 'success'
    case 'review':
      return 'warning'
    case 'failed':
      return 'error'
    case 'queued':
      return 'warning'
    default:
      return 'default'
  }
}

export function jobStatusColor(status: JobStatus): string {
  switch (status) {
    case 'running':
      return 'info'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'pending':
      return 'warning'
    default:
      return 'default'
  }
}
