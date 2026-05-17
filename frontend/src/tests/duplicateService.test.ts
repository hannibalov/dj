import { describe, expect, it, vi } from 'vitest'

import { fetchDuplicateGroups, resolveDuplicateGroup } from '@/services/duplicateService'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('duplicateService', () => {
  it('fetchDuplicateGroups calls GET /duplicates', async () => {
    const groups = [
      {
        id: 1,
        fingerprint_hash: 'abc',
        preferred_track_id: null,
        members: [],
      },
    ]
    vi.mocked(api.get).mockResolvedValue(groups)

    const result = await fetchDuplicateGroups()
    expect(api.get).toHaveBeenCalledWith('/duplicates')
    expect(result).toEqual(groups)
  })

  it('resolveDuplicateGroup calls POST /duplicates/resolve', async () => {
    const body = { group_id: 1, keep_track_id: 42, archive_track_ids: [43] }
    const response = { status: 'ok', kept_track_id: 42, archived_track_ids: [43] }
    vi.mocked(api.post).mockResolvedValue(response)

    const result = await resolveDuplicateGroup(body)
    expect(api.post).toHaveBeenCalledWith('/duplicates/resolve', body)
    expect(result).toEqual(response)
  })
})
