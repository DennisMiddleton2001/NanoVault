import os
import sys

from model_utils.vault_manager import VaultManager
from model_utils.load_model import LoadModel

class IngestPipeline:

    def __init__(self, env = None, required_models = None):
        self.env = env
        self.vault = VaultManager(self.env)
        self.required_models = required_models
    
    def run(self, delete_source=False):
        
        if not self.required_models:
            print(f"{self.env.ico.get("ALRT",__class__)} No model definitions found.")
            return False
        
        print(f"{self.env.ico.get("SRCH",__class__)} Found {len(self.required_models)} model dependencies to evaluate.\n")

        print(self.env.ico.sep(1))
        for model in self.required_models:
            name = model['name']
            subfolder = model['directory']
            active_file_path = os.path.join(self.env.active_root, subfolder, name)

            print(f"{self.env.ico.get("ACT",__class__)} '{name}' Evaluating model")

            # Step 1: Ensure the file actually exists on the NVMe
            if not os.path.exists(active_file_path):
                print(f"{self.env.ico.get("ALRT",__class__)} Not found on active. Cannot ingest.")
                print(self.env.ico.sep(2))
                continue

            # Step 2: Check if it's ALREADY in the NanoVault vault
            vault_path = self.vault.find_in_vault(name)

            if vault_path:
                print(f"{self.env.ico.get("DONE",__class__)} Found in NanoVault.")
                if not self.vault.read_sidecar(vault_path):
                    print(f"{self.env.ico.get("ALRT",__class__)} NanoVault metadata not found performing full validation.")
                    print(f"{self.env.ico.get("ACT",__class__)} Checking active file hash.")
                    active_hash = self.vault.calculate_hash(active_file_path)
                    print(f"{self.env.ico.get("KEY",__class__)} '{name}' [{active_hash}]")
                    vault_hash = self.vault.calculate_hash(vault_path)
                    print(f"{self.env.ico.get("KEY",__class__)} NanoVault [{active_hash}]")

                    if not vault_hash == active_hash:
                        print(f"{self.env.ico.get("KEY",__class__)} Hash mismatch. Unable to process file.")
                        continue

                    print(f"{self.env.ico.get("KEY",__class__)} Updating NanoVault metadata.")
                    self.vault.write_sidecar(vault_path, active_hash)

                print(f"{self.env.ico.get('BOX',__class__)} File secured in NanoVault.")
                print(self.env.ico.sep(2))
                continue

            # Step 3: Ingest the manually added file
            print(f"{self.env.ico.get('WRN',__class__)} Found on active but missing from NanoVault. Securing now...")

            # This moves the file from the NVMe to the Vault and creates the metadata
            new_vault_path = self.vault.ingest_to_vault(active_file_path, name, delete_source)

            print(self.env.ico.sep(2))
        print(self.env.ico.sep(1))

    #Perform ingest of a single model file.
    def single_ingest(self, delete_source=False):
            name = self.model_name
            subfolder = self.model_path
            active_path = os.path.join(self.env.active_root, subfolder, name)

            print(f"{self.env.ico.get("ACT",__class__)} '{name}' Evaluating model")

            # Step 1: Ensure the file actually exists on the NVMe
            if not os.path.exists(active_path):
                print(f"{self.env.ico.get("ALRT",__class__)} Active file not found.")

            # Step 2: Check if it's ALREADY in the NanoVault vault
            vault_path = self.vault.find_in_vault(name)
            if vault_path:
                print(f"{self.env.ico.get("DONE",__class__)} File present in NanoVault.")
                if not self.vault.read_sidecar(vault_path):
                    print(f"{self.env.ico.get("ALRT",__class__)} NanoVault file hash not found.")
                    h = self.vault.calculate_hash(active_path)
                    self.vault.write_sidecar(vault_path, h)
                    print(f"{self.env.ico.get('ACT',__class__)} NanoVault hash [{h}]")
                print(f"{self.env.ico.get('BOX',__class__)} File secured in NanoVault.")
                if delete_source and os.path.exists(active_path):
                    os.remove(active_path)
                    print(f"{self.env.ico.get('ALRT',__class__)} Model space freed from '{active_path}'.")
                return

            # Step 3: Ingest the manually added file
            print(f"{self.env.ico.get('WRN',__class__)} Active found but missing from NanoVault. Securing now...")
            
            # --- NEW QUARANTINE CHECK ---
            print(f"{self.env.ico.get('SRCH',__class__)} Validating tensor structure.")
            manifest = LoadModel(self.env, active_path).analyze()
            if not manifest["valid"]:
                print(f"{self.env.ico.get('ERR',__class__)} File is structurally invalid! Ingestion aborted.")
                print(f"       -> Details: {manifest['error']}")
                print(self.env.ico.sep(2))
                sys.exit(1)
            else:
                print(f"{self.env.ico.get('DONE',__class__)} Active file validated.")

            # This moves the file from the NVMe to the Vault and creates the metadata
            new_vault_path = self.vault.ingest_to_vault(active_path, name, delete_source)
         
