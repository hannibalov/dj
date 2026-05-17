import type { AnalyzeBacklogResult, QueueSummary, RescanResult } from '@/types/queue'
import { api } from './api'

export function fetchQueue(): Promise<QueueSummary> {
  return api.get<QueueSummary>('/queue')
}

export function rescanQueue(): Promise<RescanResult> {
  return api.post<RescanResult>('/queue/rescan')
}

export function analyzeBacklog(): Promise<AnalyzeBacklogResult> {
  return api.post<AnalyzeBacklogResult>('/queue/analyze-backlog')
}
