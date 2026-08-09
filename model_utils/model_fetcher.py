import os
import sys
import subprocess

# 1. Get the current directory of nano_arch.py (.../ComfyUI/model_utils)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Go up ONE level to reach the main ComfyUI root
comfyui_root = os.path.abspath(os.path.join(current_dir, ".."))

# 3. Force Python to look at the ComfyUI root first
if comfyui_root not in sys.path:
    sys.path.insert(0, comfyui_root)

from model_utils.env_config import EnvironmentConfig
from model_utils.log_icons import LogIcons
from load_model import LoadModel

ico = LogIcons()

class ModelFetcher:
    """Manages multi-connection network operations via persistent system binaries."""
    def __init__(self, env = None):
        self.env = env

    def download_to_cache(self, url, model_name, target_dir):
        staged_file_path = os.path.join(self.env.staging_cache, model_name)
        print(f"{ico.get('COMM',__class__)} Starting download.")
                
        wget_cmd = ["wget", "-c", "-O", staged_file_path]
        if "huggingface.co" in url and self.env.hf_token:
            print(f"{ico.get('KEY',__class__)} HF URL detected. Injecting Authorization header '{self.env.hf_token[:10]}...'")
            wget_cmd.append(f"--header=Authorization: Bearer {self.env.hf_token}")
        elif "civitai.com" in url and self.env.civitai_token:
            print(f"{ico.get('KEY',__class__)} CivitAI URL detected. Injecting Authorization header '{self.env.hf_token[:10]}...'")
            wget_cmd.append(f"--header=Authorization: Bearer {self.env.civitai_token}")
        wget_cmd.append(url)

        try:
            print(self.env.ico.sep(4))
            print(f"{ico.get('COMM',__class__)} COMMAND: {wget_cmd}.")
            print(self.env.ico.sep(4))
            subprocess.run(wget_cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"{ico.get('ERR',__class__)} DOWNLOAD FAILED")
            print(f"MODEL    : {model_name}")
            print(f"DIRECTORY: {target_dir}")
            print(f"URL      : {url}")
            staged_file_path = None
        print(self.env.ico.sep(3))
        
        return staged_file_path

        
