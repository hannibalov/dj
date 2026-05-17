<template>
  <v-form @submit.prevent="submit">
    <v-row>
      <v-col
        v-for="field in fields"
        :key="field.key"
        cols="12"
        md="6"
      >
        <v-text-field
          v-model="form[field.key]"
          :label="field.label"
          density="compact"
          hide-details="auto"
        />
      </v-col>
    </v-row>
    <v-btn
      type="submit"
      color="primary"
      class="mt-4"
      :loading="loading"
    >
      Save
    </v-btn>
  </v-form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

import type { AppSettings, FolderSettings } from '@/types/settings'

const props = defineProps<{
  modelValue: AppSettings
  loading: boolean
}>()

const emit = defineEmits<{
  submit: [folders: FolderSettings]
}>()

const fields: { key: keyof FolderSettings; label: string }[] = [
  { key: 'watch_folder', label: 'Watch folder' },
  { key: 'incoming_folder', label: 'Incoming folder' },
  { key: 'processing_folder', label: 'Processing folder' },
  { key: 'ready_folder', label: 'Ready folder' },
  { key: 'review_folder', label: 'Review folder' },
  { key: 'duplicates_folder', label: 'Duplicates folder' },
  { key: 'archive_folder', label: 'Archive folder' },
  { key: 'failed_folder', label: 'Failed folder' },
  { key: 'logs_folder', label: 'Logs folder' },
  { key: 'rekordbox_export_folder', label: 'Rekordbox export folder' },
]

const form = reactive<FolderSettings>({ ...pickFolders(props.modelValue) })

watch(
  () => props.modelValue,
  (value) => {
    Object.assign(form, pickFolders(value))
  },
)

function pickFolders(settings: AppSettings): FolderSettings {
  const { stability_poll_seconds: _a, stability_required_seconds: _b, ...folders } = settings
  return folders
}

function submit(): void {
  emit('submit', { ...form })
}
</script>
