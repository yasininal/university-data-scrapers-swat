from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Run the FastAPI-based dashboard UI.

    This keeps a simple `python app.py` entrypoint while using the
    more flexible web stack instead of Streamlit.
    """
    host = os.getenv("UI_HOST", "127.0.0.1")
    port = int(os.getenv("UI_PORT", "8080"))

    uvicorn.run(
        "webapp.server:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
