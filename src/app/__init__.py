"""app: sensory editor web UI for artisan-companion (M2b).

A local FastAPI web app that runs offline at localhost, providing:
- Backend endpoints for roast listing, sensory record CRUD, cupping sessions,
  and radar updates
- Frontend: single-page HTML+JS editor with roast picker, cupping form,
  and radar visualization

Entry point: py -3 -m app [--logs-dir PATH] [--sensory-dir PATH]
  defaults: sensory/ next to logs
"""

__all__ = []
