import type { YouTubeDownloadResult } from '@/types/download'
import { api } from './api'

export function downloadYouTube(url: string): Promise<YouTubeDownloadResult> {
  return api.post<YouTubeDownloadResult>('/downloads/youtube', { url })
}
