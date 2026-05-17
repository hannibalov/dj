import type { PipelineSnapshot } from '@/types/pipeline'
import { api } from './api'

export function fetchPipelineStatus(): Promise<PipelineSnapshot> {
  return api.get<PipelineSnapshot>('/pipeline/status')
}
