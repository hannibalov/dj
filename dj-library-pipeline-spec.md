
# DJ Library Automation Pipeline

## Overview

A fully automated self-hosted DJ library ingestion and organization platform designed for Raspberry Pi 4 and Docker deployment.

The system should:

- Watch a synced Nextcloud music folder
- Wait until files are fully synced and stable
- Analyze tracks for:
  - BPM
  - Key
  - Loudness
  - Energy
  - Bitrate / quality
- Detect duplicates
- Keep the best versions
- Preserve FLAC + MP3 variants when desired
- Tag metadata automatically
- Rename files consistently
- Organize tracks into a clean DJ library
- Prepare tracks for Rekordbox
- Expose configuration and monitoring through a Vue3 + Vuetify UI
- Run continuously inside Docker
- Be resource-limited and safe for Raspberry Pi 4
- Be fully fire-and-forget

---

# Core Requirements

## Technology Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- watchdog
- structlog
- mutagen

### Frontend
- Vue3
- Vite
- TypeScript
- Pinia
- Vuetify
- Vitest

### Audio Analysis
- Essentia
- ffmpeg / ffprobe
- Chromaprint / fpcalc
- pyacoustid

### Testing
- pytest
- Vitest

### Containerization
- Docker
- docker compose

---

# Development Philosophy

## TDD Required

Cursor should generate all backend and frontend code using Test Driven Development.

### Backend
- pytest
- fixtures
- integration tests
- service-level tests

### Frontend
- Vitest
- component tests
- composables tests
- store tests

All new modules should:
1. Define interfaces/types first
2. Create tests first
3. Implement functionality after tests

---

# High-Level Architecture

```text
Mac / Other Devices
        ↓
Nextcloud Sync
        ↓
Watch Folder
        ↓
Stability Detection
(wait until sync complete)
        ↓
SQLite Queue
        ↓
Worker Pipeline
        ↓
Audio Analysis
(Essentia + ffmpeg)
        ↓
Fingerprinting
(Chromaprint)
        ↓
Duplicate Resolution
        ↓
Metadata Matching
(MusicBrainz Picard / AcoustID)
        ↓
Tagging + Renaming
        ↓
Routing
        ↓
READY / REVIEW / DUPLICATES / ARCHIVE
        ↓
Rekordbox Import Folder
```

---

# Important Principles

## Never Process Files In Place

Files must never be processed directly inside Nextcloud folders.

Correct flow:

```text
Nextcloud
    ↓ copy
Processing Workspace
    ↓
Final Library
```

This avoids:
- partial sync issues
- file locks
- re-upload loops
- corruption
- unstable files

---

## Queue-Based Processing

Do NOT process files directly from filesystem events.

Correct architecture:

```text
watcher → queue → workers
```

This ensures:
- crash safety
- restart safety
- resumable jobs
- scalability
- deterministic behavior

---

# Docker-First Architecture

## Goal

The entire application should be distributable as:

```bash
docker compose up -d
```

with all dependencies already preinstalled.

No manual dependency installation should be required outside Docker.

---

# Docker Services

```text
services:
  api
  worker
  watcher
  scheduler
  frontend
```

---

# Docker Requirements

## Preinstalled Dependencies

The Docker image must already include:

- Python
- ffmpeg
- ffprobe
- Essentia
- Chromaprint
- fpcalc
- AcoustID support
- MusicBrainz Picard
- SQLite
- all Python dependencies
- Node dependencies for frontend build

---

# Resource Limiting

The system must support configurable CPU and RAM limits.

Example:

```yaml
cpus: 1.0
mem_limit: 1g
```

Recommended:
- single worker
- nice=10
- CPUQuota via Docker/systemd

Speed is NOT a priority.
Correctness and stability are the priority.

---

# Folder Configuration

## IMPORTANT

All folders must be configurable from the UI.

Paths may be:
- absolute
- relative

Configuration should live in:
- SQLite database
OR
- config file

Whichever is simpler and more maintainable.

---

# Configurable Paths

The UI must allow configuring:

```text
watch_folder
incoming_folder
processing_folder
ready_folder
review_folder
duplicates_folder
archive_folder
failed_folder
logs_folder
rekordbox_export_folder
```

---

# Frontend Requirements

## Stack

- Vue3
- Vite
- TypeScript
- Pinia
- Vuetify

Tailwind should NOT be used.

---

# Frontend Features

## Dashboard

Display:
- queue length
- CPU usage
- RAM usage
- processing status
- latest imports
- duplicate groups
- worker status

---

## Settings UI

Configurable:
- folder paths
- bitrate thresholds
- loudness thresholds
- duplicate rules
- CPU limits
- naming conventions
- auto-routing rules

---

## Duplicate Resolution UI

Allow:
- compare files
- waveform previews
- manual keep/remove decisions

---

# Audio Analysis

## Essentia

Primary analysis engine.

Used for:
- BPM
- key
- energy
- loudness
- spectral descriptors
- danceability heuristics

Speed is not important.
Accuracy is preferred.

Raspberry Pi 4 compatibility is required.

---

# Loudness Analysis

Use:
- ffmpeg
- Essentia

Suggested rules:

## Too Quiet

```text
Integrated LUFS < -18
```

## Excessive peak (review gate)

```text
True Peak > 3.0 dBTP   (default; configurable in Settings / DJ_REVIEW_TRUE_PEAK_DB)
```

Decoded MP3 often reports inter-sample peaks above 0 dBTP without audible distortion. Use a permissive threshold for MP3-heavy libraries; tighten for lossless QC if needed.

Violations (loudness or quality gates):
→ move to REVIEW

---

# BPM Detection

Store:
- bpm
- confidence

---

# Key Detection

Store:
- musical key
- scale
- Camelot notation
- confidence

Example:

```text
A minor
8A
```

---

# Energy Detection

Generate a DJ-friendly score:

```text
0-100
```

Suggested categories:

```text
0-20 ambient
20-40 warmup
40-60 groove
60-80 peak
80-100 aggressive
```

---

# Duplicate Detection

## Exact Duplicates

Use:
- Chromaprint
- fpcalc
- AcoustID

---

# Preferred Version Rules

Priority:

1. FLAC
2. WAV
3. AIFF
4. 320kbps MP3
5. lower bitrate MP3

---

# Important Rule

If formats differ:

```text
FLAC + MP3
```

keep BOTH by default.

The user should later be able to configure this behavior.

---

# Duplicate Folder Structure

```text
duplicates/
  fingerprint_hash/
    track.flac
    track.mp3
```

---

# Metadata Matching

## MusicBrainz Picard

Use for:
- metadata enrichment
- tagging
- naming
- artwork
- AcoustID lookup

Picard should NOT orchestrate the pipeline.

Python services orchestrate the workflow.

---

# Naming Convention

Library filenames after tagging (Rekordbox import folder):

```text
Title - Artist (Mix).ext
```

Examples:

```text
Generate - Eric Prydz (Original Mix).flac
Cola - CamelPhat (Club Mix).mp3
Wonderwall - Oasis (Original Mix).mp3
```

Watch-folder drops may use either `Title - Artist` or `Artist - Title`; the pipeline resolves artist/title for tags, then renames to **song first** in `ready/`.

Default template: `{title} - {artist} ({mix}){ext}` (configurable in Settings).

---

# Rekordbox Integration

Only import:

```text
/data/ready
```

into Rekordbox.

Rekordbox remains responsible for:
- beatgrids
- waveforms
- hot cues

The system should not attempt to replace Rekordbox analysis.

---

# Suggested Runtime Structure

```text
/data
  /incoming
  /processing
  /ready
  /review
  /duplicates
  /archive
  /failed
  /logs
```

---

# Database

## SQLite

Use SQLite for:
- queue management
- track metadata
- fingerprints
- duplicates
- settings
- processing history
- retries

Suggested tables:

```text
tracks
jobs
fingerprints
analysis_results
duplicates
settings
logs
```

---

# REST API

Suggested endpoints:

## Settings

```text
GET /settings
PUT /settings
```

## Queue

```text
GET /queue
POST /queue/rescan
```

## Tracks

```text
GET /tracks
GET /tracks/:id
```

## Duplicates

```text
GET /duplicates
POST /duplicates/resolve
```

## Logs

```text
GET /logs
```

---

# Suggested Backend Structure

```text
backend/
  app/
    api/
    workers/
    analysis/
    fingerprint/
    metadata/
    router/
    db/
    models/
    services/
    utils/
```

---

# Suggested Frontend Structure

```text
frontend/
  src/
    components/
    pages/
    stores/
    composables/
    services/
```

---

# Installer Requirements

Even though Docker is preferred, create installer scripts for development environments.

Supported installers:

```text
install.sh
install.py
```

Responsibilities:
- dependency validation
- environment creation
- folder initialization
- config generation
- database initialization

---

# Logging

Use structured JSON logs.

Suggested libraries:
- structlog
- logging

Log categories:

```text
WATCHER
ANALYZER
TAGGING
DUPLICATES
ROUTER
API
```

---

# Future Research Section

## Music Download Source Integrations

Future versions may integrate with legal music download providers.

This requires research.

Potential integrations:
- Beatport
- Bandcamp
- Traxsource
- Juno Download

Possible future features:
- automatic imports
- metadata enrichment
- purchase history synchronization
- smart collection building

This section is exploratory only and should NOT be implemented yet.

Research tasks:
- API availability
- authentication methods
- rate limits
- legal considerations
- metadata quality
- download permissions

---

## MusicBrainz community metadata (exploratory)

When the user **Approves** a review track with corrected artist/title, future versions may:

- Link to the MusicBrainz recording page (`musicbrainz_recording_id` is stored when search or AcoustID finds a match)
- Optionally submit tag/genre votes via the MusicBrainz editor API (requires user editor credentials — not read-only)

This complements the current **read-only** MusicBrainz integration at TAG and Approve (artist/title search, genre lookup). Implementation deferred.

---

# Long-Term Ideas

## Smart Playlist Generator

Generate playlists dynamically using:
- BPM ranges
- Camelot compatibility
- energy ranges
- genre tags

---

## AI Recommendations

Potential future:
- vibe clustering
- similar track recommendations
- automatic crate generation

---

# Final Goal

A fully automated self-hosted DJ ingestion platform that:
- continuously watches music drops
- intelligently analyzes tracks
- automatically organizes the library
- minimizes manual intervention
- produces a clean Rekordbox-ready collection
- runs reliably on Raspberry Pi 4
- is maintainable and extensible long-term
