import type {
  AnalyzeBacklogResult,
  GenreBackfillResult,
  LibrarySyncResult,
  QueueSummary,
  RescanResult,
} from '@/types/queue'
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

export function genreBackfill(): Promise<GenreBackfillResult> {
  return api.post<GenreBackfillResult>('/queue/genre-backfill')
}

export function librarySync(): Promise<LibrarySyncResult> {
  return api.post<LibrarySyncResult>('/queue/library-sync')
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

export interface MetadataSanityResponse {
  status: string
  scanned: number
  flagged_possible_swap: number
  flagged_artist_in_title: number
  artist_in_title_ratio: number
  anomaly: boolean
}

export function metadataSanityCheck(): Promise<MetadataSanityResponse> {
  return api.post<MetadataSanityResponse>('/queue/metadata-sanity-check')
}
