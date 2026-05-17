import type { TrackStatus } from './track'

export interface DuplicateGroupMember {
  track_id: number
  status: TrackStatus
  source_path: string
  final_path: string | null
  fingerprint_hash: string
  duration_seconds: number | null
  format_extension: string | null
  bitrate_kbps: number | null
  artist: string | null
  title: string | null
  integrated_lufs: number | null
}

export interface DuplicateGroup {
  id: number
  fingerprint_hash: string
  preferred_track_id: number | null
  members: DuplicateGroupMember[]
}

export interface DuplicateResolveRequest {
  group_id: number
  keep_track_id: number
  archive_track_ids?: number[]
}

export interface DuplicateResolveResponse {
  status: string
  kept_track_id: number | null
  archived_track_ids: number[]
}
