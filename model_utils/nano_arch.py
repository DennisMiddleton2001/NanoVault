import os
import sys
import json
import hashlib
import shutil
import subprocess

# Add model_tools to the system path so libraries import properly.
current_dir = os.path.dirname(os.path.abspath(__file__))
comfyui_root = os.path.abspath(os.path.join(current_dir, ".."))
if comfyui_root not in sys.path:
    sys.path.insert(0, comfyui_root)

from model_utils.env_config import EnvironmentConfig
from model_utils.ingest_pipeline import IngestPipeline
from model_utils.deployment_pipeline import DeploymentPipeline
from model_utils.purge_pipeline import PurgePipeline
from model_utils.trim_pipeline import TrimPipeline
from model_utils.test_sweep import AnalyzeModelsFolder
from model_utils.load_model import LoadModel

class SovereignManager:
    """The universal runtime management class. Routes CLI commands to the correct pipeline."""
    def __init__(self):
        self.env = EnvironmentConfig()

    def execute(self, args_list):
        self.target_path = None
        self.command = None
        argc = len(args_list)

        if argc > 1:
            for flag in ['--a', '--t', '--e', '--i', '--r','--si','--st', '--sf','--scan-active','--scan-vault','--model','--cleanup']:
                if flag in args_list:
                    self.command = flag
                    idx = args_list.index(flag)
                    if argc > idx + 1:
                        self.target_path = args_list[idx + 1]
                    break

        if not self.command:
            print(f"SCRIPT: '{sys.argv[0]}' Usage Information")
            print(f"")
            print("WORKFLOW TOOLS")
            print("  --a  :  Add workflow models to ComfyUI workspace.")
            print("  --t  :  Free workflow models from ComfyUI workspace and ingest to NanoVault.")
            print("  --i  :  Ingest workflow models to NanoVault.")
            print("  --e  :  Evict!!! Free workflow models from ComfyUI workspace ***AND*** NanoVault.")
            print(f"")
            print("MODEL FILE TOOLS")
            print("  --scan-active :  Health check .safetensors in ComfyUI/models folders.")
            print("  --scan-vault  :  Health check .safetensors in NanoVault.")
            print("  --model       :  Print debug info for a single model file.")
            print("  --st          :  Trim single model from ComfyUI workspace and ingest to NanoVault.")
            print("  --sf          :  Fetch single model from URL, deploy, and ingest to NanoVault.")
            print(f"")
            print("VAULT MANAGEMENT TOOLS")
            print("  --r  :  Rebuild NanoVault HASH values. Does not validate tensor structure.")
            print("          Used when changing value of 'fast_hash' in configuration JSON.")
            print("  --cleanup     :  Delete all active files not found in NanoVault.")
            print("")
            print("  EXAMPLES:")
            print("")
            print("         --a '/path/to/comfyworkflow.json'")
            print("         --t '/path/to/comfyworkflow.json'")
            print("         --i '/path/to/comfyworkflow.json'")
            print("         --e '/path/to/comfyworkflow.json'")
            print("         --scan-active")
            print("         --scan-vault")
            print("         --model '/path/to/vae_volcano.safetensors'")
            print("         --si 'vae' 'vae_volcano.safetensors'")
            print("         --st 'vae' 'vae_volcano.safetensors'")
            print("         --sf 'https://some.url.com/path/vae_volcano.safetensors' 'vae' 'vae_volcano.safetensors'")
            print("         --cleanup")
            print("         --r")
            sys.exit(1)

        if self.target_path:
            clean_path = self.target_path.strip(' \t\n\r"\'')

        if self.command in ['--si', '--st']:
            pipe = IngestPipeline(self.env)
            pipe.run()
        elif self.command in ['--a']:
            pipe = DeploymentPipeline(self.env)
            pipe.run(clean_path)
        elif self.command in ['--t']:
            pipe = TrimPipeline(self.env)
            pipe.run(clean_path)
        elif self.command in ['--e']:
            print(f"{self.env.ico.get("WRN",__class__)} Purge Worflow '{clean_path}'")
            ans = input('This operation will remove NanoVault files.  Confirm (Y/n)')
            if (ans.lower() == 'y' or ans == ''):
                pipe = PurgePipeline(self.env)
                pipe.run(clean_path)
            else:
                print(f"{self.env.ico.get('ERR',__class__)} Purge aborted.")
        elif self.command in ['--i']:
            pipe = IngestPipeline(self.env)
            pipe.run(clean_path)
        elif self.command in ['--r NOW', '--refresh NOW']:
            pipe = IngestPipeline(self.env)
            pipe.run(clean_path)
        elif self.command in ['--sf']:
            pipe = DeploymentPipeline(self.env)
            pipe.download_and_deploy()
        elif self.command in ['--scan-vault','--scan-active', '--cleanup']:
            pipe = AnalyzeModelsFolder(self.env)
            pipe.test_sweep()
        elif self.command in ['--model']:
            print(f"{self.env.ico.get("INFO",__class__)} Analyzing '{clean_path}'")
            pipe = LoadModel(self.env, clean_path, debug=True)
            pipe.analyze()
        else:
            print(f"{self.env.ico.get("ERR",__class__)} Unrecognized command flag '{self.command}'")

sm = SovereignManager()
sm.execute(sys.argv)
