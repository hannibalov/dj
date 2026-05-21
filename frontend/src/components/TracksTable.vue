<template>
  <v-card>
    <v-card-title class="d-flex align-center flex-wrap ga-2">
      <span>Tracks</span>
      <span
        v-if="totalTracks > tracks.length"
        class="text-caption text-medium-emphasis"
      >
        Showing {{ tracks.length }} of {{ totalTracks }} (newest first)
      </span>
      <v-spacer />
      <v-select
        v-model="statusFilterModel"
        :items="statusFilterItems"
        label="Status"
        density="compact"
        hide-details
        clearable
        style="max-width: 200px"
      />
    </v-card-title>
    <v-card-text>
      <v-data-table
        :headers="headers"
        :items="filteredTracks"
        :loading="loading"
        item-key="id"
        density="compact"
        :items-per-page="10"
        no-data-text="No tracks yet"
      >
        <template #[`item.filename`]="{ item }">
          {{ basename(item.source_path) }}
        </template>
        <template #[`item.artist`]="{ item }">
          {{ item.artist ?? '—' }}
        </template>
        <template #[`item.title`]="{ item }">
          <span>{{ item.title ?? '—' }}</span>
          <v-chip
            v-if="item.needs_metadata_review"
            size="x-small"
            color="warning"
            class="ml-1"
          >
            Metadata review
          </v-chip>
        </template>
        <template #[`item.status`]="{ item }">
          <v-chip
            size="small"
            :color="trackStatusColor(item.status)"
          >
            {{ trackStatusLabel(item.status) }}
          </v-chip>
        </template>
        <template #[`item.bpm`]="{ item }">
          {{ item.bpm != null ? item.bpm.toFixed(1) : '—' }}
        </template>
        <template #[`item.key`]="{ item }">
          <span v-if="item.musical_key && item.scale">
            {{ item.musical_key }} {{ item.scale }}
            <span
              v-if="item.camelot"
              class="text-medium-emphasis"
            >({{ item.camelot }})</span>
          </span>
          <span v-else>—</span>
        </template>
        <template #[`item.energy`]="{ item }">
          {{ item.energy ?? '—' }}
        </template>
        <template #[`item.loudness`]="{ item }">
          <div class="loudness-cell">
            <v-chip
              v-if="loudnessStatus(item) !== 'unknown'"
              size="x-small"
              :color="loudnessStatusColor(loudnessStatus(item))"
              class="mb-1"
            >
              {{ loudnessStatusLabel(loudnessStatus(item)) }}
            </v-chip>
            <v-chip
              v-else
              size="x-small"
              variant="outlined"
              class="mb-1"
            >
              Not analyzed
            </v-chip>
            <div class="text-caption text-medium-emphasis">
              <template v-if="loudnessStatus(item) !== 'unknown'">
                {{ formatLoudnessSummary(item) }}
              </template>
              <template v-else>
                Use Analyze backlog to measure
              </template>
            </div>
          </div>
        </template>
        <template #[`item.final_path`]="{ item }">
          <span class="text-caption">{{ item.final_path ? basename(item.final_path) : '—' }}</span>
        </template>
        <template #[`item.actions`]="{ item }">
          <div class="d-flex flex-wrap ga-1">
            <v-btn
              v-if="item.status === 'review'"
              size="x-small"
              color="success"
              variant="tonal"
              :loading="actionLoadingId === item.id && actionKind === 'confirm'"
              :disabled="actionLoadingId != null && actionLoadingId !== item.id"
              @click="onConfirmReview(item.id)"
            >
              Approve
            </v-btn>
            <v-btn
              v-if="item.status === 'failed'"
              size="x-small"
              color="error"
              variant="tonal"
              :loading="actionLoadingId === item.id && actionKind === 'delete'"
              :disabled="actionLoadingId != null && actionLoadingId !== item.id"
              @click="onDelete(item.id)"
            >
              Delete
            </v-btn>
            <v-btn
              size="x-small"
              variant="text"
              :loading="actionLoadingId === item.id && actionKind === 'reset'"
              :disabled="actionLoadingId != null && actionLoadingId !== item.id"
              @click="onReset(item.id)"
            >
              Reset
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { confirmTrackReview, deleteFailedTrack, resetTrack } from '@/services/trackService'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'
import type { Track, TrackStatus } from '@/types/track'
import { basename, trackStatusColor, trackStatusLabel } from '@/utils/labels'
import {
  formatLoudnessSummary,
  loudnessStatus,
  loudnessStatusColor,
  loudnessStatusLabel,
} from '@/utils/loudness'

const props = defineProps<{
  tracks: Track[]
  totalTracks: number
  loading: boolean
  statusFilter?: TrackStatus | null
}>()

const emit = defineEmits<{
  'update:statusFilter': [value: TrackStatus | null]
}>()

const pipeline = usePipelineStore()
const snackbar = useSnackbarStore()

const actionLoadingId = ref<number | null>(null)
const actionKind = ref<'reset' | 'confirm' | 'delete' | null>(null)

const statusFilterModel = computed({
  get: () => props.statusFilter ?? null,
  set: (value: TrackStatus | null) => emit('update:statusFilter', value),
})

const statusFilterItems = [
  { title: 'Queued', value: 'queued' },
  { title: 'Ingesting', value: 'processing' },
  { title: 'In pipeline', value: 'ingested' },
  { title: 'Ready', value: 'ready' },
  { title: 'Needs review', value: 'review' },
  { title: 'Failed', value: 'failed' },
]

const filteredTracks = computed(() => {
  if (!statusFilterModel.value) {
    return props.tracks
  }
  return props.tracks.filter((t) => t.status === statusFilterModel.value)
})

const headers = [
  { title: 'File', key: 'filename' },
  { title: 'Artist', key: 'artist' },
  { title: 'Title', key: 'title' },
  { title: 'Status', key: 'status' },
  { title: 'BPM', key: 'bpm' },
  { title: 'Key', key: 'key' },
  { title: 'Energy', key: 'energy' },
  { title: 'Loudness', key: 'loudness', sortable: false, width: '200px' },
  { title: 'Library copy', key: 'final_path' },
  { title: 'Actions', key: 'actions', sortable: false, width: '200px' },
]

async function onDelete(trackId: number): Promise<void> {
  actionLoadingId.value = trackId
  actionKind.value = 'delete'
  try {
    const result = await deleteFailedTrack(trackId)
    snackbar.show(result.message, { color: 'success' })
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Delete failed', { color: 'error' })
  } finally {
    actionLoadingId.value = null
    actionKind.value = null
  }
}

async function onReset(trackId: number): Promise<void> {
  actionLoadingId.value = trackId
  actionKind.value = 'reset'
  try {
    const result = await resetTrack(trackId)
    snackbar.show(result.message ?? 'Pipeline reset', { color: 'success' })
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Reset failed', { color: 'error' })
  } finally {
    actionLoadingId.value = null
    actionKind.value = null
  }
}

async function onConfirmReview(trackId: number): Promise<void> {
  actionLoadingId.value = trackId
  actionKind.value = 'confirm'
  try {
    const result = await confirmTrackReview(trackId)
    snackbar.show(result.message ?? 'Moved to ready', { color: 'success' })
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Approve failed', { color: 'error' })
  } finally {
    actionLoadingId.value = null
    actionKind.value = null
  }
}
</script>

<style scoped>
.loudness-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 140px;
}
</style>
