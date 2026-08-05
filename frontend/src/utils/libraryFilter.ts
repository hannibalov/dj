import type { Track } from '@/types/track'

export interface LibraryFilterOptions {
  search: string
  flaggedOnly: boolean
}

export function filterLibraryTracks(
  tracks: Track[],
  { search, flaggedOnly }: LibraryFilterOptions,
): Track[] {
  const query = search.trim().toLocaleLowerCase()

  return tracks.filter((track) => {
    if (flaggedOnly && track.metadata_issue == null) {
      return false
    }
    if (!query) {
      return true
    }
    const haystack = `${track.artist ?? ''} ${track.title ?? ''}`.toLocaleLowerCase()
    return haystack.includes(query)
  })
}
