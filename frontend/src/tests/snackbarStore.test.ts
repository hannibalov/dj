import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { SNACKBAR_TIMEOUT_MS, useSnackbarStore } from '@/stores/snackbarStore'

describe('snackbarStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('show sets message, color, and visibility', () => {
    const snackbar = useSnackbarStore()
    snackbar.show('Done', { color: 'success' })

    expect(snackbar.message).toBe('Done')
    expect(snackbar.color).toBe('success')
    expect(snackbar.visible).toBe(true)
    expect(snackbar.timeout).toBe(SNACKBAR_TIMEOUT_MS)
  })

  it('close hides snackbar', () => {
    const snackbar = useSnackbarStore()
    snackbar.show('Hi')
    snackbar.close()
    expect(snackbar.visible).toBe(false)
  })
})
