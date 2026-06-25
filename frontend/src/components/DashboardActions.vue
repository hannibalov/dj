<template>
  <v-card
    class="dashboard-actions mb-4"
    variant="flat"
    color="surface"
  >
    <v-card-text class="d-flex flex-wrap align-center justify-space-between ga-3 py-3">
      <h1 class="text-h5 mb-0">
        Dashboard
      </h1>
      <span class="d-flex flex-wrap ga-2">
        <v-btn
          color="primary"
          variant="outlined"
          prepend-icon="mdi-database-sync"
          :loading="loading"
          title="Scan all library folders, repair stale paths, enqueue new watch files, and refresh artist/title from filenames using known artists"
          @click="$emit('library-sync')"
        >
          Sync library
        </v-btn>
        <v-btn
          color="primary"
          prepend-icon="mdi-folder-search"
          :loading="loading"
          @click="$emit('rescan')"
        >
          Rescan watch folder
        </v-btn>
        <v-btn
          color="secondary"
          variant="flat"
          prepend-icon="mdi-waveform"
          :loading="loading"
          @click="$emit('analyze-backlog')"
        >
          Analyze backlog
        </v-btn>
        <v-btn
          color="secondary"
          variant="outlined"
          prepend-icon="mdi-refresh"
          :loading="loading"
          title="Re-runs analyze, fingerprint, tag, and route for every track (one queue job at a time)"
          @click="$emit('reanalyze-all')"
        >
          Reanalyze all
        </v-btn>
        <v-btn
          color="secondary"
          variant="outlined"
          prepend-icon="mdi-tag-multiple"
          :loading="loading"
          title="Fetch missing genre/subgenre from MusicBrainz for tagged tracks (no full reanalyze)"
          @click="$emit('genre-backfill')"
        >
          Genre backfill
        </v-btn>
      </span>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
defineProps<{
  loading: boolean
}>()

defineEmits<{
  rescan: []
  'library-sync': []
  'analyze-backlog': []
  'reanalyze-all': []
  'genre-backfill': []
}>()
</script>
