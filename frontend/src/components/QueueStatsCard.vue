<template>
  <v-card>
    <v-card-title class="d-flex flex-wrap align-center ga-2">
      <span>Pipeline</span>
      <v-chip
        size="small"
        variant="tonal"
      >
        {{ activeCount }} {{ activeCount === 1 ? 'song' : 'songs' }} total
      </v-chip>
      <v-chip
        v-if="tracksShown < activeCount"
        size="small"
        variant="outlined"
      >
        table shows {{ tracksShown }} newest
      </v-chip>
      <v-spacer />
      <v-btn
        v-if="failedCount > 0"
        size="small"
        color="error"
        variant="tonal"
        :loading="clearingFailed"
        @click="onClearAllFailed"
      >
        Clear {{ failedCount }} failed
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-skeleton-loader
        v-if="loading"
        type="chip@7"
      />
      <template v-else>
        <p class="text-caption text-medium-emphasis mb-2">
          Songs by pipeline step — click to filter the table
        </p>
        <div class="pipeline-stages d-flex flex-wrap ga-2 mb-4">
          <v-chip
            v-for="stage in stageCounts"
            :key="stage.status"
            :color="stage.count > 0 ? stage.color : undefined"
            :variant="activeFilter === stage.status ? 'flat' : 'tonal'"
            :class="{ 'pipeline-stage--empty': stage.count === 0 }"
            class="pipeline-stage"
            @click="emitFilter(stage.status)"
          >
            <span class="pipeline-stage__count">{{ stage.count }}</span>
            <span class="pipeline-stage__label">{{ stage.label }}</span>
          </v-chip>
        </div>
        <p
          v-if="archivedCount > 0"
          class="text-caption text-medium-emphasis mb-3"
        >
          {{ archivedCount }} archived
        </p>

        <v-alert
          v-if="jobSummary.pending > 0"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-3"
        >
          After <strong>Reanalyze all</strong>, most tracks show
          <strong>Awaiting analyze</strong> until the worker reaches them (one job at a time).
          Tracks move to <strong>Analyzed</strong> only after loudness/BPM analysis finishes.
        </v-alert>

        <v-divider class="mb-3" />

        <p class="text-caption text-medium-emphasis mb-2">
          Background jobs (worker queue)
        </p>
        <div class="d-flex flex-wrap align-center ga-3 text-body-2">
          <span>
            <strong>{{ jobSummary.pending }}</strong> pending
          </span>
          <span>
            <strong>{{ jobSummary.running }}</strong> running
          </span>
          <span :class="{ 'text-error': jobSummary.failed > 0 }">
            <strong>{{ jobSummary.failed }}</strong> failed jobs
          </span>
          <span class="text-medium-emphasis">
            {{ completedJobs }} completed (recent)
          </span>
          <v-btn
            v-if="jobSummary.failed > 0"
            size="x-small"
            color="error"
            variant="outlined"
            :loading="clearingFailedJobs"
            @click="onClearFailedJobs"
          >
            Clear failed jobs
          </v-btn>
        </div>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { clearFailedJobs } from '@/services/queueService'
import { deleteAllFailedTracks } from '@/services/trackService'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'
import type { TrackStatusSummary } from '@/types/pipeline'
import type { QueueSummary } from '@/types/queue'
import type { Track } from '@/types/track'
import type { PipelineStage } from '@/utils/pipelineStage'
import {
  activeCountFromSummary,
  activePipelineTracks,
  archivedTrackCount,
  buildTrackStageCountsFromSummary,
  jobQueueSummary,
} from '@/utils/pipelineCounts'

const props = defineProps<{
  tracks: Track[]
  trackSummary: TrackStatusSummary | null
  queue: QueueSummary | null | undefined
  loading: boolean
  activeFilter: PipelineStage | null
}>()

const emit = defineEmits<{
  filter: [status: PipelineStage | null]
}>()

const pipeline = usePipelineStore()
const snackbar = useSnackbarStore()
const clearingFailed = ref(false)
const clearingFailedJobs = ref(false)

const tracksShown = computed(() => activePipelineTracks(props.tracks).length)
const activeCount = computed(() => activeCountFromSummary(props.trackSummary))
const stageCounts = computed(() => buildTrackStageCountsFromSummary(props.trackSummary))
const failedCount = computed(
  () =>
    props.trackSummary?.by_pipeline_stage?.failed ??
    props.trackSummary?.by_status.failed ??
    0,
)
const archivedCount = computed(() => archivedTrackCount(props.trackSummary))
const jobSummary = computed(() => jobQueueSummary(props.queue))
const completedJobs = computed(() => props.queue?.completed ?? 0)

function emitFilter(status: PipelineStage): void {
  emit('filter', props.activeFilter === status ? null : status)
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

async function onClearAllFailed(): Promise<void> {
  clearingFailed.value = true
  try {
    const result = await deleteAllFailedTracks()
    snackbar.show(result.message, { color: 'success' })
    await pipeline.load()
    if (props.activeFilter === 'failed') {
      emit('filter', null)
    }
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Could not clear failed tracks', {
      color: 'error',
    })
  } finally {
    clearingFailed.value = false
  }
}
</script>

<style scoped>
.pipeline-stage {
  min-width: 5.5rem;
  height: auto !important;
  padding: 8px 12px !important;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.pipeline-stage--empty {
  opacity: 0.55;
}

.pipeline-stage__count {
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.2;
}

.pipeline-stage__label {
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: none;
  opacity: 0.9;
}
</style>
