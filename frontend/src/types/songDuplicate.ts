import type { TrackStatus } from './track'

export interface SongDuplicateGroupMember {
  track_id: number
  status: TrackStatus
  source_path: string
  final_path: string | null
  fingerprint_hash: string | null
  duration_seconds: number | null
  format_extension: string | null
  bitrate_kbps: number | null
  artist: string | null
  title: string | null
  integrated_lufs: number | null
  energy: number | null
  bpm: number | null
  camelot: string | null
}

export interface SongDuplicateGroup {
  group_key: string
  match_type: 'musicbrainz' | 'metadata'
  label: string
  musicbrainz_recording_id: string | null
  suggested_keep_track_id: number | null
  members: SongDuplicateGroupMember[]
}

export interface SongDuplicateResolveRequest {
  group_key: string
  keep_track_id: number
  archive_track_ids?: number[]
}

export interface SongDuplicateResolveResponse {
  status: string
  kept_track_id: number | null
  archived_track_ids: number[]
}
