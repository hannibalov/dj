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
  if (type === 'download') {
    return 'Download'
  }
  return type.charAt(0).toUpperCase() + type.slice(1)
}

export function jobSourceLabel(job: { job_type: JobType; source_path: string }): string {
  if (job.job_type === 'download') {
    const value = job.source_path
    return value.length > 56 ? `${value.slice(0, 53)}…` : value
  }
  return basename(job.source_path)
}

export function basename(path: string): string {
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1] ?? path
}

export function formatDateAdded(iso: string | null | undefined): string {
  if (!iso) {
    return '—'
  }
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return '—'
  }
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
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
