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
          <v-text-field
            :model-value="draftArtist(item)"
            density="compact"
            variant="plain"
            hide-details
            placeholder="Artist"
            class="metadata-field"
            :disabled="metadataSavingId === item.id"
            @update:model-value="(v) => setDraft(item, 'artist', v)"
            @blur="() => saveMetadata(item)"
            @keyup.enter="($event.target as HTMLInputElement)?.blur()"
          />
        </template>
        <template #[`item.title`]="{ item }">
          <div class="d-flex align-center flex-wrap ga-1">
            <v-text-field
              :model-value="draftTitle(item)"
              density="compact"
              variant="plain"
              hide-details
              placeholder="Title"
              class="metadata-field"
              :disabled="metadataSavingId === item.id"
              @update:model-value="(v) => setDraft(item, 'title', v)"
              @blur="() => saveMetadata(item)"
              @keyup.enter="($event.target as HTMLInputElement)?.blur()"
            />
            <v-chip
              v-if="item.needs_metadata_review"
              size="x-small"
              color="warning"
            >
              Metadata review
            </v-chip>
          </div>
        </template>
        <template #[`item.genre`]="{ item }">
          <v-text-field
            :model-value="draftGenre(item)"
            density="compact"
            variant="plain"
            hide-details
            placeholder="Genre"
            class="metadata-field"
            :disabled="metadataSavingId === item.id"
            @update:model-value="(v) => setDraft(item, 'genre', v)"
            @blur="() => saveMetadata(item)"
            @keyup.enter="($event.target as HTMLInputElement)?.blur()"
          />
        </template>
        <template #[`item.subgenre`]="{ item }">
          <v-text-field
            :model-value="draftSubgenre(item)"
            density="compact"
            variant="plain"
            hide-details
            placeholder="Subgenre"
            class="metadata-field"
            :disabled="metadataSavingId === item.id"
            @update:model-value="(v) => setDraft(item, 'subgenre', v)"
            @blur="() => saveMetadata(item)"
            @keyup.enter="($event.target as HTMLInputElement)?.blur()"
          />
        </template>
        <template #[`item.status`]="{ item }">
          <v-chip
            size="small"
            :color="pipelineStageColor(item.pipeline_stage)"
          >
            {{ pipelineStageLabel(item.pipeline_stage) }}
          </v-chip>
        </template>
        <template #[`item.bpm`]="{ item }">
          {{ item.bpm != null ? item.bpm.toFixed(1) : '—' }}
        </template>
        <template #[`item.key`]="{ item }">
          {{ formatTrackKey(item, keyNotation) ?? '—' }}
        </template>
        <template #[`item.energy`]="{ item }">
          {{ item.energy ?? '—' }}
        </template>
        <template #[`item.format`]="{ item }">
          {{ formatExtensionLabel(item.format_extension) }}
        </template>
        <template #[`item.quality`]="{ item }">
          {{ formatAudioQualityLabel(item) }}
        </template>
        <template #[`item.bitrate_kbps`]="{ item }">
          {{ formatBitrateLabel(item.bitrate_kbps, item.audio_family) }}
        </template>
        <template #[`item.loudness`]="{ item }">
          <div class="loudness-cell">
            <v-chip
              v-if="trackLoudnessStatus(item) !== 'unknown'"
              size="x-small"
              :color="loudnessStatusColor(trackLoudnessStatus(item))"
              class="mb-1"
            >
              {{ loudnessStatusLabel(trackLoudnessStatus(item)) }}
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
              <template v-if="trackLoudnessStatus(item) !== 'unknown'">
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

import {
  confirmTrackReview,
  deleteFailedTrack,
  resetTrack,
  updateTrackMetadata,
} from '@/services/trackService'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { useSnackbarStore } from '@/stores/snackbarStore'
import type { Track } from '@/types/track'
import { basename } from '@/utils/labels'
import {
  PIPELINE_STAGE_ORDER,
  pipelineStageColor,
  pipelineStageLabel,
  type PipelineStage,
} from '@/utils/pipelineStage'
import {
  formatAudioQualityLabel,
  formatBitrateLabel,
  formatExtensionLabel,
} from '@/utils/audioQuality'
import {
  formatLoudnessSummary,
  loudnessStatus,
  loudnessStatusColor,
  loudnessStatusLabel,
  type LoudnessThresholds,
} from '@/utils/loudness'
import { DEFAULT_KEY_NOTATION, formatTrackKey } from '@/utils/keyNotation'
import { createTrackTableSort } from '@/utils/trackTableSort'

const props = defineProps<{
  tracks: Track[]
  totalTracks: number
  loading: boolean
  statusFilter?: PipelineStage | null
}>()

const emit = defineEmits<{
  'update:statusFilter': [value: PipelineStage | null]
}>()

const pipeline = usePipelineStore()
const settingsStore = useSettingsStore()
const snackbar = useSnackbarStore()

const loudnessThresholds = computed<LoudnessThresholds>(() => ({
  lufs: settingsStore.settings?.review_lufs_threshold ?? -18,
  peak: settingsStore.settings?.review_true_peak_db ?? 3.0,
}))

const keyNotation = computed(
  () => settingsStore.settings?.key_notation ?? DEFAULT_KEY_NOTATION,
)

function trackLoudnessStatus(track: Track) {
  return loudnessStatus(track, loudnessThresholds.value)
}

const actionLoadingId = ref<number | null>(null)
const actionKind = ref<'reset' | 'confirm' | 'delete' | null>(null)
const metadataSavingId = ref<number | null>(null)
const metadataDrafts = ref<
  Record<number, { artist: string; title: string; genre: string; subgenre: string }>
>({})

function draftArtist(track: Track): string {
  return metadataDrafts.value[track.id]?.artist ?? track.artist ?? ''
}

function draftTitle(track: Track): string {
  return metadataDrafts.value[track.id]?.title ?? track.title ?? ''
}

function draftGenre(track: Track): string {
  return metadataDrafts.value[track.id]?.genre ?? track.genre ?? ''
}

function draftSubgenre(track: Track): string {
  return metadataDrafts.value[track.id]?.subgenre ?? track.subgenre ?? ''
}

function setDraft(
  track: Track,
  field: 'artist' | 'title' | 'genre' | 'subgenre',
  value: string,
): void {
  const existing = metadataDrafts.value[track.id]
  metadataDrafts.value[track.id] = {
    artist: existing?.artist ?? track.artist ?? '',
    title: existing?.title ?? track.title ?? '',
    genre: existing?.genre ?? track.genre ?? '',
    subgenre: existing?.subgenre ?? track.subgenre ?? '',
    [field]: value,
  }
}

async function saveMetadata(track: Track): Promise<void> {
  const draft = metadataDrafts.value[track.id]
  if (!draft) {
    return
  }
  const artist = draft.artist.trim()
  const title = draft.title.trim()
  const genre = draft.genre.trim()
  const subgenre = draft.subgenre.trim()
  const unchanged =
    artist === (track.artist ?? '').trim() &&
    title === (track.title ?? '').trim() &&
    genre === (track.genre ?? '').trim() &&
    subgenre === (track.subgenre ?? '').trim()
  if (unchanged) {
    delete metadataDrafts.value[track.id]
    return
  }
  if (!artist || !title) {
    snackbar.show('Artist and title are required', { color: 'warning' })
    return
  }

  metadataSavingId.value = track.id
  try {
    const result = await updateTrackMetadata(track.id, {
      artist,
      title,
      genre: genre || null,
      subgenre: subgenre || null,
    })
    delete metadataDrafts.value[track.id]
    snackbar.show(result.message ?? 'Tags updated', { color: 'success' })
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Failed to update tags', { color: 'error' })
  } finally {
    metadataSavingId.value = null
  }
}

const statusFilterModel = computed({
  get: () => props.statusFilter ?? null,
  set: (value: PipelineStage | null) => emit('update:statusFilter', value),
})

const statusFilterItems = PIPELINE_STAGE_ORDER.map((stage) => ({
  title: pipelineStageLabel(stage),
  value: stage,
}))

const filteredTracks = computed(() => {
  if (!statusFilterModel.value) {
    return props.tracks
  }
  return props.tracks.filter((t) => t.pipeline_stage === statusFilterModel.value)
})

const headers = computed(() => {
  const sort = createTrackTableSort({
    keyNotation: keyNotation.value,
    loudnessThresholds: loudnessThresholds.value,
  })

  return [
    { title: 'File', key: 'filename', sortRaw: sort.filename },
    { title: 'Artist', key: 'artist', sortRaw: sort.artist },
    { title: 'Title', key: 'title', sortRaw: sort.title },
    { title: 'Genre', key: 'genre', sortRaw: sort.genre },
    { title: 'Subgenre', key: 'subgenre', sortRaw: sort.subgenre },
    { title: 'Status', key: 'status', sortRaw: sort.status },
    { title: 'BPM', key: 'bpm', sortRaw: sort.bpm },
    { title: 'Key', key: 'key', sortRaw: sort.key },
    { title: 'Energy', key: 'energy', sortRaw: sort.energy },
    { title: 'Format', key: 'format', sortRaw: sort.format },
    { title: 'Quality', key: 'quality', sortRaw: sort.quality },
    { title: 'Bitrate', key: 'bitrate_kbps', sortRaw: sort.bitrate_kbps },
    { title: 'Loudness', key: 'loudness', sortable: false, width: '200px' },
    { title: 'Library copy', key: 'final_path', sortRaw: sort.final_path },
    { title: 'Actions', key: 'actions', sortable: false, width: '200px' },
  ]
})

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

.metadata-field {
  min-width: 120px;
  max-width: 220px;
}

.metadata-field :deep(.v-field__input) {
  padding-top: 0;
  padding-bottom: 0;
  min-height: 28px;
}
</style>
