import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as settingsService from '@/services/settingsService'
import { useSettingsStore } from '@/stores/settingsStore'

describe('settingsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads settings from API', async () => {
    const mockSettings = {
      watch_folder: '/data/watch',
      incoming_folder: '/data/incoming',
      processing_folder: '/data/processing',
      ready_folder: '/data/ready',
      review_folder: '/data/review',
      duplicates_folder: '/data/duplicates',
      archive_folder: '/data/archive',
      failed_folder: '/data/failed',
      logs_folder: '/data/logs',
      rekordbox_export_folder: '/data/rekordbox',
      stability_poll_seconds: 2,
      stability_required_seconds: 10,
      tag_confidence_threshold: 0.5,
      naming_template: '{title} - {artist} ({mix}){ext}',
      review_lufs_threshold: -18,
      review_true_peak_db: -0.1,
    }
    vi.spyOn(settingsService, 'fetchSettings').mockResolvedValue(mockSettings)

    const store = useSettingsStore()
    await store.load()

    expect(store.settings).toEqual(mockSettings)
    expect(store.error).toBeNull()
  })
})
