import os
import sys

from model_utils.vault_manager import VaultManager

class PurgePipeline:
    #Orchestrates the complete and permanent removal of workflow assets from all storage.
    def __init__(self, env = None, model_list = None):
        self.env = env
        self.model_list = model_list
        self.vault = VaultManager(self.env)

    # Runs the purge pipeline for a list of target models.
    def run(self):
        target_models = self.model_list
        if not target_models:
            print(f"{self.env.ico.get("ERR",__class__)} Audit finished: No model definitions found.")
            return False
                
        print(f"{self.env.ico.get("SRCH",__class__)} Permanently removing {len(target_models)} models.")

        for model in target_models:
            name        = model['name']
            subfolder   = model['directory']
            active_path = os.path.join(self.env.active_root, subfolder, name)

            # Step 1: Hunt down and terminate the Active file
            print(f"{self.env.ico.get("ACT",__class__)} '{name}' Evaluating purge.")
            if os.path.exists(active_path):
                os.remove(active_path)
                print(f"{self.env.ico.get("DONE",__class__)} Purged from active.")
            else:
                print(f"{self.env.ico.get("DONE",__class__)} Not found in active.")

            # Step 2: Hunt down and terminate the Vault file & Sidecar
            vault_path = self.vault.find_in_vault(name)
            if os.path.exists(vault_path):
                os.remove(vault_path)
                print(f"{self.env.ico.get("DONE",__class__)} Purged from NanoVault")

                print(f"{self.env.ico.get("ACT",__class__)} '{name}' Removing vault metadata.")
                sidecar_path = self.vault.get_sidecar_path(vault_path)
                if os.path.exists(sidecar_path):
                    os.remove(sidecar_path)
                print(f"{self.env.ico.get("DONE",__class__)} Purged NanoVault metadata.")
            else:
                print(f"{self.env.ico.get("ALRT",__class__)} File not present in NanoVault.")

            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))

        return True 

