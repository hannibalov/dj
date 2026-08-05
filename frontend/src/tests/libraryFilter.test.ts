import { describe, expect, it } from 'vitest'

import type { Track } from '@/types/track'
import { filterLibraryTracks } from '@/utils/libraryFilter'

function track(overrides: Partial<Track> = {}): Track {
  return {
    id: 1,
    status: 'ready',
    pipeline_stage: 'ready',
    source_path: '/data/watch/song.mp3',
    processing_path: null,
    final_path: null,
    artist: null,
    title: null,
    album: null,
    genre: null,
    subgenre: null,
    metadata_issue: null,
    mix_version: null,
    tag_confidence: null,
    needs_metadata_review: false,
    bpm: null,
    musical_key: null,
    camelot: null,
    energy: null,
    scale: null,
    bpm_confidence: null,
    key_confidence: null,
    integrated_lufs: null,
    true_peak_db: null,
    format_extension: null,
    audio_family: null,
    bitrate_kbps: null,
    sample_rate_hz: null,
    bits_per_sample: null,
    created_at: '',
    updated_at: '',
    ...overrides,
  }
}

describe('libraryFilter', () => {
  it('matches case-insensitively against artist and title', () => {
    const tracks = [
      track({ id: 1, artist: 'Daft Punk', title: 'One More Time' }),
      track({ id: 2, artist: 'Justice', title: 'Genesis' }),
    ]
    const result = filterLibraryTracks(tracks, { search: 'daft', flaggedOnly: false })
    expect(result.map((t) => t.id)).toEqual([1])
  })

  it('matches against title when search does not match artist', () => {
    const tracks = [
      track({ id: 1, artist: 'Daft Punk', title: 'One More Time' }),
      track({ id: 2, artist: 'Justice', title: 'Genesis' }),
    ]
    const result = filterLibraryTracks(tracks, { search: 'genesis', flaggedOnly: false })
    expect(result.map((t) => t.id)).toEqual([2])
  })

  it('returns all tracks when search is empty and flaggedOnly is false', () => {
    const tracks = [
      track({ id: 1, metadata_issue: null }),
      track({ id: 2, metadata_issue: 'possible_swap' }),
    ]
    const result = filterLibraryTracks(tracks, { search: '', flaggedOnly: false })
    expect(result.map((t) => t.id)).toEqual([1, 2])
  })

  it('filters to only flagged tracks when flaggedOnly is true', () => {
    const tracks = [
      track({ id: 1, metadata_issue: null }),
      track({ id: 2, metadata_issue: 'possible_swap' }),
      track({ id: 3, metadata_issue: 'artist_in_title' }),
    ]
    const result = filterLibraryTracks(tracks, { search: '', flaggedOnly: true })
    expect(result.map((t) => t.id)).toEqual([2, 3])
  })

  it('combines search and flaggedOnly filters', () => {
    const tracks = [
      track({ id: 1, artist: 'Daft Punk', title: 'One More Time', metadata_issue: 'possible_swap' }),
      track({ id: 2, artist: 'Daft Punk', title: 'Aerodynamic', metadata_issue: null }),
    ]
    const result = filterLibraryTracks(tracks, { search: 'daft', flaggedOnly: true })
    expect(result.map((t) => t.id)).toEqual([1])
  })
})
