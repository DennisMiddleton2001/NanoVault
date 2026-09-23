import os
import sys
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from fastapi import Request
from fastapi.responses import JSONResponse

from model_utils.nano_arch import SovereignManager

app = FastAPI(title="NanoVault Sanctuary")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- THE MISSING LINK: Mount model_utils so environment.json is directly accessible ---
app.mount("/model_utils", StaticFiles(directory=os.path.join(BASE_DIR, "model_utils")), name="model_utils")
# Point the sub-routes directly to the web/ subdirectories
app.mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "web", "js")), name="js")
app.mount("/css", StaticFiles(directory=os.path.join(BASE_DIR, "web", "css")), name="css")
@app.get("/", response_class=HTMLResponse)

async def load_control_center():
    ui_path = os.path.join(BASE_DIR, "web","index.html")
    if not os.path.exists(ui_path):
        return HTMLResponse(content=f"<h1>[CRITICAL ERROR]</h1><p>UI not found at {ui_path}</p>", status_code=404)
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()

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
    # VFP_02_shield: Strict Origin Validation
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    
    # Standardize the incoming origin string for comparison
    client_origin = origin if origin else (referer.rstrip('/') if referer else None)
    allowed_origins = ["http://127.0.0.1:8000", "http://localhost:8000"]
    
    if client_origin not in allowed_origins:
        # Returns HTTP 403 Forbidden at the network layer
        return JSONResponse(
            status_code=403,
            content={"status": "ERROR", "message": "Unauthorized"}
        )

    payload = await request.json()
    command_array = payload.get("command", [])
    
    if not command_array:
        # Returns HTTP 400 Bad Request
        return JSONResponse(
            status_code=400,
            content={"status": "ERROR", "message": "Empty command array received."}
        )

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
        # Returns HTTP 500 Internal Server Error
        return JSONResponse(
            status_code=500,
            content={
                "status": "ERROR",
                "error_type": type(e).__name__,
                "message": str(e)
            }
        )

if __name__ == "__main__":
    port = 8000
    host_id = "127.0.0.1"

    try:
        print(f"[SYSTEM INIT] Sovereign Gateway online. Binding to {host_id}:{port}")
        uvicorn.run("main:app", host=host_id , port=port, reload=False,)
    except:
            sys.exit(0)

