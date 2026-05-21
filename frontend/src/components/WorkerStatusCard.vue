<template>
  <v-card>
    <v-card-title class="d-flex align-center ga-2 flex-wrap">
      Worker
      <v-chip
        size="small"
        :color="chipColor"
      >
        {{ workerLabel }}
      </v-chip>
      <v-chip
        v-if="wsConnected"
        size="small"
        color="success"
        variant="outlined"
      >
        Live
      </v-chip>
      <v-chip
        v-else
        size="small"
        color="warning"
        variant="outlined"
      >
        Reconnecting…
      </v-chip>
    </v-card-title>
    <v-card-text>
      <v-alert
        v-if="queueStalled"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        <p class="mb-2">
          <strong>{{ pendingJobs }} job(s) waiting</strong> but none are running — the worker may
          have stopped or jobs are stuck in <code>running</code>.
        </p>
        <v-btn
          size="small"
          variant="outlined"
          :loading="unsticking"
          @click="onUnstick"
        >
          Retry stalled jobs
        </v-btn>
      </v-alert>

      <v-alert
        v-else-if="queueBacklogged && !workerActive"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        <strong>{{ pendingJobs }} jobs queued</strong> — the worker is between steps (not idle).
        It processes <strong>one job at a time</strong>; analyze can take minutes per file on a Pi.
      </v-alert>

      <v-alert
        v-if="failedJobs > 0"
        type="error"
        variant="tonal"
        density="compact"
        class="mb-3"
      >
        <p class="mb-2">
          <strong>{{ failedJobs }} failed jobs</strong> in the database — check Recent jobs for
          errors, then clear history once you have fixed the issue.
        </p>
        <v-btn
          size="small"
          variant="outlined"
          :loading="clearingFailedJobs"
          @click="onClearFailedJobs"
        >
          Clear failed jobs
        </v-btn>
      </v-alert>

      <p
        v-if="lastEvent"
        class="text-body-2 mb-0"
      >
        {{ lastEvent.message }}
      </p>
      <p
        v-else
        class="text-body-2 text-medium-emphasis mb-0"
      >
        Waiting for activity…
      </p>
      <p
        v-if="lastEvent"
        class="text-caption text-medium-emphasis mt-1 mb-0"
      >
        {{ formatTime(lastEvent.at) }}
      </p>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { clearFailedJobs, unstickQueue } from '@/services/queueService'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'
import type { PipelineEvent } from '@/types/pipeline'

const props = defineProps<{
  workerActive: boolean
  queueStalled: boolean
  queueBacklogged: boolean
  pendingJobs: number
  failedJobs: number
  wsConnected: boolean
  lastEvent: PipelineEvent | null
}>()

const pipeline = usePipelineStore()
const snackbar = useSnackbarStore()
const unsticking = ref(false)
const clearingFailedJobs = ref(false)

const chipColor = computed(() => {
  if (props.workerActive) {
    return 'info'
  }
  if (props.queueStalled) {
    return 'warning'
  }
  if (props.queueBacklogged) {
    return 'primary'
  }
  return 'default'
})

const workerLabel = computed(() => {
  if (props.workerActive) {
    return 'Processing'
  }
  if (props.queueStalled) {
    return 'Stalled'
  }
  if (props.queueBacklogged) {
    return 'Backlogged'
  }
  return 'Idle'
})

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

async function onClearFailedJobs(): Promise<void> {
  clearingFailedJobs.value = true
  try {
    const result = await clearFailedJobs()
    snackbar.show(result.message, { color: 'success' })
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Could not clear failed jobs', {
      color: 'error',
    })
  } finally {
    clearingFailedJobs.value = false
  }
}

async function onUnstick(): Promise<void> {
  unsticking.value = true
  try {
    const result = await unstickQueue()
    snackbar.show(
      result.enqueued > 0
        ? `Reset ${result.enqueued} interrupted job(s) to pending`
        : 'No interrupted jobs — check that the worker container is running',
      { color: result.enqueued > 0 ? 'success' : 'info' },
    )
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Could not unstick queue', {
      color: 'error',
    })
  } finally {
    unsticking.value = false
  }
}
</script>
