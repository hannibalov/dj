# Implementation roadmap

Phased delivery aligned with [dj-library-pipeline-spec.md](../dj-library-pipeline-spec.md).

| Phase | Doc | Status | Summary |
|-------|-----|--------|---------|
| 1 | [PHASE1.md](./PHASE1.md) | **Complete** | Watch folder, queue, ingest → `processing/` |
| 2 | [PHASE2.md](./PHASE2.md) | **Complete** | Analysis (LUFS, BPM/key), loudness routing |
| 3 | [PHASE3.md](./PHASE3.md) | **Complete** | Chromaprint fingerprints, duplicate detection |
| 4 | [PHASE4.md](./PHASE4.md) | **Complete** | AcoustID tagging, **metadata-based renaming** |
| 5 | [PHASE5.md](./PHASE5.md) | **Complete (5a)** | Duplicate resolution UI, `POST /duplicates/resolve` |
| 6 | [PHASE6.md](./PHASE6.md) | **In progress (6a)** | Docker on Raspberry Pi (images, compose, deploy docs) |
| 7+ | [PHASE6.md](./PHASE6.md#backlog-from-earlier-phases) | Planned | 5b–5d backlog, Essentia ARM, logs, metrics |

---

## Current pipeline (after Phase 5)

```text
watch / POST /queue/rescan
    → INGEST
    → ANALYZE      (ffmpeg loudness + optional Essentia)
    → FINGERPRINT  (fpcalc → duplicate groups)
    → TAG          (AcoustID / tags / filename → rename in processing/)
    → ROUTE        (ready/ vs review/ for preferred copies)
```

| Destination | When |
|-------------|------|
| `processing/` | After ingest; renamed after TAG |
| `ready/` / `review/` | Preferred copy; loudness OK and metadata confidence OK |
| `review/` | Too quiet, clipped, or low-confidence / missing metadata |
| `duplicates/<fingerprint_hash>/` | Non-preferred duplicate (same fingerprint) |

**Filenames in `ready/`:** `Title - Artist (Mix).ext` after Phase 4 TAG job.

---

## System dependencies

| Tool | Phase | `install.sh` | Docker image |
|------|-------|----------------|--------------|
| ffmpeg | 2 | Manual | Yes |
| fpcalc (Chromaprint) | 3 | Manual | Yes (`libchromaprint-tools`) |
| Essentia | 2 (optional) | Manual | Deferred on ARM/Pi |
| pyacoustid | 4 | pip (`backend`) | Yes |
| AcoustID API key | 4 | `.env` | `.env` / compose |

`install.sh` / `install.py` set up Python, Node, folders, SQLite, and `.env` only.

---

## Phase snapshots

### Phase 4 (latest)

- **Backend:** `backend/app/metadata/`, `tag_service`, tag columns on `tracks`, `raw_fingerprint` on `fingerprints`
- **Frontend:** artist/title columns, tagging settings
- **Tests:** 36 backend + frontend (`make test`)

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
| Loudness / duplicate settings UI | Phase 7c (was 5d) |
| Essentia on ARM, Picard/artwork, `GET /logs`, CPU/RAM dashboard | Phase 8+ |
