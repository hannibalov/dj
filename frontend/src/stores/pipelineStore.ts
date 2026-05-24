import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchPipelineStatus } from '@/services/pipelineService'
import { analyzeBacklog, genreBackfill, reanalyzeAll, rescanQueue } from '@/services/queueService'
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
  const queueStalled = computed(() => snapshot.value?.queue_stalled ?? false)
  const queueBacklogged = computed(() => snapshot.value?.queue_backlogged ?? false)
  const trackSummary = computed(() => snapshot.value?.track_summary ?? null)
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

  async function runReanalyzeAll(): Promise<void> {
    loading.value = true
    try {
      const result = await reanalyzeAll()
      snackbar.show(
        `Reanalyze all: enqueued ${result.enqueued}, skipped ${result.skipped}. ` +
          'Runs analyze → fingerprint → tag → route (worker must be running).',
        { color: 'success' },
      )
    } catch (e) {
      snackbar.show(e instanceof Error ? e.message : 'Reanalyze all failed', {
        color: 'error',
      })
    } finally {
      loading.value = false
    }
  }

  async function runGenreBackfill(): Promise<void> {
    loading.value = true
    try {
      const result = await genreBackfill()
      snackbar.show(
        `Genre backfill: enriched ${result.enriched}, skipped ${result.skipped}. ` +
          'MusicBrainz lookups run inline (may take a while on large libraries).',
        { color: 'success' },
      )
    } catch (e) {
      snackbar.show(e instanceof Error ? e.message : 'Genre backfill failed', {
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
    queueStalled,
    queueBacklogged,
    trackSummary,
    lastEvent,
    load,
    rescan,
    runAnalyzeBacklog,
    runReanalyzeAll,
    runGenreBackfill,
    applySnapshot,
  }
})
