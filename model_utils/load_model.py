import os
import sys
import json
import struct

current_dir = os.path.dirname(os.path.abspath(__file__))
comfyui_root = os.path.abspath(os.path.join(current_dir, ".."))
if comfyui_root not in sys.path:
    sys.path.insert(0, comfyui_root)

from model_utils.env_config import EnvironmentConfig

class LoadModel:

    def __init__(self, env=None, target_root=None, debug=False):
        self.env = env
        self.file_path = target_root
        self.debug = debug

    def print_json(self, headers):
        output = json.dumps(headers, indent=4)
        print(output)

    def analyze(self):
        manifest = {
            "fq_path": self.file_path,
            "valid": False,
            "error": None,
            "tensor_count": 0,
            "metadata": {}
        }
        
        if not self.file_path.lower().endswith(".safetensors"):
            print(f"{self.env.ico.get('WRN', __class__)} Unable to scan tensor structure. Running from ComfyUI root?")
            manifest["valid"] = True
            return manifest

        try:
            # Bypass the safetensors library entirely to avoid mmap deadlocks.
            # Read only the lightweight JSON header directly from the binary.
            with open(self.file_path, 'rb') as f:
                # Read the first 8 bytes to get the header length (little-endian 64-bit unsigned integer)
                header_size_bytes = f.read(8)
                if len(header_size_bytes) < 8:
                    raise ValueError("File is too small to be a valid safetensors file.")
                
                header_size = struct.unpack('<Q', header_size_bytes)[0]
                
                # Prevent malicious or corrupted oversized headers from blowing up RAM
                if header_size > 100_000_000:
                    raise ValueError(f"Header size {header_size} bytes is abnormally large. Possible corruption.")
                    
                # Read the JSON header string
                header_bytes = f.read(header_size)
                header_json = json.loads(header_bytes.decode('utf-8'))
                if self.debug:
                    self.print_json(header_json)
                # Safetensors metadata is stored under the special '__metadata__' key
                manifest["metadata"] = header_json.get("__metadata__", {})
                
                # The remaining keys represent the actual tensors
                metadata_offset = 1 if "__metadata__" in header_json else 0
                manifest["tensor_count"] = len(header_json) - metadata_offset
                manifest["valid"] = True
                
        except Exception as e:
            manifest["error"] = str(e)
            
        return manifest




        
        




        
        

