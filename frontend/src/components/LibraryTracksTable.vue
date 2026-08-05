<template>
  <v-data-table
    :headers="headers"
    :items="tracks"
    :loading="loading"
    item-key="id"
    density="compact"
    :items-per-page="15"
    no-data-text="No tracks match the current filters"
  >
    <template #[`item.filename`]="{ item }">
      {{ basename(item.source_path) }}
    </template>
    <template #[`item.artist`]="{ item }">
      <EditableMetadataField
        :model-value="draftArtist(item)"
        placeholder="Artist"
        :disabled="metadataSavingId === item.id"
        @update:model-value="(v) => setDraft(item, 'artist', v)"
        @blur="() => saveMetadata(item)"
      />
    </template>
    <template #[`item.title`]="{ item }">
      <EditableMetadataField
        :model-value="draftTitle(item)"
        placeholder="Title"
        :disabled="metadataSavingId === item.id"
        @update:model-value="(v) => setDraft(item, 'title', v)"
        @blur="() => saveMetadata(item)"
      />
    </template>
    <template #[`item.genre`]="{ item }">
      <EditableMetadataField
        :model-value="draftGenre(item)"
        placeholder="Genre"
        :disabled="metadataSavingId === item.id"
        @update:model-value="(v) => setDraft(item, 'genre', v)"
        @blur="() => saveMetadata(item)"
      />
    </template>
    <template #[`item.subgenre`]="{ item }">
      <EditableMetadataField
        :model-value="draftSubgenre(item)"
        placeholder="Subgenre"
        :disabled="metadataSavingId === item.id"
        @update:model-value="(v) => setDraft(item, 'subgenre', v)"
        @blur="() => saveMetadata(item)"
      />
    </template>
    <template #[`item.metadata_issue`]="{ item }">
      <v-chip
        v-if="item.metadata_issue === 'possible_swap'"
        size="x-small"
        color="warning"
      >
        Possible swap
      </v-chip>
      <v-chip
        v-else-if="item.metadata_issue === 'artist_in_title'"
        size="x-small"
        color="info"
      >
        Artist in title
      </v-chip>
    </template>
    <template #[`item.actions`]="{ item }">
      <v-btn
        v-if="item.metadata_issue === 'possible_swap'"
        size="x-small"
        variant="tonal"
        color="primary"
        :loading="swappingId === item.id"
        :disabled="swappingId != null && swappingId !== item.id"
        @click="onSwap(item.id)"
      >
        Swap
      </v-btn>
    </template>
  </v-data-table>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import EditableMetadataField from '@/components/EditableMetadataField.vue'
import { swapArtistTitle, updateTrackMetadata } from '@/services/trackService'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'
import type { Track } from '@/types/track'
import { basename } from '@/utils/labels'
import { DEFAULT_LOUDNESS_THRESHOLDS } from '@/utils/loudness'
import { createTrackTableSort } from '@/utils/trackTableSort'

defineProps<{
  tracks: Track[]
  loading: boolean
}>()

const pipeline = usePipelineStore()
const snackbar = useSnackbarStore()

const swappingId = ref<number | null>(null)
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

async function onSwap(trackId: number): Promise<void> {
  swappingId.value = trackId
  try {
    const result = await swapArtistTitle(trackId)
    snackbar.show(result.message ?? 'Artist and title swapped', { color: 'success' })
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Swap failed', { color: 'error' })
  } finally {
    swappingId.value = null
  }
}

const sort = createTrackTableSort({ loudnessThresholds: DEFAULT_LOUDNESS_THRESHOLDS })

const headers = [
  { title: 'File', key: 'filename', sortRaw: sort.filename },
  { title: 'Artist', key: 'artist', sortRaw: sort.artist },
  { title: 'Title', key: 'title', sortRaw: sort.title },
  { title: 'Genre', key: 'genre', sortRaw: sort.genre },
  { title: 'Subgenre', key: 'subgenre', sortRaw: sort.subgenre },
  { title: 'Issue', key: 'metadata_issue', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, width: '120px' },
]
</script>
