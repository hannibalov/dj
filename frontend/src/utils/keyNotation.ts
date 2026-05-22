import type { KeyNotation } from '@/types/settings'
import type { Track } from '@/types/track'

export const DEFAULT_KEY_NOTATION: KeyNotation = 'camelot'

export function formatTrackKey(
  track: Pick<Track, 'musical_key' | 'scale' | 'camelot'>,
  notation: KeyNotation = DEFAULT_KEY_NOTATION,
): string | null {
  const traditional =
    track.musical_key && track.scale ? `${track.musical_key} ${track.scale}` : null
  if (notation === 'camelot') {
    return track.camelot ?? traditional
  }
  return traditional
}
