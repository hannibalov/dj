# Phase 4 — Metadata tagging & renaming

**Status: complete** (May 2026)

**Prerequisite:** Phase 3 — [PHASE3.md](./PHASE3.md) (fingerprints & duplicates). **Next:** [PHASE5.md](./PHASE5.md) (duplicate resolution).

---

## Goal

Enrich track metadata via AcoustID (and embedded tags / filename fallback), **rename files** to a consistent DJ library convention, write tags (artist, title, album, genre), resolve **genre / subgenre** (MusicBrainz + embedded tags), then route clean copies to `ready/` for Rekordbox import.

This is the phase that answers: *“Why is my file still named `Wonderwall - Oasis.mp3` in `ready/`?”* — **renaming happens here, not in Phase 2 or 3.**

---

## What was delivered

### Pipeline chain

```text
INGEST → ANALYZE → FINGERPRINT → TAG → ROUTE
                      ↓
              duplicates/<hash>/  (non-preferred copies)
              ready/ or review/   (preferred copy, loudness + metadata rules)
```

- `FingerprintService` enqueues `TAG` (not `ROUTE`) for preferred copies
- `TagService` matches metadata, renames in `processing/`, writes tags, enqueues `ROUTE`
- `RoutingService` copies the **renamed** basename to `ready/` or `review/`

### Backend — metadata

| Area | Location |
|------|----------|
| Filename sanitizer & template | `backend/app/metadata/rename.py` |
| Embedded / filename hints | `backend/app/metadata/tags.py` |
| AcoustID lookup | `backend/app/metadata/acoustid_lookup.py` |
| MusicBrainz genre/tags | `backend/app/metadata/musicbrainz_lookup.py` |
| Genre resolve (MB + embedded) | `backend/app/metadata/genre_resolve.py` |
| Match orchestration | `backend/app/metadata/matcher.py` |
| Job handler | `backend/app/services/tag_service.py` |
| Manual metadata override | `backend/app/services/track_metadata_service.py` |
| WAV/AIFF ID3 tag I/O | `backend/app/metadata/tags.py` (`TCON`, `TPE1`, `TIT2`, …) |

**Track columns added:** `album`, `mix_version`, `musicbrainz_recording_id`, `tag_confidence`, `needs_metadata_review`, `tagged_at`, `genre`, `subgenre`

**Fingerprint column added:** `raw_fingerprint` (Chromaprint string for AcoustID)

**Config / settings:** `DJ_ACOUSTID_API_KEY`, `DJ_TAG_CONFIDENCE_THRESHOLD`, `DJ_NAMING_TEMPLATE` (UI-overridable in Settings)

### Renaming convention

```text
Title - Artist (Mix).ext
```

Default template: `{title} - {artist} ({mix}){ext}` — missing mix becomes `Original Mix`.

ID3 tags still store `artist` and `title` fields separately; only the **filename** uses song name first.

### Routing (refined)

- **Loudness gate:** integrated LUFS below threshold, or true peak above threshold (default `3.0` dBTP — see [README § Configuration](../README.md#configuration))
- **Quality gate:** MP3 below min bitrate, or lossless below min bit depth / sample rate (defaults: 320 kbps, 16-bit, 44.1 kHz; set `0` in Settings to disable a check)
- Low-confidence metadata → `needs_metadata_review` → `review/` even when loudness and quality are OK
- No match still enqueues `ROUTE` (original basename, metadata review flag)

### Frontend (dashboard tracks table)

| Feature | Location |
|---------|----------|
| Artist / title (editable → `PATCH /tracks/{id}/metadata`) | `TracksTable.vue`, `trackService.ts` |
| Genre / subgenre (read-only; set at TAG) | `TracksTable.vue` |
| Format / quality / bitrate (from file via API; sortable columns) | `TracksTable.vue`, `utils/audioQuality.ts` |
| Loudness badges (OK / Too quiet / High peak; thresholds from Settings) | `TracksTable.vue`, `utils/loudness.ts` |
| Metadata review chip | `TracksTable.vue` |
| Tagging settings | `TagSettingsForm.vue`, `SettingsPage.vue` |
| Loudness + quality gate settings | `LoudnessSettingsForm.vue`, `QualitySettingsForm.vue`, `SettingsPage.vue` |

### Genre / subgenre (TAG step)

1. If AcoustID returns a MusicBrainz recording ID → `GET /recording/{id}?inc=genres+tags` (1 req/s; worker is sequential).
2. **Genre** — top MusicBrainz genre, else top tag, else embedded `genre` tag.
3. **Subgenre** — more specific MusicBrainz tag (e.g. `Techno` → `Minimal Techno`), else second part of embedded `Genre; Subgenre`.
4. Written to DB and to the file genre tag as `Genre; Subgenre` when both exist.

### WAV / AIFF tagging

Lossless files use **ID3 frames** inside the WAV/AIFF container (`TPE1`, `TIT2`, `TCON`), not mutagen’s “easy” API. Assigning plain strings caused `not a Frame instance` TAG failures on `.wav` in older builds.

### Tests

**Backend (36):** `test_rename`, `test_tag_service`, updated fingerprint tests.

```bash
make test
make lint
```

---

## API (metadata)

| Method | Path | Purpose |
|--------|------|---------|
| PATCH | `/tracks/{id}/metadata` | Body: `{ "artist", "title" }` — write tags, rename file, set `tagged_at` |

## Track & job lifecycle (Phase 4)

| Job types used | `ingest`, `analyze`, `fingerprint`, `tag`, `route` |

| Track field | Meaning |
|-------------|---------|
| `genre` / `subgenre` | Set at TAG (MusicBrainz + embedded); shown in dashboard |
| `needs_metadata_review` | Tag confidence below threshold or no match |
| `tagged_at` | Tag job completed (idempotent skip) |

---

## Operational notes

### AcoustID API key

1. Register at https://acoustid.org/new-application
2. Set `DJ_ACOUSTID_API_KEY` in `.env`

Without a key, tagging uses embedded ID3/Vorbis tags and filename parsing (`Title - Artist` or `Artist - Title`). **Genre/subgenre** from MusicBrainz require a key and a successful AcoustID match.

### Try renaming

1. Drop `Wonderwall - Oasis.mp3` into `data/watch/` (basename may be title–artist or artist–title).
2. Let the pipeline run through `TAG`.
3. Check `data/processing/` then `data/ready/` — file should be `Wonderwall - Oasis (Original Mix).mp3` (when metadata resolves).

### Watch folder lifecycle

- When a track is routed to **`ready/`** (or **Approve** from review), the copy in **`watch/`** is deleted — the library file in `ready/` is canonical.
- Tracks in **`review/`** keep the watch copy until you approve or reset.
- **Reset** with no watch file: moves the `ready/` or `review/` library copy back to the original `source_path` under watch, then re-runs ingest.

Restart **API**, **worker**, **watcher**, and **frontend** after code changes.

---

## Deferred (later phases)

- MusicBrainz Picard CLI in Docker (pyacoustid used instead; Python orchestrates pipeline)
- Artwork embed from Cover Art Archive
- Manual duplicate resolution — [PHASE5.md](./PHASE5.md)
- Backlog `POST /queue/tag-backlog` — Phase 5c in [PHASE5.md](./PHASE5.md)

---

## Exit criteria (Phase 4)

- [x] `pytest` green; rename + tag tests
- [x] Pipeline: `FINGERPRINT → TAG → ROUTE`
- [x] Renamed file in `ready/` uses `Title - Artist (Mix).ext`
- [x] Low-confidence / no-match tracks route to `review/` when flagged
- [x] Settings UI: naming template + confidence threshold
- [x] Genre/subgenre via MusicBrainz; WAV/AIFF ID3 tagging; editable artist/title; format/quality/bitrate in UI; loudness + quality gates in Settings
- [x] Docs updated: PHASE4, README, deploy troubleshooting

---

## References

- [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md)
- [PHASE3.md](./PHASE3.md)
- [ROADMAP.md](./ROADMAP.md)
