import type {
  DuplicateGroup,
  DuplicateResolveRequest,
  DuplicateResolveResponse,
} from '@/types/duplicate'

import { api } from './api'

export function fetchDuplicateGroups(): Promise<DuplicateGroup[]> {
  return api.get<DuplicateGroup[]>('/duplicates')
}

export function resolveDuplicateGroup(
  body: DuplicateResolveRequest,
): Promise<DuplicateResolveResponse> {
  return api.post<DuplicateResolveResponse>('/duplicates/resolve', body)
}
