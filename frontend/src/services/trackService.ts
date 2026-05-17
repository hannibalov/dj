import type { Track } from '@/types/track'

import { api } from './api'

export interface TrackActionResponse {
  status: string
  track: Track
  message: string | null
}

export function resetTrack(trackId: number): Promise<TrackActionResponse> {
  return api.post<TrackActionResponse>(`/tracks/${trackId}/reset`)
}

export function confirmTrackReview(trackId: number): Promise<TrackActionResponse> {
  return api.post<TrackActionResponse>(`/tracks/${trackId}/confirm-review`)
}
