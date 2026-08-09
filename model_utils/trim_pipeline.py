import os
import sys
import shutil

from model_utils.vault_manager import VaultManager
from model_utils.workflow import WorkflowParser

class TrimPipeline:
    def __init__(self, env = None):
        self.env = env
        self.vault = VaultManager(self.env)
    
    def run(self, workflow_path):
        parser = WorkflowParser(self.env, workflow_path)
        required_models = parser.get_required_models()

        if not required_models:
            print(f"{self.env.ico.get('ALRT',__class__)} No model definitions found.")
            return

        print(f"{self.env.ico.get('ACT',__class__)} TRIM: '{os.path.basename(workflow_path)}'")
        print(self.env.ico.sep(1))
        for model in required_models:
            name = model['name']
            subfolder = model['directory']
            active_path = os.path.join(self.env.active_root, subfolder, name)

            if not os.path.exists(active_path):
                print(f"{self.env.ico.get('DONE',__class__)} '{name}' Not on active NVMe.")
                print(self.env.ico.sep(2))
                continue

            # --- OPTIMIZED PRE-INGEST CHECK ---
            # If it's already in the vault, we just delete it without hashing
            vault_path = self.vault.find_in_vault(name)
            if vault_path:
                print(f"{self.env.ico.get('BOX',__class__)} '{name}' Secured in NanoVault.")
                print(f"{self.env.ico.get('DONE',__class__)} '{name}' Removed from active NVMe.")
                os.remove(active_path)
                print(self.env.ico.sep(2))
                continue
            else:
                print(f"{self.env.ico.get('ALRT',__class__)} '{name}' Not found in NanoVault.")
                print(f"{self.env.ico.get('INFO',__class__)} Found on NVMe. Updating NanoVault.")
                self.vault.ingest_to_vault(active_path, name, delete_source=True)
                print(f"{self.env.ico.get('BOX',__class__)} Secured in NanoVault.")
            print(self.env.ico.sep(2))
        print(self.env.ico.sep(1))
