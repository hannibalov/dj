<template>
  <div class="dashboard-page">
    <h1 class="text-h5 mb-4">
      Settings
    </h1>
    <v-alert
      v-if="settingsStore.error"
      type="error"
      class="mb-4"
    >
      {{ settingsStore.error }}
    </v-alert>
    <template v-if="settingsStore.settings">
      <h2 class="text-subtitle-1 mb-2">
        Folders
      </h2>
      <FolderSettingsForm
        :model-value="settingsStore.settings"
        :loading="settingsStore.loading"
        @submit="onSaveFolders"
      />
      <v-divider class="my-6" />
      <h2 class="text-subtitle-1 mb-2">
        Tagging &amp; naming
      </h2>
      <TagSettingsForm
        :tag-confidence-threshold="settingsStore.settings.tag_confidence_threshold"
        :naming-template="settingsStore.settings.naming_template"
        :loading="settingsStore.loading"
        @submit="onSaveTagging"
      />
      <v-divider class="my-6" />
      <h2 class="text-subtitle-1 mb-2">
        Loudness gates
      </h2>
      <p class="text-body-2 text-medium-emphasis mb-4">
        Tracks outside these limits are sent to <code>review/</code> instead of <code>ready/</code>.
      </p>
      <LoudnessSettingsForm
        :review-lufs-threshold="settingsStore.settings.review_lufs_threshold"
        :review-true-peak-db="settingsStore.settings.review_true_peak_db"
        :loading="settingsStore.loading"
        @submit="onSaveLoudness"
      />
      <v-divider class="my-6" />
      <h2 class="text-subtitle-1 mb-2">
        Quality gates
      </h2>
      <p class="text-body-2 text-medium-emphasis mb-4">
        Tracks below these audio specs are sent to <code>review/</code> instead of <code>ready/</code>.
        Set a value to <code>0</code> to disable that check.
      </p>
      <QualitySettingsForm
        :review-min-mp3-bitrate-kbps="settingsStore.settings.review_min_mp3_bitrate_kbps"
        :review-min-lossless-bit-depth="settingsStore.settings.review_min_lossless_bit_depth"
        :review-min-lossless-sample-rate-hz="settingsStore.settings.review_min_lossless_sample_rate_hz"
        :loading="settingsStore.loading"
        @submit="onSaveQuality"
      />
    </template>
    <v-progress-linear
      v-else-if="settingsStore.loading"
      indeterminate
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

import FolderSettingsForm from '@/components/FolderSettingsForm.vue'
import LoudnessSettingsForm from '@/components/LoudnessSettingsForm.vue'
import QualitySettingsForm from '@/components/QualitySettingsForm.vue'
import TagSettingsForm from '@/components/TagSettingsForm.vue'
import { useSettingsStore } from '@/stores/settingsStore'
import type { FolderSettings } from '@/types/settings'

const settingsStore = useSettingsStore()

onMounted(() => {
  void settingsStore.load()
})

async function onSaveFolders(folders: FolderSettings): Promise<void> {
  await settingsStore.save({ folders })
}

async function onSaveTagging(payload: {
  tag_confidence_threshold: number
  naming_template: string
}): Promise<void> {
  await settingsStore.save(payload)
}

async function onSaveLoudness(payload: {
  review_lufs_threshold: number
  review_true_peak_db: number
}): Promise<void> {
  await settingsStore.save(payload)
}

async function onSaveQuality(payload: {
  review_min_mp3_bitrate_kbps: number
  review_min_lossless_bit_depth: number
  review_min_lossless_sample_rate_hz: number
}): Promise<void> {
  await settingsStore.save(payload)
}
</script>
