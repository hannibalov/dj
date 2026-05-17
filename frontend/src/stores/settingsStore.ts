import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchSettings, updateSettings } from '@/services/settingsService'
import type { AppSettings, SettingsUpdatePayload } from '@/types/settings'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<AppSettings | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      settings.value = await fetchSettings()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load settings'
    } finally {
      loading.value = false
    }
  }

  async function save(payload: SettingsUpdatePayload): Promise<void> {
    loading.value = true
    error.value = null
    try {
      settings.value = await updateSettings(payload)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to save settings'
      throw e
    } finally {
      loading.value = false
    }
  }

  return { settings, loading, error, load, save }
})
