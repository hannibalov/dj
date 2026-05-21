import type { Track } from '@/types/track'

import { api } from './api'

export interface TrackActionResponse {
  status: string
  track: Track
  message: string | null
}

export interface TrackDeleteResponse {
  status: string
  message: string
  deleted_count: number
}

export function resetTrack(trackId: number): Promise<TrackActionResponse> {
  return api.post<TrackActionResponse>(`/tracks/${trackId}/reset`)
}

export function confirmTrackReview(trackId: number): Promise<TrackActionResponse> {
  return api.post<TrackActionResponse>(`/tracks/${trackId}/confirm-review`)
}

export function deleteFailedTrack(trackId: number): Promise<TrackDeleteResponse> {
  return api.delete<TrackDeleteResponse>(`/tracks/${trackId}`)
}

export function deleteAllFailedTracks(): Promise<TrackDeleteResponse> {
  return api.post<TrackDeleteResponse>('/tracks/delete-failed')
}
