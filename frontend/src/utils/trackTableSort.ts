import type { KeyNotation } from '@/types/settings'
import type { Track } from '@/types/track'
import { compareBitrateTracks, compareQualityTracks } from '@/utils/audioQuality'
import { basename } from '@/utils/labels'
import { DEFAULT_KEY_NOTATION, formatTrackKey } from '@/utils/keyNotation'
import { loudnessStatus, type LoudnessThresholds } from '@/utils/loudness'
import { PIPELINE_STAGE_ORDER, type PipelineStage } from '@/utils/pipelineStage'

export function compareNullableStrings(
  a: string | null | undefined,
  b: string | null | undefined,
): number {
  const left = (a ?? '').trim().toLocaleLowerCase()
  const right = (b ?? '').trim().toLocaleLowerCase()
  if (!left && !right) {
    return 0
  }
  if (!left) {
    return 1
  }
  if (!right) {
    return -1
  }
  return left.localeCompare(right)
}

function pipelineStageRank(stage: PipelineStage): number {
  const index = PIPELINE_STAGE_ORDER.indexOf(stage)
  return index === -1 ? PIPELINE_STAGE_ORDER.length : index
}

function compareLoudnessTracks(
  a: Track,
  b: Track,
  thresholds: LoudnessThresholds,
): number {
  const aHas = a.integrated_lufs != null || a.true_peak_db != null
  const bHas = b.integrated_lufs != null || b.true_peak_db != null
  if (!aHas && !bHas) {
    return 0
  }
  if (!aHas) {
    return 1
  }
  if (!bHas) {
    return -1
  }

  const statusOrder = { ok: 0, quiet: 1, clipped: 2, unknown: 3 } as const
  const aStatus = loudnessStatus(a, thresholds)
  const bStatus = loudnessStatus(b, thresholds)
  const statusDiff = statusOrder[aStatus] - statusOrder[bStatus]
  if (statusDiff !== 0) {
    return statusDiff
  }

  return (a.integrated_lufs ?? 0) - (b.integrated_lufs ?? 0)
}

export interface TrackTableSortOptions {
  keyNotation?: KeyNotation
  loudnessThresholds: LoudnessThresholds
}

export function createTrackTableSort(options: TrackTableSortOptions) {
  const keyNotation = options.keyNotation ?? DEFAULT_KEY_NOTATION
  const { loudnessThresholds } = options

  return {
    filename: (a: Track, b: Track) =>
      compareNullableStrings(basename(a.source_path), basename(b.source_path)),
    artist: (a: Track, b: Track) => compareNullableStrings(a.artist, b.artist),
    title: (a: Track, b: Track) => compareNullableStrings(a.title, b.title),
    genre: (a: Track, b: Track) => compareNullableStrings(a.genre, b.genre),
    subgenre: (a: Track, b: Track) => compareNullableStrings(a.subgenre, b.subgenre),
    status: (a: Track, b: Track) =>
      pipelineStageRank(a.pipeline_stage) - pipelineStageRank(b.pipeline_stage),
    bpm: (a: Track, b: Track) => (a.bpm ?? -1) - (b.bpm ?? -1),
    key: (a: Track, b: Track) =>
      compareNullableStrings(formatTrackKey(a, keyNotation), formatTrackKey(b, keyNotation)),
    energy: (a: Track, b: Track) => (a.energy ?? -1) - (b.energy ?? -1),
    format: (a: Track, b: Track) =>
      compareNullableStrings(a.format_extension, b.format_extension),
    quality: compareQualityTracks,
    bitrate_kbps: compareBitrateTracks,
    loudness: (a: Track, b: Track) => compareLoudnessTracks(a, b, loudnessThresholds),
    final_path: (a: Track, b: Track) => compareNullableStrings(a.final_path, b.final_path),
  }
}

export type TrackTableSortFunctions = ReturnType<typeof createTrackTableSort>
