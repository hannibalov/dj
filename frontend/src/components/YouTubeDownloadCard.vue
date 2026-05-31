<template>
  <v-card class="youtube-download-card mb-4">
    <v-card-title class="d-flex align-center ga-2">
      <v-icon icon="mdi-youtube" />
      Download from YouTube
    </v-card-title>
    <v-card-text>
      <p class="text-body-2 text-medium-emphasis mb-3">
        Paste a YouTube URL to download best-available audio as 320 kbps MP3 with loudness
        normalization (-9 LUFS club master), cover art, and tags into the watch folder. Ensure the worker
        is running.
      </p>
      <v-form @submit.prevent="submit">
        <v-text-field
          v-model="url"
          label="YouTube URL"
          placeholder="https://www.youtube.com/watch?v=..."
          prepend-inner-icon="mdi-link"
          :disabled="loading"
          :error-messages="error"
          clearable
          hide-details="auto"
          class="mb-3"
        />
        <v-btn
          type="submit"
          color="primary"
          prepend-icon="mdi-download"
          :loading="loading"
          :disabled="!url.trim()"
        >
          Download MP3
        </v-btn>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { downloadYouTube } from '@/services/downloadService'
import { useSnackbarStore } from '@/stores/snackbarStore'

const url = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const snackbar = useSnackbarStore()

async function submit(): Promise<void> {
  const trimmed = url.value.trim()
  if (!trimmed) {
    return
  }

  loading.value = true
  error.value = null
  try {
    const result = await downloadYouTube(trimmed)
    snackbar.show(result.message, { color: result.enqueued ? 'success' : 'warning' })
    if (result.enqueued) {
      url.value = ''
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Download request failed'
    error.value = message
    snackbar.show(message, { color: 'error' })
  } finally {
    loading.value = false
  }
}
</script>
