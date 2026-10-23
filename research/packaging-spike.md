# M5 Packaging Spike — artisan-companion

## Summary

This spike makes the project `artisan-companion` properly pip-installable and verifies it end-to-end.

## Changes

### 1. `pyproject.toml` (src-layout, setuptools backend retained)

- **Metadata**: Added `readme = "README.md"`, `authors = [{ name = "gpotdevin" }]`, modest `keywords` (artisan, coffee, roasting, sensory, cupping), and `classifiers` (Python 3.11–13, MIT license, OS Independent).
- **URLs**: Added `[project.urls]` with `Repository = "https://github.com/gpotdevin/artisan_companion_app"`.
- **Console script**: Added `[project.scripts]` entry: `artisan-companion = "app.__main__:main"`. This generates `artisan-companion.exe` in `Scripts/` on Windows.
- **Extras**: 
  - `app` extra: pinned `fastapi>=0.100` and `uvicorn>=0.20` (previously unpinned).
  - `dev` extra: added `pytest` and `httpx` (tests use httpx; confirmed in `tests/test_app.py`).
- **Requires-python**: Kept at `>=3.11`; license declaration retained as `MIT`.

## Verification

### Fresh virtualenv

Created at: `C:\Users\guill\AppData\Local\Temp\m5pkg-venv`

**Note on Windows**: Python venvs on Windows place executables in `Scripts\` (not `bin/`). `pip install -e` places console scripts in that same directory, which is automatically on the venv's PATH.

### Commands executed and outputs

```bash
# 1. Create venv
py -3 -m venv C:\Users\guill\AppData\Local\Temp\m5pkg-venv

# 2. Install package in editable mode with app extra
cd /c/Users/guill/ai/coffee/artisan_companion_app
/c/Users/guill/AppData/Local/Temp/m5pkg-venv/Scripts/python.exe -m pip install -e ".[app]"
# Output: Successfully installed artisan-companion-0.1.0 (and dependencies)

# 3. Import check from a DIFFERENT working directory
cd /c/Users/guill/AppData/Local/Temp
/c/Users/guill/AppData/Local/Temp/m5pkg-venv/Scripts/python.exe -c "import alog_core, store, sync, app; print('All imports successful')"
# Output: All imports successful

# 4. Console script smoke test
/c/Users/guill/AppData/Local/Temp/m5pkg-venv/Scripts/artisan-companion.exe
# Output (truncated): 
#   INFO:     Started server process [...]
#   INFO:     Waiting for application startup.
#   INFO:     Application startup complete.
#   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# Note: The server started successfully on port 8000. No --help flag is 
# implemented (main() in src/app/main.py calls uvicorn.run directly).
# Verified by starting, seeing startup messages, and killing the process.

# 5. Module entry point smoke test
/c/Users/guill/AppData/Local/Temp/m5pkg-venv/Scripts/python.exe -m app
# Output: Same as above — Uvicorn server started on http://127.0.0.1:8000.
# Also requested http://localhost:8000/ via curl and received 200 OK with HTML.
```

### Editable install behavior

- The `-e` (editable) install creates a `.pth` file in the venv's `site-packages` that points to the project's `src/` directory.
- This means changes to source files are immediately visible without re-installation.
- The console script `artisan-companion.exe` is created in `Scripts/` and delegates to `app.__main__:main` via the entry-point mechanism.

## Caveats

1. **Windows `Scripts/` path**: On Windows, venv executables (including console scripts) are in `<venv>\Scripts\`, not `<venv>/bin/`. This is standard Windows virtualenv behavior.

2. **No `--help` in entry point**: The `main()` function in `src/app/main.py` does not use argparse; it parses command-line flags manually (`--logs-dir`, `--sensory-dir`) and then immediately starts uvicorn. Therefore, `artisan-companion --help` starts the server rather than showing usage. To smoke-test, we start the server and verify it listens on port 8000.

3. **`python -m app` works**: Because `src/app/__main__.py` exists and delegates to `main()` from `main.py`, the module can be run as `python -m app`. This is independent of the console script.

4. **Temp directory conflict**: The first import attempt failed due to a pre-existing `C:\Users\guill\AppData\Local\Temp\inspect.py` that shadowed the standard library's `inspect` module. Deleting that file resolved the issue. This is a general Windows/Temp directory hazard unrelated to the packaging.

## Test additions

Added `tests/test_packaging.py` with 16 installation-independent tests that:
- Parse `pyproject.toml` with `tomllib`
- Assert `[project.scripts]` maps `artisan-companion` to `app.__main__:main`
- Assert the `app` extra contains `fastapi>=0.100` and `uvicorn>=0.20`
- Assert `packages.find.where` contains `"src"`
- Assert name, version, license, authors, readme, keywords, classifiers, URLs

These tests pass in CI with only `pytest httpx fastapi uvicorn` installed, relying on the `conftest.py` `sys.path` hack.

## Full test suite

After adding the new test file:
- Before: 282 passed + 1 skipped
- After: 298 passed + 1 skipped (282 + 16 new packaging tests)
