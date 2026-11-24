import os
import sys
import json
import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import uvicorn

from model_utils.nano_arch import SovereignManager

app = FastAPI(title="NanoVault Sanctuary")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensures only one command redirects process-level stdout/stderr FDs at a time
_stream_fd_lock = threading.Lock()


def get_host():
    try:
        with open("config.json") as f:
            env = json.load(f)
    except Exception:
        env = None
    return env.get("host", None) if env else None


def _validate_origin(request: Request) -> bool:
    """VFP_02_shield: Strict Origin Validation."""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    client_origin = origin if origin else (referer.rstrip("/") if referer else None)

    allowed_origins = ["http://127.0.0.1:8000", "http://localhost:8000"]
    host = get_host()
    if host:
        allowed_origins.append(f"http://{host}:8000")

    return client_origin in allowed_origins


# --- Static Mounts ---
app.mount("/model_utils", StaticFiles(directory=os.path.join(BASE_DIR, "model_utils")), name="model_utils")
app.mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "web", "js")), name="js")
app.mount("/css", StaticFiles(directory=os.path.join(BASE_DIR, "web", "css")), name="css")


@app.get("/", response_class=HTMLResponse)
async def load_control_center():
    ui_path = os.path.join(BASE_DIR, "web", "index.html")
    if not os.path.exists(ui_path):
        return HTMLResponse(content=f"<h1>[CRITICAL ERROR]</h1><p>UI not found at {ui_path}</p>", status_code=404)
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("./web/favicon.ico")

@app.get("/api/config/workflow-path")
async def get_workflow_path():
    config_path = os.path.join(BASE_DIR, "config.json")
    if not os.path.exists(config_path):
        return JSONResponse(status_code=404, content={"status": "ERROR", "message": "config.json not found"})
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        comfy_root = data.get("paths", {}).get("comfy_ui_root", "").rstrip("/\\")
        full_path = f"{comfy_root}/user/default/workflows/"
        return {"status": "SUCCESS", "workflow_path": full_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERROR", "message": str(e)})


@app.post("/api/execute")
async def execute_command(request: Request):
    if not _validate_origin(request):
        return JSONResponse(status_code=403, content={"status": "ERROR", "message": "Unauthorized"})

    payload = await request.json()
    command_array = payload.get("command", [])

    if not command_array:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Empty command array received."})

    command_flag = command_array[0]
    target = command_array[1] if len(command_array) > 1 else "Global"

    try:
        retval = SovereignManager().execute(command_array)
        return {
            "status": "SUCCESS",
            "command_echo": command_array,
            "retval": retval,
            "message": f"Successfully executed {command_flag} on {target}"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "ERROR",
                "error_type": type(e).__name__,
                "message": str(e)
            }
        )


@app.post("/api/execute-stream")
async def execute_command_stream(request: Request):
    """
    Executes SovereignManager().execute() while capturing OS-level FD 1 (stdout)
    and FD 2 (stderr) so both Python print() and subprocess wget progress stream
    live as newline-delimited JSON (NDJSON).
    """
    if not _validate_origin(request):
        return JSONResponse(status_code=403, content={"status": "ERROR", "message": "Unauthorized"})

    payload = await request.json()
    command_array = payload.get("command", [])

    if not command_array:
        return JSONResponse(status_code=400, content={"status": "ERROR", "message": "Empty command array received."})

    command_flag = command_array[0]
    target = command_array[1] if len(command_array) > 1 else "Global"
    loop = asyncio.get_running_loop()
    event_queue: asyncio.Queue = asyncio.Queue()

    def push_event(obj):
        loop.call_soon_threadsafe(event_queue.put_nowait, obj)

    def run_with_fd_capture():
        with _stream_fd_lock:
            # Ensure Python's print() flushes per line even when FD 1 points to a pipe
            for stream in (sys.stdout, sys.stderr):
                if hasattr(stream, "reconfigure"):
                    try:
                        stream.reconfigure(line_buffering=True)
                    except Exception:
                        pass

            sys.stdout.flush()
            sys.stderr.flush()

            orig_stdout_fd = os.dup(1)
            orig_stderr_fd = os.dup(2)
            read_fd, write_fd = os.pipe()

            # Redirect OS FDs 1 & 2 into the pipe so print() AND subprocess wget are captured
            os.dup2(write_fd, 1)
            os.dup2(write_fd, 2)
            os.close(write_fd)

            def drain_pipe():
                try:
                    while True:
                        chunk = os.read(read_fd, 4096)
                        if not chunk:
                            break
                        # Echo back to original server terminal
                        try:
                            os.write(orig_stdout_fd, chunk)
                        except OSError:
                            pass
                        text = chunk.decode("utf-8", errors="replace")
                        push_event({"type": "stdout", "data": text})
                finally:
                    os.close(read_fd)

            reader_thread = threading.Thread(target=drain_pipe, daemon=True)
            reader_thread.start()

            result_packet = None
            try:
                retval = SovereignManager().execute(command_array)
                result_packet = {
                    "type": "result",
                    "status": "SUCCESS",
                    "command_echo": command_array,
                    "retval": retval,
                    "message": f"Successfully executed {command_flag} on {target}"
                }
            except Exception as e:
                result_packet = {
                    "type": "result",
                    "status": "ERROR",
                    "error_type": type(e).__name__,
                    "retval": None,
                    "message": str(e)
                }
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                # Restoring FDs 1 & 2 closes the pipe's write end, signaling EOF to drain_pipe
                os.dup2(orig_stdout_fd, 1)
                os.dup2(orig_stderr_fd, 2)
                reader_thread.join(timeout=2.0)
                os.close(orig_stdout_fd)
                os.close(orig_stderr_fd)

            push_event(result_packet)
            push_event(None)  # End-of-stream sentinel

    threading.Thread(target=run_with_fd_capture, daemon=True).start()

    async def ndjson_generator():
        while True:
            item = await event_queue.get()
            if item is None:
                break
            yield (json.dumps(item) + "\n").encode("utf-8")

    return StreamingResponse(
        ndjson_generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


if __name__ == "__main__":
    port = 8000
    host_id = "127.0.0.1"

    try:
        print(f"[SYSTEM INIT] Sovereign Gateway online. Binding to {host_id}:{port}")
        uvicorn.run("main:app", host=host_id, port=port, reload=False)
    except Exception:
        sys.exit(0)