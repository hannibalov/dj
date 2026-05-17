export interface FolderSettings {
  watch_folder: string
  incoming_folder: string
  processing_folder: string
  ready_folder: string
  review_folder: string
  duplicates_folder: string
  archive_folder: string
  failed_folder: string
  logs_folder: string
  rekordbox_export_folder: string
}

export interface AppSettings extends FolderSettings {
  stability_poll_seconds: number
  stability_required_seconds: number
  tag_confidence_threshold: number
  naming_template: string
  review_lufs_threshold: number
  review_true_peak_db: number
}

export interface SettingsUpdatePayload {
  folders?: FolderSettings
  stability_poll_seconds?: number
  stability_required_seconds?: number
  tag_confidence_threshold?: number
  naming_template?: string
  review_lufs_threshold?: number
  review_true_peak_db?: number
}
