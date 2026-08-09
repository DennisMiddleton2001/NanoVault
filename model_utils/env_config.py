import os
import sys
import json
from pathlib import Path

# Insert ComfyUI root into sys.path so imports work from model_utils folder.
current_dir = os.path.dirname(os.path.abspath(__file__))
comfyui_root = os.path.abspath(os.path.join(current_dir, ".."))
if comfyui_root not in sys.path:
    sys.path.insert(0, comfyui_root)

from model_utils.banner_gen import Banner
from model_utils.log_icons import LogIcons

env_path = "/home/darth-tedious/.sovereign-ai/ComfyUI/model_utils/environment.json"

class EnvironmentConfig:
    """Manages system paths, environment states, and API credentials."""
    def __init__(self, env_path = env_path, show_banner=True):
        config_error = False
        self.ico = LogIcons()
        self.env_path = env_path

        if show_banner:
            Banner()

        json_path = os.path.expanduser(os.path.join(".",env_path))
        try:        
            with open(json_path) as f:
                env = json.load(f)
            
            paths = env.get("paths")
            self.active_root   = os.path.expanduser(os.path.join('.', paths.get('active_root')))
            self.staging_cache = os.path.expanduser(os.path.join('.', paths.get('staging_cache')))
            self.vault_dir     = os.path.expanduser(os.path.join('.', paths.get('vault_dir')))

            # Get fast_hash value.
            self.fast_hash = env.get("fast_hash")
            
            # Initialize tokens for CLI repo access.
            tokens = env.get("tokens")
            self.hf_token = tokens.get("hf_token")
            self.civitai_token = tokens.get("civitai_token")
        except Exception as e:
            #if something is wrong with JSON, point out the line number.
            print(f"{self.ico.get('ERR')} - ERROR: {self.env_path}\n{e}")
            sys.exit(1)

        # Automatically create the directory (and any necessary parent directories) if it's missing
        pc = Path(self.staging_cache)
        pv = Path(self.vault_dir)
        
        print(f"NanoArch Configuration")
        print(self.ico.sep(0))
        print(f"CONFIG : '{self.env_path}'\n")

        if os.path.exists(self.active_root):
            print(f"{self.ico.get('DONE')} Models    : {self.active_root}")
        else:
            print(f"{self.ico.get('ERR')} Models    : {self.active_root} - does not exist.")
            config_error = True

        if os.path.exists(self.vault_dir):
            print(f"{self.ico.get('DONE')} NanoVault : {self.vault_dir}")
        else:
            print(f"{self.ico.get('ERR')} NanoVault : {self.vault_dir} - does not exist.")
            config_error = True

        if os.path.exists(self.staging_cache):
            print(f"{self.ico.get('DONE')} Staging   : {self.staging_cache}")
        else:
            print(f"{self.ico.get('ERR')} Staging   : {self.staging_cache} - does not exist")
            config_error = True

        if not self.fast_hash:
            hash_type = "SHA-256"
        else:
            hash_type = "XXH3-128"

        print("")
        print(f"{self.ico.get('KEY')} VAULT_HASH     : {hash_type}")                        
        print(f"{self.ico.get('KEY')} HF_TOKEN       : {self.hf_token[:10]}...")
        print(f"{self.ico.get('KEY')} CIVITAI_TOKEN  : {self.civitai_token[:10]}...")
        print(self.ico.sep(0))        
        if config_error:
            print(f"{self.ico.get('ERR')} Unable to continue - verify paths.")
            sys.exit(1)



        
