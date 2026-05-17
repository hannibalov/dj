import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchQueue, rescanQueue } from '@/services/queueService'
import type { QueueSummary } from '@/types/queue'

export const useQueueStore = defineStore('queue', () => {
  const summary = ref<QueueSummary | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      summary.value = await fetchQueue()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load queue'
    } finally {
      loading.value = false
    }
  }

  async function rescan(): Promise<void> {
    await rescanQueue()
    await load()
  }

  return { summary, loading, error, load, rescan }
})
