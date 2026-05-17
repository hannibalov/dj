import { describe, expect, it, vi } from 'vitest'

import { fetchDuplicateGroups } from '@/services/duplicateService'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

describe('duplicateService', () => {
  it('fetchDuplicateGroups calls GET /duplicates', async () => {
    const groups = [
      {
        id: 1,
        fingerprint_hash: 'abc',
        members: [],
      },
    ]
    vi.mocked(api.get).mockResolvedValue(groups)

    const result = await fetchDuplicateGroups()
    expect(api.get).toHaveBeenCalledWith('/duplicates')
    expect(result).toEqual(groups)
  })
})
