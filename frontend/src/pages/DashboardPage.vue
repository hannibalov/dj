<template>
  <div class="dashboard-page">
    <DashboardActions
      :loading="pipeline.loading"
      @rescan="pipeline.rescan()"
      @analyze-backlog="pipeline.runAnalyzeBacklog()"
    />

    <v-row class="mb-4">
      <v-col
        cols="12"
        md="4"
      >
        <QueueStatsCard
          :pending="pipeline.queue?.pending ?? 0"
          :running="pipeline.queue?.running ?? 0"
          :completed="pipeline.queue?.completed ?? 0"
          :failed="pipeline.queue?.failed ?? 0"
          :loading="pipeline.loading && !pipeline.snapshot"
        />
      </v-col>
      <v-col
        cols="12"
        md="8"
      >
        <WorkerStatusCard
          :worker-active="pipeline.workerActive"
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
          :tracks="pipeline.tracks"
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

import DashboardActions from '@/components/DashboardActions.vue'
import DuplicateGroupsCard from '@/components/DuplicateGroupsCard.vue'
import JobsTable from '@/components/JobsTable.vue'
import QueueStatsCard from '@/components/QueueStatsCard.vue'
import TracksTable from '@/components/TracksTable.vue'
import WorkerStatusCard from '@/components/WorkerStatusCard.vue'
import { usePipelineWebSocket } from '@/composables/usePipelineWebSocket'
import { usePipelineStore } from '@/stores/pipelineStore'

const pipeline = usePipelineStore()
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
