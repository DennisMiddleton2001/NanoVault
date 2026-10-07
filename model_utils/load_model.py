import os
import json
import struct

# --- GGUF SPECIFIC CONSTANTS ---
GGML_TYPES = {
    0:  (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20), 6: (32, 22), 7: (32, 24),
    8:  (32, 34), 9: (32, 36), 10: (256, 84), 11: (256, 110), 12: (256, 144),
    13: (256, 176), 14: (256, 210), 15: (256, 292), 16: (256, 66), 17: (256, 74),
    18: (256, 98), 19: (256, 50), 20: (32, 18), 21: (256, 110), 22: (256, 82),
    23: (256, 136), 24: (1, 1), 25: (1, 2), 26: (1, 4), 27: (1, 8), 28: (1, 8),
    29: (256, 56), 30: (1, 2)
}

_SCALAR = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?",
           10: "Q", 11: "q", 12: "d"}

class GGUFReader:
    # Big thanks to community member for the GGUF header parsing logic. This class is a sequential reader for GGUF headers, optimized to skip heavy metadata.
    """Sequential reader for GGUF headers, optimized to skip heavy metadata."""
    def __init__(self, fh):
        self.fh = fh
        self.pos = 0

    def raw(self, n):
        b = self.fh.read(n)
        if len(b) != n:
            raise ValueError("file ends inside the header")
        self.pos += n
        return b

    def scalar(self, fmt):
        return struct.unpack("<" + fmt, self.raw(struct.calcsize(fmt)))[0]

    def string(self):
        return self.raw(self.scalar("Q")).decode("utf-8", "replace")

    def skip(self, n):
        self.fh.seek(n, os.SEEK_CUR)
        self.pos += n

    def value(self, vtype, keep=True):
        if vtype in _SCALAR:
            v = self.scalar(_SCALAR[vtype])
            return v if keep else None
        if vtype == 8:
            n = self.scalar("Q")
            if keep: return self.raw(n).decode("utf-8", "replace")
            self.skip(n)
            return None
        if vtype == 9:
            elem, count = self.scalar("I"), self.scalar("Q")
            if not keep and elem in _SCALAR:
                self.skip(count * struct.calcsize(_SCALAR[elem]))
                return None
            out = [self.value(elem, keep) for _ in range(count)]
            return out if keep else None
        raise ValueError("unknown metadata value type %d" % vtype)


class SafetensorCheck:
    def __init__(self, file_path, debug=False):
        self.file_path = file_path
        self.debug = debug

    def verify(self, model_entry):
        with open(self.file_path, 'rb') as f:
            header_size_bytes = f.read(8)
            if len(header_size_bytes) < 8:
                raise ValueError("File is too small to be a valid safetensors file.")

            header_size = struct.unpack('<Q', header_size_bytes)[0]
            if header_size > 100_000_000:
                raise ValueError("Invalid header size.")

            header_bytes = f.read(header_size)
            header_json = json.loads(header_bytes.decode('utf-8'))

            if self.debug:
                model_entry["metadata"] = header_json.get("__metadata__", {})

            data_start_offset = 8 + header_size
            max_end_offset = data_start_offset
            metadata_offset = 1 if "__metadata__" in header_json else 0
            
            for key, info in header_json.items():
                if key == "__metadata__":
                    continue
                if "data_offsets" in info:
                    offsets = info["data_offsets"]
                    if len(offsets) == 2:
                        tensor_end_abs = data_start_offset + offsets[1]
                        if tensor_end_abs > max_end_offset:
                            max_end_offset = tensor_end_abs

            if model_entry["size"] < max_end_offset:
                raise ValueError(f"CONTINUE_DOWNLOAD : {model_entry['size']} of {max_end_offset} bytes.")

            model_entry["tensor_count"] = len(header_json) - metadata_offset
            model_entry["valid"] = True
            model_entry["status"] = "verified"
            
        return model_entry


class GgufCheck:
    def __init__(self, file_path, debug=False):
        self.file_path = file_path
        self.debug = debug

    def verify(self, model_entry):
        with open(self.file_path, "rb") as fh:
            r = GGUFReader(fh)
            if r.raw(4) != b"GGUF":
                raise ValueError("not a GGUF file")
            
            version = r.scalar("I")
            n_tensors = r.scalar("Q")
            n_kv = r.scalar("Q")

            alignment = 32
            for _ in range(n_kv):
                key = r.string()
                vtype = r.scalar("I")
                val = r.value(vtype, keep=(key == "general.alignment"))
                if key == "general.alignment":
                    alignment = val

            far_off, far_end = 0, 0
            for _ in range(n_tensors):
                r.string()
                dims = [r.scalar("Q") for _ in range(r.scalar("I"))]
                type_id = r.scalar("I")
                offset = r.scalar("Q")
                
                if type_id not in GGML_TYPES:
                    raise ValueError(f"unknown ggml type {type_id}")
                
                block, size = GGML_TYPES[type_id]
                n = 1
                for d in dims: n *= d
                if n % block:
                    raise ValueError(f"element count {n} not a multiple of block {block}")
                
                t_bytes = n // block * size
                
                if offset >= far_off:
                    far_off, far_end = offset, offset + t_bytes

            header_end = r.pos

        data_start = (header_end + alignment - 1) // alignment * alignment
        expected = data_start + (far_end + alignment - 1) // alignment * alignment

        if model_entry["size"] < expected:
            raise ValueError(f"CONTINUE_DOWNLOAD : {model_entry['size']} of {expected} bytes.")
        
        model_entry["tensor_count"] = n_tensors
        model_entry["valid"] = True
        model_entry["status"] = "verified"
        
        return model_entry


# --- MAIN ORCHESTRATOR ---

class LoadModel:

    def __init__(self, env=None, file_path=None, debug=False):
        self.env = env
        self.file_path = file_path
        self.debug = debug

    def print_json(self, headers):
        output = json.dumps(headers, indent=4)
        print(output)

    def analyze(self):
        return self.check_model_fq_path()

    def check_active_model(self, model_subfolder, model_name):
        self.file_path = os.path.join(self.env.active_root, model_subfolder, model_name)
        return self.check_model_fq_path()

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

    def check_model_fq_path(self, file_path=None):
        if file_path:
            self.file_path = file_path
        else:
            file_path = self.file_path

        model_entry = {
            "fq_path": self.file_path,
            "valid": False,
            "status": "unchecked", 
            "error": None,
            "size" : int(0),
            "tensor_count": int(0),
            "metadata": {}
        }
       
        try:
            if not os.path.exists(self.file_path):
                 raise ValueError("File not found.")

            model_entry["size"] = os.path.getsize(self.file_path)
            if model_entry["size"] < 1024:
                 raise ValueError("Not a tensor file.")

            ext = os.path.splitext(self.file_path)[1].lower()

            # --- ROUTER LOGIC ---
            if ext == ".safetensors":
                checker = SafetensorCheck(self.file_path, self.debug)
                model_entry = checker.verify(model_entry)
                
            elif ext == ".gguf":
                checker = GgufCheck(self.file_path, self.debug)
                model_entry = checker.verify(model_entry)

            else:
                if self.debug and self.env and hasattr(self.env, 'ico'):
                    print(f"{self.env.ico.get('WRN', __class__)} Format {ext} unsupported for truncation check.")
                model_entry["valid"] = True
                model_entry["status"] = "unchecked"

        except (ValueError, KeyError, json.JSONDecodeError, struct.error) as e:
            model_entry["valid"] = False
            model_entry["status"] = "failed"
            model_entry["error"] = str(e)

        return model_entry