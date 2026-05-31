export interface YouTubeDownloadResult {
  status: string
  enqueued: boolean
  job_id?: number | null
  skip_reason?: string | null
  message: string
}
