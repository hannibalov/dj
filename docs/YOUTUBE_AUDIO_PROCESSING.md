# YouTube download — audio processing

How the pipeline transforms audio when you use **Download from YouTube** on the dashboard.

**Code:** `backend/app/download/youtube.py`, `backend/app/download/linear_gain.py`

---

## Summary

| Goal | Approach |
|------|----------|
| Best source from YouTube | yt-dlp `bestaudio/best` |
| DJ-friendly file format | 320 kbps MP3, 44.1 kHz |
| Tags & artwork | yt-dlp embed metadata + thumbnail |
| **Level matching (club-ish)** | **Uniform linear gain** toward **-9 LUFS** — **not** dynamic compression |

We **do not** use ffmpeg `loudnorm` anymore. `loudnorm` changes gain over time (quieter sections get boosted more than loud sections), which sounds like “only parts of the song got louder” and reshapes dynamics.

Instead we **measure** the track once, compute **one dB value**, and apply **`volume=XdB`** to the **entire file** so every sample is multiplied by the same factor. Relative dynamics between sections are preserved.

---

## Processing stages (in order)

### 1. Download & decode (yt-dlp)

- **Input:** YouTube URL (single video; playlists ignored).
- **Format selection:** `bestaudio/best` — highest-quality audio stream YouTube exposes (often Opus or AAC in WebM/M4A).
- **No video** is kept.

### 2. Transcode to MP3 (yt-dlp → ffmpeg)

- **Codec:** `libmp3lame`
- **Bitrate:** 320 kbps CBR (`320K`)
- **Sample rate:** 44.1 kHz (`-ar 44100`)
- **Filters on this step:** **none** (no loudnorm, no EQ, no compression)

This step is a straight decode → encode. YouTube’s lossy source limits how much “real” quality exists; 320k avoids an extra quality loss vs lower MP3 rates.

### 3. Metadata & thumbnail (yt-dlp)

- **ID3 tags:** artist, title (parsed from uploader/channel + title)
- **Cover art:** YouTube thumbnail embedded as album art (JPEG)

### 4. Uniform level boost (pipeline — `linear_gain.py`)

After the file lands in the watch folder:

1. **Measure** integrated loudness and true peak with ffmpeg **`ebur128`** (same family of meter used elsewhere in the pipeline).
2. **Compute one gain value in dB:**
   - `gain_for_lufs = target_lufs - measured_lufs` (default target **-9 LUFS**)
   - If `gain_for_lufs ≤ 0`, **no change** (already loud enough — we never turn tracks down).
   - If boosting would push true peak above **-0.5 dBTP**, use the **smaller** gain so peaks stay under that ceiling (avoids clipping; still linear, not multi-band compression).
3. **Apply** ffmpeg **`volume={gain}dB`** to the **whole file**.
4. Re-encode to 320k MP3 at 44.1 kHz, **copy existing ID3 metadata** (`-map_metadata 0`).

If the required gain is below **0.05 dB**, the file is left unchanged (avoid a useless re-encode).

---

## What we intentionally do **not** do

| Technique | Why not |
|-----------|---------|
| **`loudnorm`** | Dynamic normalization — different gain at different times; changes the “shape” of the track |
| **Multiband compression / limiting** | Alters punch and dynamics; not constant gain |
| **Attenuating loud tracks** | Only **boost** quiet material; hot masters are left as-is |
| **EQ / stereo widening** | Not part of download processing |
| **Upsampling tricks** | Cannot create detail YouTube did not ship |

---

## Constants (club-ish defaults)

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `CLUB_TARGET_LUFS` | **-9** | Integrated loudness we boost toward |
| `CLUB_PEAK_CEILING_DB` | **-0.5 dBTP** | Max true peak after boost |
| MP3 bitrate | **320 kbps** | Matches pipeline quality gate |
| Sample rate | **44100 Hz** | Standard DJ library rate |

These align with the analyzer’s note that club masters often sit around **-9 to -14 LUFS**. Downloads are pushed toward the **hot** end without dynamic processing.

---

## After download

The file follows the normal pipeline:

```text
watch/ → INGEST → ANALYZE → FINGERPRINT → TAG → ROUTE → ready/ or review/
```

**ANALYZE** measures LUFS again for routing gates (default: below **-18 LUFS** → `review/`). Boosted downloads should usually pass the “too quiet” gate.

**Bitrate gate:** 320 kbps MP3 should pass the default **320 kbps** minimum.

---

## Operational notes

- **Double MP3 encode:** When linear gain is applied, the file is transcoded a second time (after yt-dlp’s first MP3). This is the tradeoff for measuring loudness on the actual MP3 before boosting. Gain is skipped when unnecessary.
- **Source ceiling:** A quiet YouTube rip cannot become a true -9 LUFS **master** if peak headroom caps the linear gain — we prefer **no clipping** over hitting the LUFS target exactly.
- **Worker required:** Download jobs run in the worker container; ffmpeg and yt-dlp must be on `PATH` (included in the backend Docker image).

---

## Changing behavior

Edit constants in `backend/app/download/linear_gain.py` (`CLUB_TARGET_LUFS`, `CLUB_PEAK_CEILING_DB`) or transcode settings in `backend/app/download/youtube.py`.

If you need **true two-pass** EBU measurement before gain, that would be a separate enhancement; current design uses the same integrated LUFS summary `ebur128` already used at ANALYZE time.
