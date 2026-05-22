import { describe, expect, it } from 'vitest'

import { formatTrackKey } from '@/utils/keyNotation'

const track = {
  musical_key: 'A',
  scale: 'minor',
  camelot: '8A',
}

describe('formatTrackKey', () => {
  it('shows camelot when notation is camelot', () => {
    expect(formatTrackKey(track, 'camelot')).toBe('8A')
  })

  it('shows traditional when notation is traditional', () => {
    expect(formatTrackKey(track, 'traditional')).toBe('A minor')
  })

  it('falls back to traditional when camelot missing', () => {
    expect(formatTrackKey({ ...track, camelot: null }, 'camelot')).toBe('A minor')
  })

  it('returns null when no key data', () => {
    expect(formatTrackKey({ musical_key: null, scale: null, camelot: null }, 'camelot')).toBeNull()
  })
})
