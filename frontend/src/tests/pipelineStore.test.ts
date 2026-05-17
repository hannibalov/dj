import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as queueService from '@/services/queueService'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'

describe('pipelineStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('runAnalyzeBacklog shows success snackbar', async () => {
    vi.spyOn(queueService, 'analyzeBacklog').mockResolvedValue({
      status: 'ok',
      enqueued: 2,
      skipped: 1,
    })

    const pipeline = usePipelineStore()
    const snackbar = useSnackbarStore()
    await pipeline.runAnalyzeBacklog()

    expect(snackbar.message).toBe('Analyze backlog: enqueued 2, skipped 1')
    expect(snackbar.color).toBe('success')
    expect(snackbar.visible).toBe(true)
  })
})
