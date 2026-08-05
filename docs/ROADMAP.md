# Implementation roadmap

Phased delivery aligned with [dj-library-pipeline-spec.md](./dj-library-pipeline-spec.md).

| Phase | Doc | Status | Summary |
|-------|-----|--------|---------|
| 1 | [PHASE1.md](./PHASE1.md) | **Complete** | Watch folder, queue, ingest → `processing/` |
| 2 | [PHASE2.md](./PHASE2.md) | **Complete** | Analysis (LUFS, BPM/key), loudness routing |
| 3 | [PHASE3.md](./PHASE3.md) | **Complete** | Chromaprint fingerprints, duplicate detection |
| 4 | [PHASE4.md](./PHASE4.md) | **Complete** | AcoustID tagging, **metadata-based renaming** |
| 5 | [PHASE5.md](./PHASE5.md) | **Complete (5a)** | Duplicate resolution UI, `POST /duplicates/resolve` |
| 6 | [PHASE6.md](./PHASE6.md) | **In progress (6a)** | Docker on Raspberry Pi (images, compose, deploy docs) |
| 7+ | [PHASE6.md](./PHASE6.md#backlog-from-earlier-phases) | Planned | 5b–5d backlog, logs, metrics |

---

## Current pipeline (after Phase 5)

```text
watch / POST /queue/rescan
    → INGEST
    → ANALYZE      (ffmpeg loudness + Essentia BPM/key in Docker)
    → FINGERPRINT  (fpcalc → duplicate groups)
    → TAG          (AcoustID / tags / filename → rename in processing/)
    → ROUTE        (ready/ vs review/ for preferred copies)
```

| Destination | When |
|-------------|------|
| `processing/` | After ingest; renamed after TAG |
| `ready/` / `review/` | Preferred copy; passes loudness, quality, and metadata gates |
| `review/` | Too quiet, high peak, below min quality, low-confidence / missing metadata, or manual approval pending |
| `duplicates/<fingerprint_hash>/` | Non-preferred duplicate (same fingerprint) |

**Watch folder:** drop zone only. When a track reaches `ready/` or `duplicates/`, its watch copy is deleted; tracks in `review/` keep the watch file until approve. SQLite retains all track rows and fingerprints for dedup — see [PHASE4 § Watch folder lifecycle](./PHASE4.md#watch-folder-lifecycle).

**Filenames in `ready/`:** `Title - Artist (Mix).ext` after Phase 4 TAG job.

### Dashboard pipeline steps

The API exposes `pipeline_stage` on each track and `by_pipeline_stage` in `track_summary`. See [PHASE4.md § Dashboard pipeline steps](./PHASE4.md#dashboard-pipeline-steps-pipeline_stage) for the full table (Awaiting analyze → Analyzed → Awaiting tag → …).

---

## Dashboard & operations

| Doc | Audience |
|-----|----------|
| [README § Dashboard](../README.md#dashboard) | Actions, pipeline vs job queue, worker states, API summary |
| [deploy/README § Dashboard troubleshooting](../deploy/README.md#dashboard-troubleshooting-pi) | Pi: backlog, failed jobs, worker logs |

---

## System dependencies

| Tool | Phase | `scripts/install.sh` | Docker image |
|------|-------|----------------|--------------|
| ffmpeg | 2 | Manual | Yes |
| fpcalc (Chromaprint) | 3 | Manual | Yes (`libchromaprint-tools`) |
| Essentia | 2 | Docker image | BPM/key in `Dockerfile.backend`; optional for local dev |
| pyacoustid | 4 | pip (`backend`) | Yes |
| yt-dlp | 7 | pip (`backend`) | Yes |
| httpx (MusicBrainz search + genres) | 4 | pip (`backend`) | Yes |
| AcoustID API key | 4 | `.env` | `.env` / compose |

`scripts/install.sh` / `scripts/install.py` set up Python, Node, folders, SQLite, and `.env` only.

---

## Phase snapshots

### Phase 4 (metadata & dashboard)

- **Backend:** `metadata/` (AcoustID, MusicBrainz search + genres with release/artist fallback, WAV/AIFF ID3 tags), `tag_service`, `genre_backfill_service`, `track_metadata_service` (genre re-resolve on edit), `track_lifecycle_service` (approve + genre backfill), `pipeline_stage` on track responses
- **Frontend:** tracks table — editable artist/title, genre/subgenre, **pipeline step chips**, format/quality/bitrate (sortable), loudness badges; dashboard **Genre backfill** action; Settings — tagging, loudness gates, quality gates
- **API:** `PATCH /tracks/{id}/metadata`, `POST /tracks/{id}/confirm-review`, `POST /queue/genre-backfill`; `pipeline_stage` + `by_pipeline_stage` on pipeline snapshot
- **Tests:** run `make test` for current counts

### Phase 3

- **Backend:** `backend/app/fingerprint/`, duplicate groups
- **API:** `GET /duplicates`
- **Frontend:** duplicate groups card

---

## Active work

**Phase 6a** — Docker deployment on Pi: see [PHASE6.md](./PHASE6.md). README documents `docker compose up`, registry push/pull, and volume layout.

## Backlog (not in Phase 6a)

Full table: [PHASE6.md § Backlog from earlier phases](./PHASE6.md#backlog-from-earlier-phases).

| Item | Target |
|------|--------|
| Duplicate compare + waveforms | Phase 7a (was 5b) |
| Tag backlog + scheduler retries | Phase 7b (was 5c) |
| Loudness / duplicate settings UI | Phase 7c (was 5d) — **loudness + quality gates done**; duplicate-rule toggle still open |
| Picard/artwork, MusicBrainz editor submit on Approve, `GET /logs`, CPU/RAM dashboard | Phase 8+ |
