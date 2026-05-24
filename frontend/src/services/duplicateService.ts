import type {
  DuplicateGroup,
  DuplicateResolveRequest,
  DuplicateResolveResponse,
} from '@/types/duplicate'
import type {
  SongDuplicateGroup,
  SongDuplicateResolveRequest,
  SongDuplicateResolveResponse,
} from '@/types/songDuplicate'

import { api } from './api'

export function fetchDuplicateGroups(): Promise<DuplicateGroup[]> {
  return api.get<DuplicateGroup[]>('/duplicates')
}

export function fetchSongDuplicateGroups(): Promise<SongDuplicateGroup[]> {
  return api.get<SongDuplicateGroup[]>('/duplicates/songs')
}

export function resolveDuplicateGroup(
  body: DuplicateResolveRequest,
): Promise<DuplicateResolveResponse> {
  return api.post<DuplicateResolveResponse>('/duplicates/resolve', body)
}

export function resolveSongDuplicateGroup(
  body: SongDuplicateResolveRequest,
): Promise<SongDuplicateResolveResponse> {
  return api.post<SongDuplicateResolveResponse>('/duplicates/songs/resolve', body)
}
