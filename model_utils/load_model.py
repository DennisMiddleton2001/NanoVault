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
        sidecar_meta = None
        self.file_path = os.path.join(self.env.vault_dir, model_name)

        sidecar_path = self.file_path + self.env.sidecar_ext
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r') as f:
                sidecar_meta = json.load(f)

        model_info = self.check_model_fq_path()

        if sidecar_meta:
            model_info.update({"sidecar_hash": sidecar_meta})

        return model_info

    # Used internally to check the fully qualified path of a model file and return its metadata.
    # Used internally to check the fully qualified path of a model file and return its metadata.
    def check_model_fq_path(self, file_path=None):

        if file_path:
            self.file_path = file_path
        else:
            file_path = self.file_path

        model_entry = {
            "fq_path": self.file_path,
            "valid": False,
            "error": None,
            "size" : int(0),
            "tensor_count": int(0),
            "metadata": {}
        }
       
        if not self.file_path.lower().endswith(".safetensors"):
            print(f"{self.env.ico.get('WRN', __class__)} Unable to scan tensor structure. Running from ComfyUI root?")
            model_entry["valid"] = True
            return model_entry

        try:
            if not os.path.exists(self.file_path):
                 raise ValueError(f"File not found.")

            model_entry["size"] = os.path.getsize(self.file_path)
            if model_entry["size"] < 1024:
                 raise ValueError(f"Not a tensor file.")

            with open(self.file_path, 'rb') as f:
                # Read the first 8 bytes (header length)
                header_size_bytes = f.read(8)
                if len(header_size_bytes) < 8:
                    raise ValueError("File is too small to be a valid safetensors file.")

                header_size = struct.unpack('<Q', header_size_bytes)[0]

                if header_size > 100_000_000:
                    raise ValueError(f"Invalid header size.")

                # Read the JSON header string
                header_bytes = f.read(header_size)
                header_json = json.loads(header_bytes.decode('utf-8'))

                if self.debug:
                    model_entry["metadata"] = header_json.get("__metadata__", {})

                # --- NEW: TRUNCATION & PAYLOAD INTEGRITY CHECK ---
                # Safetensors format dictates that the binary data starts immediately 
                # after the 8-byte length prefix + the JSON header bytes.
                data_start_offset = 8 + header_size
                max_end_offset = data_start_offset

                metadata_offset = 1 if "__metadata__" in header_json else 0
                
                for key, info in header_json.items():
                    if key == "__metadata__":
                        continue
                    
                    # Each tensor entry specifies its data offsets as [start_byte, end_byte]
                    if "data_offsets" in info:
                        offsets = info["data_offsets"]
                        if len(offsets) == 2:
                            # Calculate absolute file position where this tensor ends
                            tensor_end_abs = data_start_offset + offsets[1]
                            if tensor_end_abs > max_end_offset:
                                max_end_offset = tensor_end_abs

                # If the actual physical file size is smaller than where the tensors claim to end, 
                # the file was cut off mid-download!
                if model_entry["size"] < max_end_offset:
                    raise ValueError(
                        f"CONTINUE_DOWNLOAD : {model_entry['size']} of {max_end_offset} bytes."
                    )
                # ------------------------------------------------

                model_entry["tensor_count"] = len(header_json) - metadata_offset
                model_entry["valid"] = True

        except (ValueError, KeyError, json.JSONDecodeError) as e:
            model_entry["valid"] = False
            model_entry["error"] = str(e)
        finally:
            pass

        return model_entry