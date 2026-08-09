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
        self.command = None
        argc = len(sys.argv)

        if argc == 2:
            self.command = sys.argv[1]
        
        if self.command in ['--scan-vault']:
            self.target_dir = os.path.abspath(self.env.vault_dir)
        elif self.command in ['--scan-active']:
            self.target_dir = os.path.abspath(self.env.active_root)
        elif self.command in ['--cleanup']:
            self.target_dir = os.path.abspath(self.env.active_root)

        print(f"{self.env.ico.get("SRCH")} Scanning '{self.target_dir}'")
        if not os.path.exists(self.target_dir):
            print(f"{self.env.ico.get("ERR")} Path not found '{self.target_dir}'.")
            sys.exit(1)

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

    def test_sweep(self):
        self.run()
        if self.command not in ['--cleanup']:
            self.print_report()
        print(self.env.ico.sep(1))

    def delete_mismatch(self, root, name):
        active_path = os.path.join(root, name)
        vault_path  = os.path.join(self.env.vault_dir, name)
        
        exists_in_active = os.path.exists(active_path)
        exists_in_vault  = os.path.exists(vault_path)

        marked = 0

        if exists_in_active and not exists_in_vault:
            print(f"{self.env.ico.get("INFO")} Removing '{active_path}'.")
            yn = input(f"Confirm Delete (Y/n):")
            if (yn.lower() in ['y', 'yes','']):
                os.remove(active_path)
                marked = 1
            else:
                marked = -1
        
        return marked
            
    def run(self):
        if not os.path.exists(self.target_dir):
            return self.manifest

        ingest_list = list()

        for root, _, files in os.walk(self.target_dir):
            

            for file in files:
                if file.lower().endswith(".safetensors"):
                    fq_path = os.path.join(root, file)
                    if self.command in ['--cleanup']:
                        deleted = self.delete_mismatch(root, file)
                        if deleted == -1:
                            ingest_list.append(f"python {sys.argv[0]} --si {root} {file}")
                    else:
                        loader = LoadModel(self.env, fq_path)
                        entry = loader.analyze()
                        self.manifest.append(entry)

        if len(ingest_list):
            print("Suggested ingest list...")
            for l in ingest_list:
                print(l)
                            


