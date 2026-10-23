# M5 Review — artisan-companion release prep

**Date:** 2026-10-23
**Reviewer:** one-shot review agent (M5)
**Repo:** `C:\Users\guill\ai\coffee\artisan_companion_app`, branch `dev`
**Reviewed commits:** `aaf04e8` (MIT LICENSE), `a02c04c` (README/gallery/plan), `65589cb` (packaging) on top of `d6c4538`
**Constraints honored:** no commit, no push, no tags/releases; `src/`, `tests/`, `tests/fixtures/`, and the corpus `C:\Users\guill\ai\coffee\Artisan\logs` untouched (checksums/mtimes verified before and after); no server process left running (port 8000 verified free after every smoke test).

## Verdict

| # | Checklist item | Result |
|---|---|---|
| 1 | Packaging re-verification (fresh venv) | **PASS after 1 fix** — the wheel was missing the app's HTML assets (release blocker for any non-editable install); fixed in `pyproject.toml` and re-verified end-to-end (wheel + sdist + wheel-install smoke) |
| 2 | README accuracy (literal walkthrough) | **PASS after 3 fixes** — stale test count (282 → 298); the sample-data steps didn't work as written (empty library without `--logs-dir`); added `dev` extra mention |
| 3 | Sample gallery facts | **PASS after 1 fix** — one incorrect claim ("first Windows-recorded generation" on v2.10.0; the corpus shows it belongs to 2.6.0); every other row/claim verified against the fixtures, the corpus, and `research/m0-roundtrip.md` |
| 4 | License consistency | **PASS** — MIT consistent across `LICENSE`, `pyproject.toml`, README, and the built wheel |
| 5 | Disclaimer | **PASS** — wording adequate and correctly placed; no change needed |
| 6 | Plan status | **PASS after 3 fixes** — stale HEAD ref removed; repo-layout package list and tech-stack row aligned with what actually shipped |
| 7 | Test suite | **PASS** — 298 passed, 1 skipped (before and after my `pyproject.toml` change); fixture checksums and corpus untouched |
| 8 | CI check | **Gap found** — CI never built/installed the package, which is exactly how the wheel bug slipped through; added a minimal `packaging` job; YAML validated and the check logic simulated locally |
| 9 | Git hygiene | **PASS** — clean start; the three M5 commits sit on `d6c4538`; branch is ahead of `origin/dev` by 3 (unpushed — expected, orchestrator pushes after review); one stray venv directory in the repo root reported |

---

## 1. Packaging re-verification (from scratch)

A **fresh** venv was created (the spike's `m5pkg-venv` was not reused), at `C:\Users\guill\AppData\Local\Temp\m5review-venv`.

### 1.1 Fresh venv + editable install with the `app` extra

```bash
py -3 -m venv /c/Users/guill/AppData/Local/Temp/m5review-venv
# -> Python 3.13.15

cd /c/Users/guill/ai/coffee/artisan_companion_app
/c/Users/guill/AppData/Local/Temp/m5review-venv/Scripts/python.exe -m pip install -e ".[app]"
# -> Successfully installed artisan-companion-0.1.0 fastapi-0.161.1 uvicorn-0.54.0
#    (plus anyio, starlette, pydantic, click, h11, idna, ...)
```

### 1.2 Import check from a different cwd

```bash
cd /c/Users/guill/AppData/Local/Temp
/c/Users/guill/AppData/Local/Temp/m5review-venv/Scripts/python.exe \
  -c "import alog_core, store, sync, app; print('imports OK')"
# -> imports OK: alog_core store sync app
```

### 1.3 Console script

```bash
ls /c/Users/guill/AppData/Local/Temp/m5review-venv/Scripts/artisan-companion*
# -> artisan-companion.exe

python -c "from importlib.metadata import entry_points; \
  print([e for e in entry_points(group='console_scripts') if e.name=='artisan-companion'][0])"
# -> EntryPoint(name='artisan-companion', value='app.__main__:main', group='console_scripts')
```

### 1.4 Server smoke tests (editable install)

Both entry points were started, curled, and killed within a single shell command; port 8000 was verified free after each kill.

| Entry point | Command | Result |
|---|---|---|
| Console script | `artisan-companion --logs-dir tests/fixtures/alogs --sensory-dir <tmp>` | `GET /` → 200 HTML; `GET /api/roasts` → 200; `GET /viewer?uuid=41bc…c495` → 200 HTML; `GET /api/roasts/41bc…c495/profile` → 200; uvicorn log: `Uvicorn running on http://127.0.0.1:8000` |
| Module | `python -m app --logs-dir tests/fixtures/alogs --sensory-dir <tmp>` | same endpoints → 200; `/api/roasts` listed **7 roasts** (all fixtures); profile returned `artisan_version: 2.10.4`, title `Abricot 5`, markers `CHARGE/DROP/FCs/TP`, 9 events |

Host/port match `src/app/main.py` (`uvicorn.run(..., host="127.0.0.1", port=8000)`) and the README's `http://127.0.0.1:8000`.

### 1.5 Wheel build — **bug found**

```bash
python -m pip wheel --no-deps -w <tmp> .
# -> artisan_companion-0.1.0-py3-none-any.whl
```

Wheel contents (before fix): all four packages present (`alog_core`, `app`, `store`, `sync` — every `.py`), `entry_points.txt` (`artisan-companion = app.__main__:main`), `licenses/LICENSE`, `top_level.txt` — **but `app/frontend.html` and `app/viewer.html` were missing.** The stale `src/artisan_companion.egg-info/SOURCES.txt` had already hinted at this (no MANIFEST.in, no package-data rule).

End-to-end proof: a second fresh venv (`m5review-venv2`) with the wheel installed (non-editable) served:

```
GET /                  -> 200  <html><body><h1>Frontend not found</h1></body></html>
GET /viewer?uuid=...   -> 404  <html><body><h1>Viewer not found</h1></body></html</n```

`site-packages/app/` contained only the `.py` files. Root cause: `src/app/main.py` reads `Path(__file__).parent / "frontend.html"` / `"viewer.html"`, and setuptools does not include package data without an explicit rule. Editable installs worked only because they read from the source tree — so the spike's editable-only verification missed it. **This would have broken every wheel/sdist install (i.e., the planned GitHub release).**

### 1.6 Fix + re-verification

`pyproject.toml` (2 lines added):

```toml
[tool.setuptools.package-data]
app = ["*.html"]
```

Re-built and re-verified:

```bash
python -m pip wheel --no-deps -w <tmp> .
# wheel now contains: app/frontend.html, app/viewer.html + all four packages

# venv2 force-reinstalled with the fixed wheel:
GET /                  -> 200  <!DOCTYPE html> ... <title>Artisan Companion - Sensory Editor</title> ...
GET /viewer?uuid=...   -> 200  <!DOCTYPE html> ... (real viewer page)
# grep "Frontend not found" -> absent; site-packages/app/ now has frontend.html + viewer.html
```

sdist also verified (`python -m build --sdist`): `artisan_companion-0.1.0.tar.gz` contains `src/app/frontend.html`, `src/app/viewer.html`, all four packages' sources, `LICENSE`, `README.md`, `pyproject.toml`.

Wheel `METADATA` headers checked: name `artisan-companion`, version `0.1.0`, `License: MIT`, `Requires-Python: >=3.11`, `Provides-Extra: app` (`fastapi>=0.100`, `uvicorn>=0.20`) and `dev` (`pytest`, `httpx`) — all match `pyproject.toml`.

## 2. README accuracy (literal walkthrough)

Followed Install/Run/"Try it with sample data" as a new user would:

- `pip install -e ".[app]"` from the repo root — works (1.1).
- `artisan-companion` and `python -m app` — both start the server on `http://127.0.0.1:8000` (1.4). Host/port match `src/app/main.py`.
- CLI flags `--logs-dir` / `--sensory-dir` and their defaults (`./logs` else cwd; `<logs-dir>/../sensory`) match `src/app/main.py`.
- Sample data: the repository does include 7 anonymized fixtures in `tests/fixtures/alogs/`, one per Artisan version 2.4.6–4.2.0 (verified: 2.4.6, 2.6.0, 2.8.2, 2.10.0, 2.10.4, 3.2.0, 4.2.0), and `docs/sample-gallery.md` exists.
- **Literal run of the old step 1 ("Install and run the app (as shown above)", i.e. no flags) from the repo root: `/api/roasts` returned 0 roasts.** `build_index` uses a non-recursive `logs.glob("*.alog")`, and the fixtures live in a subdirectory — so the documented flow showed an empty library and `/viewer?uuid=…` would 404. The gallery's own command (`artisan-companion --logs-dir tests/fixtures/alogs`) was run literally and lists all 7 roasts.
- Status blockquote said **282** tests passed; the suite (and the spike's own note: 282 + 16 packaging tests) is **298** passed / 1 skipped.
- Documentation table: all six linked files exist (`docs/feasibility-evaluation.md`, `docs/implementation-plan.md`, `docs/ui-spec.md`, `docs/sample-gallery.md`, `research/upstream-findings.md`, `research/m0-roundtrip.md`).
- "CI green": the three M5 commits are **unpushed** (`origin/dev` = `d6c4538`, `git log origin/dev..dev` shows the 3 M5 commits), so CI has not run on them yet; the claim reflects the last pushed state. Left as-is (it will be true once the orchestrator pushes and CI passes), noted here for transparency.

**Fixes applied to `README.md`:**
1. Status line: `282 tests passed` → `298 tests passed / 1 skipped`.
2. Sample-data section rewritten: run `artisan-companion --logs-dir tests/fixtures/alogs` (from the repo root), then open the viewer / browse the library; added a note that the sensory store defaults to `tests/fixtures/sensory/` (gitignored) and that `--sensory-dir` can relocate it.
3. Install section: added the `dev` extra (`pip install -e ".[app,dev]"`) for running the test suite.

## 3. Sample gallery facts

Every row/claim in `docs/sample-gallery.md` was cross-checked by parsing all 7 fixtures read-only (`ast.literal_eval`) and against `tests/fixtures/alogs/README.md`, `research/m0-roundtrip.md`, and a read-only scan of the 230-file corpus:

| Claim | Verified |
|---|---|
| 7 fixtures, one per Artisan version 2.4.6–4.2.0 | Yes (7 distinct versions) |
| 2.4.6: French locale, `etypes` = Air/Tambour/Vanne/Brûleur; multi-line pydump; CHARGE/FCs/DROP present, DRY not marked; 151 keys | Yes (`locale='fr'`, multiline, `timeindex=[29,0,276,…,348]`, 151 keys) |
| 2.6.0: 21 events; single-line; CHARGE/FCs/DROP marked | Yes (21 `specialevents`, markers CHARGE/FCs/DROP) |
| 2.8.2: CHARGE/FCs/DROP present, DRY not marked | Yes |
| 2.10.4: `roastUUID` matches `UUID_A` of the M2a store tests | Yes — `41bc74340a464d98a8156045b5bfc495` is both the fixture's `roastUUID` and `UUID_A` in `tests/test_sensory_store.py` |
| 3.2.0: full marker set CHARGE/DRY/FCs/DROP | Yes |
| 4.2.0: `hash` 64-hex, `signature` 128-hex, `bbp_*` + PID config keys, full markers, 196 keys | Yes (8 `bbp_*` keys, `pidKp/Ki/Kd/…` keys, 196 keys) |
| Key-set drift 151 → 196 | Yes (151/152/155/155/155/179/196 across versions) |
| Native sync table (pre-4.2: fields only; 4.2+: recompute `hash`, preserve `signature`; `.bak` always; SHA-256 over canonical JSON with int→float) | Yes — matches `research/m0-roundtrip.md` §6–7 and `src/sync/integrity.py` / `src/sync/writer.py` |
| Viewer claims (BT/ET, RoR, markers, phase shading, sensory panel, `artisan_version` in the metadata panel, library → `/viewer?uuid=` links) | Yes — verified in `src/app/viewer.html`, `src/app/frontend.html`, and live responses |
| **"First Windows-recorded generation in the corpus" (on v2.10.0)** | **No — incorrect.** Corpus scan: 2.4.6 = 56 files, all `Mac OS X`; 2.6.0 = 14 files, all `Windows` (the v2.6.0 fixture itself is `artisan_os='Windows'`). The first Windows-recorded generation is **2.6.0**, not 2.10.0. |

**Fix applied to `docs/sample-gallery.md`:** the incorrect claim on v2.10.0 (table row + per-version note) was replaced with a verified fact (first 2.10.x generation; key set drops `beansize` and adds `default_etypes` vs 2.8.2), and the true "first Windows-recorded generation in the corpus" note was moved to the 2.6.0 row/note (all 2.4.6 corpus files are Mac OS X). Also added the sensory-store location note to "How to View" (see §2).

Note: `tests/fixtures/alogs/README.md` carries the same incorrect "first Windows-recorded generation" note for v2.10.0 — it is under `tests/` and therefore off-limits for this review; see recommendations.

## 4. License consistency

- `LICENSE`: MIT License, `Copyright (c) 2026 gpotdevin` — matches the task's expectation.
- `pyproject.toml`: `license = { text = "MIT" }` + classifier `License :: OSI Approved :: MIT License`.
- `README.md`: "MIT — see [LICENSE](LICENSE)".
- Built wheel: `artisan_companion-0.1.0.dist-info/licenses/LICENSE` present; METADATA `License: MIT`.

Consistent everywhere. No change needed.

## 5. Disclaimer

README's `## Affiliation` section (placed at the end, after License):

> artisan-companion is an independent project. It is not affiliated with, endorsed by, or sponsored by Artisan (artisan-scope.org). 'Artisan' is a trademark of its respective owners. This project only reads and writes the public `.alog` file format.

Assessment: **adequate and correctly placed.** It covers non-affiliation/non-endorsement/non-sponsorship, the trademark attribution, and the factual scope (public file format only); the H1 also flags "(working title)", matching the plan's open decision ("keep `artisan-companion`, revisit branding before any public release"). No change needed.

## 6. Plan status (`docs/implementation-plan.md`)

- Milestones M0–M4 "Done", M5 "In progress" — consistent with reality (this review is part of M5).
- Open decisions: License **MIT** (LICENSE added) — consistent; Distribution **GitHub releases first** — consistent (nothing contradicts); Viewer tech **Canvas + SVG (vanilla JS)** — verified against `src/app/viewer.html` (`<canvas id="chartCanvas">` for BT/ET/RoR, `<svg class="radar-svg">` for the radar, zero external references in both HTML files); Project name **keep `artisan-companion`** with disclaimer — consistent with the README.
- **Fixes applied:**
  1. Status blockquote cited a stale `HEAD commit d6c4538` (three M5 commits have landed since, and the ref would go stale again on the next commit) → replaced with "M0–M4 complete; M5 (release prep) in progress."
  2. Repository-layout comment said `pyproject.toml # package: alog_core + app` → corrected to `# packages: alog_core, store, sync, app` (all four ship in the wheel).
  3. Tech-stack table still listed the undecided "Plotly or lightweight chart lib" for App/UI → updated to the shipped choice (FastAPI + vanilla-JS frontend, canvas charts, SVG radar, zero frontend dependencies), matching the resolved open decision.

## 7. Test suite + fixture/corpus integrity

```bash
py -3 -m pytest tests/ -q
# -> 298 passed, 1 skipped, 157 warnings in ~20s   (run twice: before and after the pyproject fix)
```

(The 157 warnings are pre-existing FastAPI `@app.on_event` deprecation warnings.)

- `tests/fixtures/alogs/` checksums (sha256 of all 7 `.alog` files + README) identical before and after all review activity — `git status` clean for that dir.
- Corpus `C:\Users\guill\ai\coffee\Artisan\logs`: 230 `.alog` files, newest mtime 2026-10-19 22:06 (before this session) — never modified.
- `tests/fixtures/sensory/*.sqlite` are untracked/gitignored (`*.sqlite`, `sensory/` in `.gitignore`); running the app per the docs writes there, which is why the README/gallery now document it.

## 8. CI check (`.github/workflows/test.yml`)

Existing `test` job: push/PR on `main`+`dev`, matrix 3.11/3.12/3.13, `pip install pytest httpx fastapi uvicorn`, `python -m pytest tests/ -q`. This covers the suite adequately — `tests/test_packaging.py` uses stdlib `tomllib` (3.11+), so it passes across the matrix, and `tests/conftest.py` makes `src/` importable without installing the package.

**Gap:** CI never installs or builds the package, so nothing would have caught the missing-HTML-assets wheel (§1.5). **Fix applied:** added a minimal `packaging` job (build sdist+wheel on 3.13, then assert the wheel contains the four packages' key files and `app/frontend.html` + `app/viewer.html`):

```yaml
  packaging:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install build
      - run: python -m build --wheel --sdist
      - run: |
          python -m zipfile -l dist/*.whl > wheel-contents.txt
          for f in alog_core/__init__.py store/__init__.py sync/__init__.py app/main.py app/frontend.html app/viewer.html; do
            grep -q "$f" wheel-contents.txt || { echo "MISSING from wheel: $f"; exit 1; }
          done
          echo "wheel contents OK"
```

Validated: the YAML parses (pyyaml), and the exact check logic was simulated locally against the fixed wheel (`wheel contents OK`). Live CI status could not be checked (no workflow-runs tool available; the M5 commits are unpushed anyway).

## 9. Git hygiene

- Start of review: `git status` clean, `git log --oneline -6` showed `65589cb`, `a02c04c`, `aaf04e8` on top of `d6c4538` — as expected.
- End of review: `git status` shows exactly the five intended file modifications (no commits/pushes made, per instructions):
  `pyproject.toml`, `README.md`, `docs/implementation-plan.md`, `docs/sample-gallery.md`, `.github/workflows/test.yml` (+ this report, untracked).
- `origin/dev` = `d6c4538`; the three M5 commits are local only (branch ahead by 3).
- **Stray artifact:** `UsersguillAppDataLocalTempm5pkg-venv/` — a venv accidentally created *inside the repo root* during M5 (a mis-pathed venv command; the directory name is a mangled `C:\Users\guill\AppData\Local\Temp\m5pkg-venv`). It is invisible to git (venvs ship their own `.gitignore` with `*`), so it does not dirty the tree and will not be committed, but it is clutter and should be deleted locally (see recommendations).
- **Stray tree outside the repo:** `C:\c\Users\guill\ai\coffee\artisan_companion_app\` — a small (56K) mirror tree created by earlier path-mangled tool writes (the same `C:\` prefix-doubling that briefly misdirected this review's own report write, since corrected). It contains duplicates of tracked research files plus two files that never reached the repo: `research/corpus_manifest.txt` (a 230-line list of corpus paths) and `scan_corpus.py`. Neither is referenced by the repo; both are untracked strays outside the working tree.

---

## Fixes applied (file-by-file)

| File | Change |
|---|---|
| `pyproject.toml` | Added `[tool.setuptools.package-data] app = ["*.html"]` — the release-blocking fix: wheels/sdists now ship `app/frontend.html` + `app/viewer.html` (verified by rebuild + wheel-install smoke test) |
| `README.md` | Status line 282 → **298** tests; sample-data section now runs `artisan-companion --logs-dir tests/fixtures/alogs` (the old steps produced an empty library) + sensory-store location note; Install section mentions the `dev` extra |
| `docs/sample-gallery.md` | Corrected the incorrect "first Windows-recorded generation" claim (moved to 2.6.0, where the corpus proves it; 2.10.0 row/note now states verified key-set facts); added the sensory-store note to "How to View" |
| `docs/implementation-plan.md` | Removed stale `HEAD commit d6c4538` from the status blockquote; repo-layout comment now lists all four packages; tech-stack App/UI row reflects the shipped canvas+SVG vanilla-JS frontend |
| `.github/workflows/test.yml` | Added the minimal `packaging` job (build wheel+sdist, assert wheel contents incl. HTML assets) — closes the CI gap that let the wheel bug through |

No changes to `src/`, `tests/`, `tests/fixtures/`, or the corpus. Nothing committed, pushed, tagged, or released.

## Remaining recommendations

1. **`tests/fixtures/alogs/README.md` still contains the incorrect "first Windows-recorded generation" note for v2.10.0** (it says "first Windows-recorded generation" in the versions table). It is under `tests/` and was off-limits for this review — fix it to match the corrected gallery (2.6.0 is the first Windows-recorded generation) when `tests/` may be touched.
2. **Delete the stray `UsersguillAppDataLocalTempm5pkg-venv/` directory** in the repo root (gitignored, but clutter from a mis-pathed venv command during M5).
3. **Inspect and delete the stray `C:\c\...` tree** (56K, outside the repo): it holds path-mangled duplicates of research files plus `corpus_manifest.txt` and `scan_corpus.py`, which never made it into the repo. Salvage the latter two into `research/` first if they are wanted; then delete `C:\c`.
4. **Push `dev` and watch CI** — the three M5 commits (plus this review's changes, once the orchestrator commits them) have never been CI'd; the README's "CI green" refers to the last pushed state (`d6c4538`) until then.
5. **Tag `v0.1.0` and cut the first GitHub release** per the distribution decision (pyproject is already at `0.1.0`; wheel + sdist build cleanly and are verified). Not done here per instructions.
6. **Optional hardening:** `artisan-companion --help` currently starts the server (manual argv parsing in `src/app/main.py`, no argparse) — a known caveat from the packaging spike; consider a real `--help` in a future `src/` change (out of scope for this review).
7. **Optional:** run the new `packaging` CI job on 3.11 as well to cover the `requires-python` floor; the suite matrix already covers 3.11–3.13.
8. The stale `src/artisan_companion.egg-info/` is regenerated on every build and gitignored — no action needed.
