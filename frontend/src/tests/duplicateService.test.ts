import { describe, expect, it, vi } from 'vitest'

import {
  fetchDuplicateGroups,
  fetchSongDuplicateGroups,
  resolveDuplicateGroup,
  resolveSongDuplicateGroup,
} from '@/services/duplicateService'
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

  it('fetchSongDuplicateGroups calls GET /duplicates/songs', async () => {
    const groups = [
      {
        group_key: 'mbid:1',
        match_type: 'musicbrainz',
        label: 'Artist — Title',
        musicbrainz_recording_id: '1',
        suggested_keep_track_id: 42,
        members: [],
      },
    ]
    vi.mocked(api.get).mockResolvedValue(groups)

    const result = await fetchSongDuplicateGroups()
    expect(api.get).toHaveBeenCalledWith('/duplicates/songs')
    expect(result).toEqual(groups)
  })

  it('resolveSongDuplicateGroup calls POST /duplicates/songs/resolve', async () => {
    const body = { group_key: 'mbid:1', keep_track_id: 42, archive_track_ids: [43] }
    const response = { status: 'ok', kept_track_id: 42, archived_track_ids: [43] }
    vi.mocked(api.post).mockResolvedValue(response)

    const result = await resolveSongDuplicateGroup(body)
    expect(api.post).toHaveBeenCalledWith('/duplicates/songs/resolve', body)
    expect(result).toEqual(response)
  })
})
