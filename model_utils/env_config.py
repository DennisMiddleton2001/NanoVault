import os
import sys
import json
from pathlib import Path

from .banner_gen import Banner
from .log_icons import LogIcons

env_path = os.path.join(".", "config.json")

class EnvironmentConfig:
    """Manages system paths, environment states, and API credentials."""
    def __init__(self, env_path = env_path, banner=False):
        config_error = False
        self.ico = LogIcons()
        self.env_path = env_path
        
        if banner:
            Banner()

        json_path = os.path.expanduser(os.path.join(".",env_path))
        try:
            with open(json_path) as f:
                env = json.load(f)
            
            paths = env.get("paths")
            self.comfy_ui_root = os.path.expanduser(paths.get('comfy_ui_root'))
            self.active_root   = os.path.expanduser(os.path.join(self.comfy_ui_root, 'models'))
            self.staging_cache = os.path.expanduser(paths.get('staging_cache'))
            self.vault_dir     = os.path.expanduser(paths.get('vault_dir'))
            self.fast_hash = env.get('fast_hash')
            self.sidecar_ext = ".xxh128" if self.fast_hash else ".sha256"
            tokens = env.get("tokens")
            self.hf_token = tokens.get("hf_token")
            self.civitai_token = tokens.get("civitai_token")
            self.immutable = env.get('exclude_from_purge')

        except Exception as e:
            #if something is wrong with JSON, point out the line number.
            print(f"{self.ico.get('ERR')} - ERROR: {self.env_path}\n{e}")

        # Automatically create the directory (and any necessary parent directories) if it's missing
        pc = Path(self.staging_cache)
        pv = Path(self.vault_dir)

    def print_config(self):
        print(f"NanoArch Configuration")
        print(self.ico.sep(0))
        print(f"CONFIG : '{self.env_path}'\n")
        config_error = False
        if os.path.exists(self.comfy_ui_root):
            print(f"{self.ico.get('FOLD')} ComfyUI    : {self.comfy_ui_root}")
        else:
            print(f"{self.ico.get('ERR')} ComfyUI     : {self.comfy_ui_root} - does not exist.")
            config_error = True

        if os.path.exists(self.active_root):
            print(f"{self.ico.get('FOLD')} Models    : {self.active_root}")
        else:
            print(f"{self.ico.get('ERR')} Models    : {self.active_root} - does not exist.")
            config_error = True

        if os.path.exists(self.vault_dir):
            print(f"{self.ico.get('FOLD')} NanoVault : {self.vault_dir}")
        else:
            print(f"{self.ico.get('ERR')} NanoVault : {self.vault_dir} - does not exist.")
            config_error = True

        if os.path.exists(self.staging_cache):
            print(f"{self.ico.get('FOLD')} Staging   : {self.staging_cache}")
        else:
            print(f"{self.ico.get('ERR')} Staging   : {self.staging_cache} - does not exist")
            config_error = True

        hash_type = self.sidecar_ext

        print("")
        print(f"{self.ico.get('KEY')} HASH_TYPE      : {hash_type}")                        
        print(f"{self.ico.get('KEY')} HF_TOKEN       : {self.hf_token[:10]}...")
        print(f"{self.ico.get('KEY')} CIVITAI_TOKEN  : {self.civitai_token[:10]}...\n")
        
        if len(self.immutable):
            print(f"{self.ico.get('LIGHT')} Locked From Purge")
            print(self.ico.sep(3, 40))
            for m in self.immutable:
                print(f"{self.ico.get('LOCK')}    {m}")

        print(self.ico.sep(0))
        if config_error:
            print(f"{self.ico.get('ERR')} Unable to continue - check {self.env_path}.")
            return False

        return True

