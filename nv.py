import os
import sys
import json
from model_utils.nano_arch import SovereignManager



workspace_folder = "/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/"
#region USAGE
def print_usage():
    print(f"****DANGER!!!  POWER USER ZONE*****")
    print(f"")
    print(f"Visit us at https://www.amnanotech.com")
    print(f"")
    print(f"USAGE: {sys.argv[0]}")
    print(f"")
    print("WORKFLOW TOOLS - These affect the specified workflow only")
    print("  --list-workflows : Creates a json report of all dependencies in a folder")
    print("  --a  :  Add models: Download=>Vault=>Deploy")
    print("  --as :  Add models: Download=>Deploy - good for staging spot instances where vault isn't needed")
    print("  --t  :  Trim models: VaultActive=>DeleteActive")
    print("  --i  :  Ingest models: VaultActive (no delete)")
    print("  --e  :  Evict! DeleteActive, DeleteVaulted(unless excluded in config.json)")
    print(f"")
    print("MODEL FILE TOOLS")
    print("  --model       :  Print debug info for a single model file (output is large)")
    print("  --scan-active :  Health check .safetensors in ComfyUI/models folders.")
    print("  --scan-vault  :  Health check .safetensors in NanoVault.")
    print("  --single-add  :  Download, vault, and install a single model")
    print("  --single-spot :  Download and install a single model (only to active).")
    print(f"")
    print("  EXAMPLES:")
    print("         --list_workflows '../ComfyUI/user/default/workflows/'")
    print("         --a '/path/to/comfyworkflow.json'")
    print("         --t '/path/to/comfyworkflow.json'")
    print("         --scan-active")
    print("         --model '/path/to/vae_volcano.safetensors'")
    print("         --single-add 'filename.safetensors' 'models_subfolder' 'https://url.com'")
    print("         --single-spot 'filename.safetensors' 'models_subfolder' 'https://url.com'")
    print("         --st 'vae' 'vae_volcano.safetensors'")
    print("         --sf 'https://some.url.com/path/vae_volcano.safetensors' 'vae' 'vae_volcano.safetensors'")
    print("         --cleanup")
    sys.exit(1)
#endregion


argc = len(sys.argv)

if argc==1:
    print_usage()
    sys.exit(1)

args = sys.argv
del args[0]

results = SovereignManager().execute(args)

