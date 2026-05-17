import type { DuplicateGroup } from '@/types/duplicate'

import { api } from './api'

export function fetchDuplicateGroups(): Promise<DuplicateGroup[]> {
  return api.get<DuplicateGroup[]>('/duplicates')
}
