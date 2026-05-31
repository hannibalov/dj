import { describe, expect, it, vi } from 'vitest'

import { downloadYouTube } from '@/services/downloadService'
import type { YouTubeDownloadResult } from '@/types/download'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({
  api: {
    post: vi.fn(),
  },
}))

describe('downloadService', () => {
  it('downloadYouTube calls POST /downloads/youtube', async () => {
    const response: YouTubeDownloadResult = {
      status: 'ok',
      enqueued: true,
      job_id: 7,
      message: 'YouTube download queued',
    }
    vi.mocked(api.post).mockResolvedValue(response)

    const result = await downloadYouTube('https://www.youtube.com/watch?v=abc123')
    expect(api.post).toHaveBeenCalledWith('/downloads/youtube', {
      url: 'https://www.youtube.com/watch?v=abc123',
    })
    expect(result).toEqual(response)
  })
})
