/** Display pipeline step — terminal statuses plus in-progress sub-stages for `ingested`. */
export type PipelineStage =
  | 'queued'
  | 'ingesting'
  | 'awaiting_analyze'
  | 'awaiting_fingerprint'
  | 'awaiting_tag'
  | 'awaiting_route'
  | 'ready'
  | 'review'
  | 'duplicate'
  | 'failed'
  | 'archived'

/** Dashboard chips in worker order (archived omitted from main row). */
export const PIPELINE_STAGE_ORDER: PipelineStage[] = [
  'queued',
  'ingesting',
  'awaiting_analyze',
  'awaiting_fingerprint',
  'awaiting_tag',
  'awaiting_route',
  'ready',
  'review',
  'duplicate',
  'failed',
]

const STAGE_LABELS: Record<PipelineStage, string> = {
  queued: 'Queued',
  ingesting: 'Ingesting',
  awaiting_analyze: 'Awaiting analyze',
  awaiting_fingerprint: 'Analyzed',
  awaiting_tag: 'Awaiting tag',
  awaiting_route: 'Awaiting route',
  ready: 'Ready',
  review: 'Needs review',
  duplicate: 'Duplicate',
  failed: 'Failed',
  archived: 'Archived',
}

const STAGE_COLORS: Record<PipelineStage, string> = {
  queued: 'warning',
  ingesting: 'info',
  awaiting_analyze: 'primary',
  awaiting_fingerprint: 'primary',
  awaiting_tag: 'primary',
  awaiting_route: 'primary',
  ready: 'success',
  review: 'warning',
  duplicate: 'secondary',
  failed: 'error',
  archived: 'default',
}

export function pipelineStageLabel(stage: PipelineStage): string {
  return STAGE_LABELS[stage] ?? stage
}

export function pipelineStageColor(stage: PipelineStage): string {
  return STAGE_COLORS[stage] ?? 'default'
}

export function isPipelineStage(value: string): value is PipelineStage {
  return value in STAGE_LABELS
}
