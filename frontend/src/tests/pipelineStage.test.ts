import { describe, expect, it } from 'vitest'

import {
  PIPELINE_STAGE_ORDER,
  isPipelineStage,
  pipelineStageColor,
  pipelineStageLabel,
  type PipelineStage,
} from '@/utils/pipelineStage'

const ALL_STAGES: PipelineStage[] = [
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
  'archived',
]

describe('pipelineStage', () => {
  it('defines worker-order stages for dashboard chips', () => {
    expect(PIPELINE_STAGE_ORDER).toEqual([
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
    ])
    expect(PIPELINE_STAGE_ORDER).not.toContain('archived')
  })

  it('labels stages as the next step the worker will run', () => {
    expect(pipelineStageLabel('awaiting_analyze')).toBe('Awaiting analyze')
    expect(pipelineStageLabel('awaiting_fingerprint')).toBe('Analyzed')
    expect(pipelineStageLabel('awaiting_tag')).toBe('Awaiting tag')
    expect(pipelineStageLabel('awaiting_route')).toBe('Awaiting route')
    for (const stage of ALL_STAGES) {
      expect(pipelineStageLabel(stage).length).toBeGreaterThan(0)
    }
  })

  it('isPipelineStage accepts known stages only', () => {
    for (const stage of ALL_STAGES) {
      expect(isPipelineStage(stage)).toBe(true)
    }
    expect(isPipelineStage('in pipeline')).toBe(false)
    expect(isPipelineStage('fingerprinted')).toBe(false)
  })

  it('uses distinct colors for in-progress vs terminal stages', () => {
    expect(pipelineStageColor('awaiting_fingerprint')).toBe('primary')
    expect(pipelineStageColor('awaiting_tag')).toBe('primary')
    expect(pipelineStageColor('ready')).toBe('success')
    expect(pipelineStageColor('failed')).toBe('error')
    expect(pipelineStageColor('archived')).toBe('default')
  })
})
