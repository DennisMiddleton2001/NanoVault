import os
import json
import struct

class LoadModel:

    def __init__(self, env=None, file_path=None, debug=False):
        self.env = env
        self.file_path = file_path
        self.debug = debug

    # Used for debugging purposes to print model's JSON data in a readable format.
    def print_json(self, headers):
        output = json.dumps(headers, indent=4)
        print(output)

    # Used to analyze a model file as specified in the mutable instance.
    def analyze(self):
        return self.check_model_fq_path()

    # Used to check a model file in the active subfolder and return its metadata.
    def check_active_model(self, model_subfolder, model_name):
        self.file_path = os.path.join(self.env.active_root, model_subfolder, model_name)
        return self.check_model_fq_path()

    # Used to check a model file in the vault and return its metadata and hash.
    def check_vault_model(self, model_name):
        sidecar_hash = None
        self.file_path = os.path.join(self.env.vault_dir, model_name)

        sidecar_path = self.file_path + self.env.sidecar_ext
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r') as f:
                sidecar_hash = f.read()

        model_info = self.check_model_fq_path()

        if sidecar_hash:
            model_info.update({"sidecar_hash": sidecar_hash})

        return model_info

    # Used internally to check the fully qualified path of a model file and return its metadata.
    def check_model_fq_path(self, file_path=None):
        if file_path:
            self.file_path = file_path
        else:
            file_path = self.file_path

        model_info = {
            "fq_path": self.file_path,
            "valid": False,
            "error": None,
            "tensor_count": 0,
            "metadata": {}
        }

        if not self.file_path.lower().endswith(".safetensors"):
            print(f"{self.env.ico.get('WRN', __class__)} Unable to scan tensor structure. Running from ComfyUI root?")
            model_info["valid"] = True
            return model_info

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

                # Safetensors metadata is stored under the special '__metadata__' key
                if self.debug:
                    self.print_json(header_json)
                    model_info["metadata"] = header_json.get("__metadata__", {})
                
                # The remaining keys represent the actual tensors
                metadata_offset = 1 if "__metadata__" in header_json else 0
                model_info["tensor_count"] = len(header_json) - metadata_offset
                model_info["valid"] = True
                
        except Exception as e:
            model_info["error"] = str(e)

        return model_info


        
        




        
        

