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
}

export interface DuplicateGroup {
  id: number
  fingerprint_hash: string
  members: DuplicateGroupMember[]
}
