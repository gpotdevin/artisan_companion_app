# Artisan Companion - Sensory Editor (M2b)

A local web application for annotating Artisan .alog roast logs with sensory data:
cupping scores, flavor radar, descriptors, and defect observations.

## Usage

Start the server from the `src/` directory:

```bash
cd src
py -3 -m app [--logs-dir PATH] [--sensory-dir PATH]
```

Or from the repo root with PYTHONPATH:

```bash
PYTHONPATH=src py -3 -m app [--logs-dir PATH] [--sensory-dir PATH]
```

- `--logs-dir`: Path to the directory containing .alog files (default: `./logs`)
- `--sensory-dir`: Path to the sensory store directory (default: `<logs-dir>/../sensory`)

The app starts on `http://127.0.0.1:8000` and can be accessed in your browser.

## Features

- **Roast Library**: Browse all roasts from your .alog logs directory
- **Cupping Entry**: Record SCA scores (10 attributes), descriptors, notes, and defects
- **Live Total Calculation**: Total score is automatically computed from attribute scores
- **Flavor Radar**: Visualize and edit the 9-axis flavor radar matching Artisan's style
- **Defect Tracking**: Check off the 10 native Artisan defect flags
- **Cupping History**: View, edit, and delete past cupping sessions for each roast

## Architecture

- **Backend**: FastAPI with endpoints for CRUD operations on sensory records
- **Frontend**: Single-page HTML+JS application with vanilla JavaScript (no build step, no npm)
- **Storage**: Uses the SensoryStore from `src/store/` - JSON sidecars in the sensory directory
- **Index**: SQLite index for fast listing and searching

## Endpoints

- `GET /api/roasts` - List all roasts with annotation status
- `GET /api/roasts/{uuid}` - Get sensory record for a roast
- `POST /api/roasts/{uuid}` - Create empty sensory record
- `PUT /api/roasts/{uuid}` - Update record top-level sections
- `DELETE /api/roasts/{uuid}` - Delete sensory record
- `POST /api/roasts/{uuid}/cupping` - Add cupping session
- `PUT /api/roasts/{uuid}/cupping/{index}` - Edit cupping session
- `DELETE /api/roasts/{uuid}/cupping/{index}` - Remove cupping session
- `PUT /api/roasts/{uuid}/radar` - Update radar values
- `GET /api/radar_labels` - Get default radar labels
- `GET /api/score_keys` - Get SCA score keys
- `GET /api/defect_keys` - Get defect keys

## Guardrails

- **Read-only .alog files**: The app never writes to .alog files (native sync is opt-in and separate)
- **No eval/exec**: No code execution on log content
- **Atomic writes**: Uses SensoryStore's atomic write mechanism
- **Validation**: All inputs are validated against the schema

## Dependencies

The app requires FastAPI and uvicorn (included in the `app` optional dependencies group):

```bash
py -3 -m pip install fastapi uvicorn
```

The core libraries (`alog_core`, `store`) remain stdlib-only with no additional dependencies.
