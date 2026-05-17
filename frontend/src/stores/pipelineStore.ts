import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchPipelineStatus } from '@/services/pipelineService'
import { analyzeBacklog, rescanQueue } from '@/services/queueService'
import type { PipelineSnapshot } from '@/types/pipeline'

import { useSnackbarStore } from './snackbarStore'

export const usePipelineStore = defineStore('pipeline', () => {
  const snapshot = ref<PipelineSnapshot | null>(null)
  const loading = ref(false)
  const wsConnected = ref(false)

  const snackbar = useSnackbarStore()

  const queue = computed(() => snapshot.value?.queue ?? null)
  const tracks = computed(() => snapshot.value?.tracks ?? [])
  const workerActive = computed(() => snapshot.value?.worker_active ?? false)
  const lastEvent = computed(() => snapshot.value?.last_event ?? null)

  function applySnapshot(data: PipelineSnapshot): void {
    snapshot.value = data
  }

  async function load(): Promise<void> {
    loading.value = true
    try {
      snapshot.value = await fetchPipelineStatus()
    } catch (e) {
      snackbar.show(
        e instanceof Error ? e.message : 'Failed to load pipeline status',
        { color: 'error' },
      )
    } finally {
      loading.value = false
    }
  }

  async function rescan(): Promise<void> {
    loading.value = true
    try {
      const result = await rescanQueue()
      snackbar.show(`Rescan: enqueued ${result.enqueued}, skipped ${result.skipped}`, {
        color: 'success',
      })
    } catch (e) {
      snackbar.show(e instanceof Error ? e.message : 'Rescan failed', { color: 'error' })
    } finally {
      loading.value = false
    }
  }

  async function runAnalyzeBacklog(): Promise<void> {
    loading.value = true
    try {
      const result = await analyzeBacklog()
      snackbar.show(`Analyze backlog: enqueued ${result.enqueued}, skipped ${result.skipped}`, {
        color: 'success',
      })
    } catch (e) {
      snackbar.show(e instanceof Error ? e.message : 'Analyze backlog failed', {
        color: 'error',
      })
    } finally {
      loading.value = false
    }
  }

  return {
    snapshot,
    loading,
    wsConnected,
    queue,
    tracks,
    workerActive,
    lastEvent,
    load,
    rescan,
    runAnalyzeBacklog,
    applySnapshot,
  }
})
