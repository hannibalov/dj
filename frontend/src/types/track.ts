export type TrackStatus =
  | 'queued'
  | 'processing'
  | 'ingested'
  | 'ready'
  | 'review'
  | 'duplicate'
  | 'archived'
  | 'failed'

export interface Track {
  id: number
  status: TrackStatus
  source_path: string
  processing_path: string | null
  final_path: string | null
  artist: string | null
  title: string | null
  album: string | null
  mix_version: string | null
  tag_confidence: number | null
  needs_metadata_review: boolean
  bpm: number | null
  musical_key: string | null
  camelot: string | null
  energy: number | null
  scale: string | null
  bpm_confidence: number | null
  key_confidence: number | null
  integrated_lufs: number | null
  true_peak_db: number | null
  created_at: string
  updated_at: string
}
