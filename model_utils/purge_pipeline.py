import os
from .vault_manager import VaultManager

class PurgePipeline:
    #Orchestrates the complete and permanent removal of workflow assets from all storage.
    def __init__(self, env = None, model_list = None):
        self.env = env
        self.model_list = model_list
        self.vault = VaultManager(self.env)

    def immune_to_purge(self, name):
        return True if name in self.env.immutable else False

    # Runs the purge pipeline for a list of target models.
    def run(self):
        response = {
            "success"    : True,
            "command"    : "PurgePipeline",
            "message"    : "Purge in progress.",
            "total"      : len(self.model_list),
            "removed"    : 0,
            "excluded"   : 0,
            "failed"     : 0
        }

        target_models = self.model_list
        print(f"{self.env.ico.get("SRCH",__class__)} Permanently removing {len(target_models)} models.")

        for model in target_models:
            model_name        = model['name']
            model_subfolder   = model['directory']

            active_fq_path = self.vault.get_active_fq_path(model_subfolder, model_name)
            
            # Step 1: Hunt down and terminate the Active file
            if os.path.exists(active_fq_path):
                os.remove(active_fq_path)
                print(f"{self.env.ico.get("DONE",__class__)} Purged from active.")
            else:
                print(f"{self.env.ico.get("DONE",__class__)} Not found in active.")

            immune = self.immune_to_purge(model_name)
            if immune:
                print(f"{self.env.ico.get("LOCK",__class__)} File locked from purge.")
                response["excluded"] += 1
                continue

            if not self.vault.free_vault_file(model_name):
                print(f"{self.env.ico.get("ERR",__class__)} File was deleted out of band.")
                response["failed"] += 1
                print(self.env.ico.sep(2))
                continue

            print(f"{self.env.ico.get("DONE",__class__)} Purge complete.")
            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))
        if response["failed"]:
            response["message"] = "Purge completed with errors."
        else:
            response["message"] = "Purge completed."
        return response

