# Anonymized .alog test fixtures

Golden fixtures for the `alog_core` parser/indexer. Each file is an
anonymized copy of one roast log from the real Artisan corpus (the
read-only `Artisan/logs` folder next to this repo; originals were never
modified). One file was chosen per Artisan version present in the corpus.

## Versions represented

| Fixture | Artisan version | Roast date (ISO) | Notes |
|---|---|---|---|
| `v2.4.6_2021-11-19_multiline.alog` | 2.4.6 | 2021-11-19 | French locale (`etypes` = Air/Tambour/Vanne/Bruleur); pretty-printed multi-line pydump variant; CHARGE/FCs/DROP marked, DRY not marked |
| `v2.6.0_2022-09-16.alog` | 2.6.0 | 2022-09-16 | 21 events; first Windows-recorded generation in the corpus |
| `v2.8.2_2023-04-09.alog` | 2.8.2 | 2023-04-09 | CHARGE/FCs/DROP marked, DRY not marked |
| `v2.10.0_2024-04-02.alog` | 2.10.0 | 2024-04-02 | first 2.10.x generation in the corpus |
| `v2.10.4_2024-08-03.alog` | 2.10.4 | 2024-08-03 | `roastUUID` matches `UUID_A` used in the M2a store tests |
| `v3.2.0_2026-07-23.alog` | 3.2.0 | 2026-07-23 | CHARGE/DRY/FCs/DROP all marked |
| `v4.2.0_2026-10-04.alog` | 4.2.0 | 2026-10-04 | v4 key set (`hash`, `signature`, `bbp_*`, PID config); CHARGE/DRY/FCs/DROP all marked |

Together these exercise: single-line and multi-line pydump formatting,
French- and English-locale `etypes`, missing-DRY and full marker sets,
empty and populated event lists, and the key-set drift from 151 (2.4.6)
to 196 (4.2.0) keys.

## Anonymization applied

The copies were redacted textually, so every structural byte (keys, list
layout, series data, markers, formatting) is unchanged from the original.
Each copy was programmatically diffed against its parsed original to
guarantee that only the fields below changed:

- `backgroundpath`: every absolute local path (which contained usernames,
  e.g. `C:/Users/<name>/Jottacloud/Kawa/...`) replaced with the literal
  string `<redacted>`. The key itself is preserved.
- `title`, `beans`: a roaster-machine nickname replaced with `anon`
  (case-insensitive).
- No operator names, email addresses, or machine serials were present in
  the selected originals: `operator` and `organization` are empty strings
  in all seven files, and `machinesetup`/`devices` contain only generic
  Phidget hardware descriptors (`VINT TMP1101 2xTC`,
  `Phidget TMP1101 4xTC 01`).
- Values left as-is because they are not identifying and are needed for
  realistic parsing: `roastUUID`, `backgroundUUID` (random Artisan UUIDs),
  v4.x `hash`/`signature` integrity strings, roast timestamps, and coffee
  origin names in titles/beans.
- Fixture filenames were renamed to neutral
  `v<version>_<roast-date>.alog` names; the original corpus filenames are
  not recorded here because they embed the same nickname.
