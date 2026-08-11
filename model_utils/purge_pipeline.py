import os
from model_utils.vault_manager import VaultManager

class PurgePipeline:
    #Orchestrates the complete and permanent removal of workflow assets from all storage.
    def __init__(self, env = None, model_list = None):
        self.env = env
        self.model_list = model_list
        self.vault = VaultManager(self.env)

    # Runs the purge pipeline for a list of target models.
    def run(self):
        response = {
            "success"    : True,
            "command"    : "PurgePipeline",
            "message"    : "Purge in progress.",
            "total"      : len(self.model_list),
            "removed"    : 0,
            "failed"     : 0
        }

        target_models = self.model_list
        print(f"{self.env.ico.get("SRCH",__class__)} Permanently removing {len(target_models)} models.")

        for model in target_models:
            name        = model['name']
            subfolder   = model['directory']

            active_path = self.vault.find_valid_active_file(subfolder, name)
            
            # Step 1: Hunt down and terminate the Active file
            if active_path:
                os.remove(active_path)
                print(f"{self.env.ico.get("DONE",__class__)} Purged from active.")
            else:
                print(f"{self.env.ico.get("DONE",__class__)} Not found in active.")

            if not self.vault.free_vault_file(name):
                print(f"{self.env.ico.get("ERR",__class__)} File was deleted out of band.")
                response["failed"] += 1
                print(self.env.ico.sep(2))
                continue

            print(f"{self.env.ico.get("DONE",__class__)} Purged NanoVault metadata.")
            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))
        if response["failed"]:
            response["message"] = "Purge completed with errors."
        else:
            response["message"] = "Purge completed."
        return response

