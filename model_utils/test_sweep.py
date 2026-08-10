import os
import sys
import math
import math

from load_model import LoadModel

# Lambda function to calculate the log scale unit
human_size = lambda s: f"{s / (1024 ** (i := int(math.log(s, 1024) if s > 0 else 0))):.2f} {['B','KB','MB','GB','TB'][i]}"

class AnalyzeModelsFolder:

    def __init__(self, env=None):
        self.env = env
        self.manifest = list()

    def analyze_vault(self):
        self.target_dir = os.path.abspath(self.env.vault_dir)
        return self.run(vault=True)

    def analyze_active(self):
        self.target_dir = os.path.abspath(self.env.active_root)
        return self.run(vault=False)

    def print_report(self):
        print(f"{self.env.ico.get("SCAN")} Tensor Report")
        print(self.env.ico.sep(1))

        storage_size = 0

        for entry in self.manifest:

            size = os.path.getsize(entry["fq_path"])
            storage_size += size

            print(self.env.ico.sep(2))
            if entry["valid"]:
                print(f"{self.env.ico.get("DONE")}  | VALID - {entry['fq_path']}")
                print(f"     TensorCount {entry['tensor_count']} Size [{human_size(size)}]")
                
            else:
                print(f"{self.env.ico.get("ERR")} {entry['error']} - {entry['fq_path']}")
                print(f"     Size [{human_size(size)}]")
                print(f"     Re-download or check vault with test_sweep.py /vault/path/folder/")

        print(self.env.ico.sep(2))
        print(f"{self.env.ico.get("INFO")} Model Storage Size {human_size(storage_size)}")

    def run(self, vault=False):
        scan_results = list()

        self.target_dir = self.env.active_root if not vault else self.env.vault_dir

        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.lower().endswith(".safetensors"):
                    fq_path = os.path.join(root, file)
                    loader = LoadModel(self.env, fq_path)

                    if (vault):
                        entry = loader.check_vault_model(file)
                    else:
                        entry = loader.check_model_fq_path(fq_path)
                        
                    self.manifest.append(entry)

        return self.manifest


