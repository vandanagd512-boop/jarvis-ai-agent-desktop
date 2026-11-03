import sys
import os

# Add root directory to sys.path for Vercel serverless execution
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from jarvis.ui.api_server import app
except Exception as exc:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    error_trace = traceback.format_exc()
    app = FastAPI()

    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def debug_error(path_name: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "JARVIS Vercel Lambda Initialization Error",
                "message": str(exc),
                "traceback": error_trace,
            },
        )
