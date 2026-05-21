<template>
  <div class="dashboard-page">
    <DashboardActions
      :loading="pipeline.loading"
      @rescan="pipeline.rescan()"
      @analyze-backlog="pipeline.runAnalyzeBacklog()"
      @reanalyze-all="pipeline.runReanalyzeAll()"
    />

    <v-row class="mb-4">
      <v-col cols="12">
        <QueueStatsCard
          :tracks="pipeline.tracks"
          :track-summary="pipeline.trackSummary"
          :queue="pipeline.queue"
          :active-filter="trackStatusFilter"
          :loading="pipeline.loading && !pipeline.snapshot"
          @filter="trackStatusFilter = $event"
        />
      </v-col>
      <v-col cols="12">
        <WorkerStatusCard
          :worker-active="pipeline.workerActive"
          :queue-stalled="pipeline.queueStalled"
          :queue-backlogged="pipeline.queueBacklogged"
          :pending-jobs="pipeline.queue?.pending ?? 0"
          :failed-jobs="pipeline.queue?.failed ?? 0"
          :ws-connected="wsConnected"
          :last-event="pipeline.lastEvent"
        />
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12">
        <DuplicateGroupsCard ref="duplicateGroupsRef" />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <TracksTable
          v-model:status-filter="trackStatusFilter"
          :tracks="pipeline.tracks"
          :total-tracks="pipeline.trackSummary?.total ?? pipeline.tracks.length"
          :loading="pipeline.loading && !pipeline.snapshot"
        />
      </v-col>
      <v-col cols="12">
        <JobsTable
          :jobs="pipeline.queue?.jobs ?? []"
          :loading="pipeline.loading && !pipeline.snapshot"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { TrackStatus } from '@/types/track'

import DashboardActions from '@/components/DashboardActions.vue'
import DuplicateGroupsCard from '@/components/DuplicateGroupsCard.vue'
import JobsTable from '@/components/JobsTable.vue'
import QueueStatsCard from '@/components/QueueStatsCard.vue'
import TracksTable from '@/components/TracksTable.vue'
import WorkerStatusCard from '@/components/WorkerStatusCard.vue'
import { usePipelineWebSocket } from '@/composables/usePipelineWebSocket'
import { usePipelineStore } from '@/stores/pipelineStore'

const pipeline = usePipelineStore()
const trackStatusFilter = ref<TrackStatus | null>(null)
const wsConnected = ref(false)
const duplicateGroupsRef = ref<{ load: () => Promise<void> } | null>(null)

usePipelineWebSocket(
  (data) => {
    pipeline.applySnapshot(data)
    void duplicateGroupsRef.value?.load()
  },
  (connected) => {
    wsConnected.value = connected
  },
)

onMounted(() => {
  void pipeline.load()
})

</script>
