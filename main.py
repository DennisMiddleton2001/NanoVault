import os
import sys
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from model_utils.nano_arch import SovereignManager

app = FastAPI(title="NanoVault Sanctuary")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- THE MISSING LINK: Mount model_utils so environment.json is directly accessible ---
app.mount("/model_utils", StaticFiles(directory=os.path.join(BASE_DIR, "model_utils")), name="model_utils")

@app.get("/", response_class=HTMLResponse)
async def load_control_center():
    ui_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(ui_path):
        return HTMLResponse(content=f"<h1>[CRITICAL ERROR]</h1><p>UI not found at {ui_path}</p>", status_code=404)
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/save_env")
async def save_environment(request: Request):
    try:
        payload = await request.json()
        env_path = os.path.join(BASE_DIR, "model_utils", "environment.json")
        os.makedirs(os.path.dirname(env_path), exist_ok=True)
        
        with open(env_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
            
        return {"status": "SUCCESS", "message": "Environment configuration saved."}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

@app.post("/api/execute")
async def execute_command(request: Request):
    payload = await request.json()
    command_array = payload.get("command", [])
    
    if not command_array:
        return {"status": "ERROR", "message": "Empty command array received."}

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
        return {
            "status": "ERROR",
            "error_type": type(e).__name__,
            "message": str(e)
        }

if __name__ == "__main__":
    print("[SYSTEM INIT] Sovereign Gateway online. Binding to 0.0.0.0:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)