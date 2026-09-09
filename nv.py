import os
import sys
import json
from model_utils.nano_arch import SovereignManager



workspace_folder = "/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/"
#region USAGE
def print_usage():

    print(f"***IMPORTANT*** Items marked with '*' are features which are included in the premium")
    print(f"   edition of NanoArch with NanoVault.  Visit us at 'https://www.amnanotech.com' and")
    print(f"   help us keep the lights on and the tensor cores humming. Thanks in advance!\n")
    print(f"USAGE: '{sys.argv[0]}'")
    print("WORKFLOW TOOLS")
    print("  --a  :  Add workflow models to ComfyUI workspace.")
    print("  --t  :  Free workflow models from ComfyUI workspace and ingest to NanoVault.")
    print("* --i  :  Ingest workflow models to NanoVault.")
    print("* --e  :  Evict!!! Free workflow models from ComfyUI workspace ***AND*** NanoVault.")
    print(f"")
    print("MODEL FILE TOOLS")
    print("  --scan-active :  Health check .safetensors in ComfyUI/models folders.")
    print("  --model       :  Print debug info for a single model file.")
    print("* --scan-vault  :  Health check .safetensors in NanoVault.")
    print("* --st          :  Trim single model from ComfyUI workspace and ingest to NanoVault.")
    print("* --sf          :  Fetch single model from URL, deploy, and ingest to NanoVault.")
    print(f"")
    print("VAULT MANAGEMENT")
    print("* --r           :  Rebuild NanoVault HASH values. Does not validate tensor structure.")
    print("* --cleanup     :  Delete all active files not found in the NanoVault.")
    print("")
    print("  EXAMPLES:")
    print("         --a '/path/to/comfyworkflow.json'")
    print("         --t '/path/to/comfyworkflow.json'")
    print("         --scan-active")
    print("         --model '/path/to/vae_volcano.safetensors'")
    print("         --si 'vae' 'vae_volcano.safetensors'")
    print("         --st 'vae' 'vae_volcano.safetensors'")
    print("         --sf 'https://some.url.com/path/vae_volcano.safetensors' 'vae' 'vae_volcano.safetensors'")
    print("         --cleanup")
    sys.exit(1)
#endregion


argc = len(sys.argv)
if argc==1:
    print_usage()
    sys.exit(1)
elif argc==2:
    args = [sys.argv[1]]
else:
    args = [sys.argv[1], sys.argv[2]]

results = SovereignManager().execute(args)

print(f"Input:\n{args}\n")
print(f"Output:\n")
print(json.dumps(results, indent=2))
