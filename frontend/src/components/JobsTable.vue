<template>
  <v-card>
    <v-card-title class="d-flex flex-wrap align-center ga-2">
      <span>Recent jobs</span>
      <span class="text-caption text-medium-emphasis">(last 200)</span>
    </v-card-title>
    <v-card-text>
      <v-data-table
        :headers="headers"
        :items="jobs"
        :loading="loading"
        item-key="id"
        density="compact"
        :items-per-page="25"
        no-data-text="No jobs yet"
      >
        <template #[`item.filename`]="{ item }">
          {{ basename(item.source_path) }}
        </template>
        <template #[`item.job_type`]="{ item }">
          {{ jobTypeLabel(item.job_type) }}
        </template>
        <template #[`item.status`]="{ item }">
          <v-chip
            size="small"
            :color="jobStatusColor(item.status)"
          >
            {{ jobStatusLabel(item.status) }}
          </v-chip>
        </template>
        <template #[`item.error_message`]="{ item }">
          <span class="text-caption text-error">{{ item.error_message ?? '—' }}</span>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { Job } from '@/types/queue'
import { basename, jobStatusColor, jobStatusLabel, jobTypeLabel } from '@/utils/labels'

defineProps<{
  jobs: Job[]
  loading: boolean
}>()

const headers = [
  { title: 'File', key: 'filename' },
  { title: 'Type', key: 'job_type' },
  { title: 'Status', key: 'status' },
  { title: 'Error', key: 'error_message' },
]
</script>
