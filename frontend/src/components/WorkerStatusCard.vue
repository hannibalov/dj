<template>
  <v-card>
    <v-card-title class="d-flex align-center ga-2">
      Worker
      <v-chip
        size="small"
        :color="workerActive ? 'info' : 'default'"
      >
        {{ workerActive ? 'Processing' : 'Idle' }}
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
import type { PipelineEvent } from '@/types/pipeline'

defineProps<{
  workerActive: boolean
  wsConnected: boolean
  lastEvent: PipelineEvent | null
}>()

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}
</script>
