# Phase 3 — Fingerprinting & duplicate detection

**Status: complete** (May 2026)

**Prerequisite:** Phase 2 — [PHASE2.md](./PHASE2.md). **Next:** [PHASE5.md](./PHASE5.md) (duplicate resolution).

---

## Goal

Identify duplicate and near-duplicate tracks using audio fingerprints, persist groups in SQLite, and route extra copies to `duplicates/<fingerprint_hash>/` per spec—without auto-deleting files.

---

## What was delivered

### Pipeline chain

```text
INGEST → ANALYZE → FINGERPRINT → ROUTE
                      ↓
              duplicates/<hash>/  (non-preferred copies)
              ready/ or review/   (preferred copy, loudness rules)
```

- `AnalysisService` enqueues `FINGERPRINT` (not `ROUTE`) after analyze
- `FingerprintService` runs Chromaprint via `fpcalc`, stores hash, resolves duplicates, then enqueues `ROUTE` for preferred copies only

### Backend — fingerprinting

| Area | Location |
|------|----------|
| fpcalc wrapper | `backend/app/fingerprint/chromaprint.py` |
| Version priority (FLAC→WAV→AIFF→MP3) | `backend/app/fingerprint/version_priority.py` |
| Format/bitrate helpers | `backend/app/utils/audio_format.py` |
| Job handler | `backend/app/services/fingerprint_service.py` |
| Duplicate groups API | `backend/app/services/duplicate_service.py` |

**Tables:** `fingerprints`, `duplicate_groups`

### Backend — duplicate rules

- Exact match on SHA-256 of Chromaprint fingerprint string
- **Preferred version** per format family: FLAC → WAV → AIFF → 320k MP3 → lower MP3
- **FLAC + MP3:** both families can have a preferred copy (keep both by default)
- Non-preferred copies → `duplicates/<fingerprint_hash>/`, `TrackStatus.DUPLICATE`

### Backend — queue & routing

| Area | Location |
|------|----------|
| Fingerprint dedup | `backend/app/services/queue_service.py` |
| Route skips `DUPLICATE` | `backend/app/services/routing_service.py` |
| Worker | `backend/app/workers/main.py` |

### Backend — API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/duplicates` | List duplicate groups (2+ members) with format/bitrate |
| POST | `/duplicates/resolve` | Stub — manual resolution in a later phase |

### Frontend

| Feature | Location |
|---------|----------|
| Duplicate groups card | `frontend/src/components/DuplicateGroupsCard.vue` |
| Types + API client | `frontend/src/types/duplicate.ts`, `duplicateService.ts` |
| Dashboard integration | `DashboardPage.vue` (refreshes on WebSocket snapshot) |

### Tests

**Backend (28):** `test_version_priority`, `test_fingerprint_service`, `test_duplicate_detection`, `test_fingerprint_queue_dedup`, plus Phase 1–2 tests.

**Frontend (8):** includes `duplicateService.test.ts`.

```bash
make test
make lint
```

---

## Track & job lifecycle (Phase 3)

| Track status | Meaning |
|--------------|---------|
| `duplicate` | Non-preferred copy in `duplicates/<hash>/` |
| `ready` / `review` | Preferred copy after loudness routing |

| Job types used | `ingest`, `analyze`, `fingerprint`, `route` |

---

## Operational notes

### fpcalc (Chromaprint)

**Not installed by `install.sh`** — install on the host before running the worker locally.

```bash
# macOS
brew install chromaprint   # provides fpcalc

# Debian/Ubuntu
sudo apt install libchromaprint-tools
```

Verify: `fpcalc -version`

Docker: `libchromaprint-tools` is in `docker/Dockerfile.backend` (includes `fpcalc`).

You also need **ffmpeg** for the analyze step (`brew install ffmpeg` / `apt install ffmpeg`). Neither ffmpeg nor fpcalc is validated by `install.py` today.

Restart **API**, **worker**, **watcher**, and **frontend** after code changes.

### Try duplicates

1. Drop two copies of the same track (e.g. 128k and 320k MP3) into `data/watch/`.
2. Let the pipeline run through fingerprint.
3. Preferred copy → `data/ready/` or `data/review/`; other → `data/duplicates/<hash>/`.
4. Dashboard **Duplicate groups** section lists grouped tracks.

---

## Deferred (Phase 5+)

- ~~MusicBrainz / Picard tagging~~ — [PHASE4.md](./PHASE4.md)
- ~~**File renaming**~~ — [PHASE4.md](./PHASE4.md)
- Manual duplicate UI (waveforms, keep/remove) — [PHASE5.md](./PHASE5.md)
- `POST /duplicates/resolve` implementation — [PHASE5.md](./PHASE5.md)
- Re-evaluate older preferred copies when a better file arrives — [PHASE5.md](./PHASE5.md)

---

## Exit criteria (Phase 3)

- [x] `pytest` green; new fingerprint/duplicate tests
- [x] `npm test` + `make lint` green
- [x] Two identical/near-identical files → grouped in DB; non-preferred copy under `data/duplicates/<hash>/`
- [x] Preferred copy still flows through loudness routing to `ready/` or `review/`
- [x] Dashboard shows duplicate groups (minimal UI OK)
- [x] Docs updated: PHASE3 complete, ROADMAP, README

---

## References

- [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md)
- [PHASE2.md](./PHASE2.md)
- [PHASE4.md](./PHASE4.md)
