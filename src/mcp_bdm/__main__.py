"""Entry point del pacchetto: delega alla CLI.

`python -m mcp_bdm <comando>`  -> CLI (login/search/get/check).
Il server MCP ha un entry dedicato:  python -m mcp_bdm.server
"""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
