import os
import sys

from model_utils.vault_manager import VaultManager
from model_utils.workflow import WorkflowParser

class PurgePipeline:
    """Orchestrates the complete and permanent removal of workflow assets from all storage."""
    def __init__(self, env = None):
        self.env = env
        self.vault = VaultManager(self.env)

    def run(self, workflow_path):
        parser = WorkflowParser(self.env, workflow_path)
        required_models = parser.get_required_models()

        if not required_models:
            print(f"{self.env.ico.get("ALRT",__class__)} Audit finished: No model definitions found.")
            sys.exit(1)
        else:
            print(f"{self.env.ico.get("SCAN",__class__)} Analyzing workflow dependencies for: {os.path.basename(workflow_path)}")


        print(f"{self.env.ico.get("WRN",__class__)} Initiating destructive eviction of: {os.path.basename(workflow_path)}")
        print(f"{self.env.ico.get("SRCH",__class__)} Found {len(required_models)} dependencies to permanently purge.")
        print(self.env.ico.sep(1))
        for model in required_models:
            
            name = model['name']
            subfolder = model['directory']
            active_path = os.path.join(self.env.active_root, subfolder, name)

            print(f"{self.env.ico.get("ACT",__class__)} '{name}' Evaluating purge.")

            # Step 1: Terminate the Active NVMe instance
            if os.path.exists(active_path):
                os.remove(active_path)
                print(f"{self.env.ico.get("DONE",__class__)} Purged from active.")
            else:
                print(f"{self.env.ico.get("DONE",__class__)} Not found in active.")

            # Step 2: Hunt down and terminate the Vault file & Sidecar
            vault_path = self.vault.find_in_vault(name)
            if vault_path:
                os.remove(vault_path)
                print(f"{self.env.ico.get("DONE",__class__)} Purged from NanoVault")

                sidecar_path = f"{vault_path}.xxh128"
                if os.path.exists(sidecar_path):
                    os.remove(sidecar_path)

                sidecar_path = f"{vault_path}.sha256"
                if os.path.exists(sidecar_path):
                    os.remove(sidecar_path)
                    print(f"{self.env.ico.get("DONE",__class__)} Purged NanoVault metadata.")
            else:
                print(f"{self.env.ico.get("ALRT",__class__)} File not present in NanoVault.")
            print(self.env.ico.sep(2))
        print(self.env.ico.sep(1))

