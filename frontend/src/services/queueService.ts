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

export function reanalyzeAll(): Promise<AnalyzeBacklogResult> {
  return api.post<AnalyzeBacklogResult>('/queue/reanalyze-all')
}

export function unstickQueue(): Promise<AnalyzeBacklogResult> {
  return api.post<AnalyzeBacklogResult>('/queue/unstick')
}

export interface ClearFailedJobsResult {
  status: string
  deleted_count: number
  message: string
}

export function clearFailedJobs(): Promise<ClearFailedJobsResult> {
  return api.post<ClearFailedJobsResult>('/queue/clear-failed-jobs')
}
