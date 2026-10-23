"""Android entry point for artisan-companion (Chaquopy).

Called from MainActivity (Kotlin) on a background thread:

    Python.getInstance().getModule("launcher")
        .callAttr("start_server", logsDir, sensoryDir)

It points the existing FastAPI app at on-device storage and starts uvicorn
bound to localhost. The WebView then loads http://127.0.0.1:8000.

No artisan-companion source is modified: the app already reads --logs-dir and
--sensory-dir from sys.argv at startup, so we set sys.argv and reuse it.
"""

from __future__ import annotations

import sys
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000


def start_server(logs_dir: str, sensory_dir: str,
                 host: str = HOST, port: int = PORT) -> None:
    """Create storage dirs, point the app at them, and serve forever.

    Blocks the calling thread (uvicorn). Run from a background thread.
    """
    logs = Path(logs_dir)
    sensory = Path(sensory_dir)
    logs.mkdir(parents=True, exist_ok=True)
    sensory.mkdir(parents=True, exist_ok=True)

    # The FastAPI startup handler in app.main reads these flags from sys.argv.
    sys.argv = [
        "artisan-companion",
        "--logs-dir", str(logs),
        "--sensory-dir", str(sensory),
    ]

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="warning",
        reload=False,
    )
