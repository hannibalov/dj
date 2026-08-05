<template>
  <div class="library-page">
    <v-alert
      v-if="pipeline.lastSanityResult"
      :type="pipeline.lastSanityResult.anomaly ? 'warning' : 'info'"
      class="mb-4"
      variant="tonal"
    >
      <div class="d-flex align-center flex-wrap ga-4">
        <span>
          Scanned {{ pipeline.lastSanityResult.scanned }} tracks —
          {{ pipeline.lastSanityResult.flagged_possible_swap }} possible swaps,
          {{ pipeline.lastSanityResult.flagged_artist_in_title }} artist-in-title flags.
          <template v-if="pipeline.lastSanityResult.anomaly">
            Flag ratio looks unusually high — review before bulk-fixing.
          </template>
        </span>
        <v-spacer />
        <v-btn
          size="small"
          variant="tonal"
          :loading="pipeline.sanityCheckLoading"
          @click="pipeline.runMetadataSanityCheck()"
        >
          Run check now
        </v-btn>
      </div>
    </v-alert>
    <v-alert
      v-else
      type="info"
      variant="tonal"
      class="mb-4"
    >
      <div class="d-flex align-center flex-wrap ga-4">
        <span>No metadata sanity check has run yet.</span>
        <v-spacer />
        <v-btn
          size="small"
          variant="tonal"
          :loading="pipeline.sanityCheckLoading"
          @click="pipeline.runMetadataSanityCheck()"
        >
          Run check now
        </v-btn>
      </div>
    </v-alert>

    <v-card class="mb-4">
      <v-card-title class="d-flex align-center flex-wrap ga-2">
        <span>Library</span>
        <v-spacer />
        <v-btn
          size="small"
          variant="tonal"
          @click="renameDialogOpen = true"
        >
          Rename artist everywhere
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div class="d-flex align-center flex-wrap ga-4 mb-4">
          <v-text-field
            v-model="search"
            label="Search artist or title"
            density="compact"
            hide-details
            clearable
            style="max-width: 320px"
          />
          <v-switch
            v-model="flaggedOnly"
            label="Flagged only"
            density="compact"
            hide-details
          />
        </div>
        <LibraryTracksTable
          :tracks="filteredTracks"
          :loading="pipeline.loading && !pipeline.snapshot"
        />
      </v-card-text>
    </v-card>

    <v-dialog
      v-model="renameDialogOpen"
      max-width="480"
    >
      <v-card>
        <v-card-title>Rename artist everywhere</v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">
            Renames every track matching the old artist name to the new one.
          </p>
          <v-text-field
            v-model="oldArtist"
            label="Old artist"
            density="compact"
            class="mb-2"
          />
          <v-text-field
            v-model="newArtist"
            label="New artist"
            density="compact"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="renaming"
            @click="renameDialogOpen = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="renaming"
            :disabled="!oldArtist.trim() || !newArtist.trim()"
            @click="confirmRename"
          >
            Confirm
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import LibraryTracksTable from '@/components/LibraryTracksTable.vue'
import { renameArtistEverywhere } from '@/services/trackService'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useSnackbarStore } from '@/stores/snackbarStore'
import { filterLibraryTracks } from '@/utils/libraryFilter'

const pipeline = usePipelineStore()
const snackbar = useSnackbarStore()

const search = ref('')
const flaggedOnly = ref(false)

const renameDialogOpen = ref(false)
const oldArtist = ref('')
const newArtist = ref('')
const renaming = ref(false)

const filteredTracks = computed(() =>
  filterLibraryTracks(pipeline.tracks, {
    search: search.value ?? '',
    flaggedOnly: flaggedOnly.value,
  }),
)

async function confirmRename(): Promise<void> {
  const old_artist = oldArtist.value.trim()
  const new_artist = newArtist.value.trim()
  if (!old_artist || !new_artist) {
    return
  }

  renaming.value = true
  try {
    const result = await renameArtistEverywhere({ old_artist, new_artist })
    renameDialogOpen.value = false
    oldArtist.value = ''
    newArtist.value = ''
    snackbar.show(
      `Rename artist: matched ${result.matched}, updated ${result.updated}.`,
      { color: 'success' },
    )
    await pipeline.load()
  } catch (e) {
    snackbar.show(e instanceof Error ? e.message : 'Rename artist failed', {
      color: 'error',
    })
  } finally {
    renaming.value = false
  }
}

onMounted(() => {
  if (!pipeline.snapshot) {
    void pipeline.load()
  }
  if (pipeline.lastSanityResult == null) {
    void pipeline.runMetadataSanityCheck()
  }
})
</script>
