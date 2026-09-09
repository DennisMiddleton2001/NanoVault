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
            "command"    : "PurgePipeline",
            "attempted"  : len(self.model_list),
            "successful" : int(0),
            "active"     : [],
            "download"   : [],
            "vault"      : [],
            "failed"     : [],
            "purged"     : [],
            "excluded"   : [],
            "message"    : "Purge in progress."
        }

        target_models = self.model_list
        print(f"{self.env.ico.get("SRCH",__class__)} Permanently removing {len(target_models)} models.")

        for model in target_models:
            model_entry = model
            model_name  = model['model_name']
            model_path  = model['model_path']

            
            # Hunt down and terminate the Active file
            active_fq_path = self.vault.get_active_fq_path(model_path, model_name)
            if os.path.exists(active_fq_path):
                os.remove(active_fq_path)
                print(f"{self.env.ico.get("DONE",__class__)} Trimmed from active.")
            else:
                print(f"{self.env.ico.get("DONE",__class__)} Not found in active.")

            # Check if the file is on the exclusion list.
            immune = self.immune_to_purge(model_name)
            if immune:
                print(f"{self.env.ico.get("LOCK",__class__)} File excluded from purge.")
                print(self.env.ico.sep(2))
                response["excluded"].append(model_name)
                response["successful"] += 1
                continue
            else:
                self.vault.free_vault_file(model_name)
                response["purged"].append(model_name)
                response["successful"] += 1
                print(self.env.ico.sep(2))
                continue

        print(f"{self.env.ico.get("DONE",__class__)} Purge complete.")

        if not response["successful"]:
            response["message"] = "Purge failed."
        elif response["successful"] != response["attempted"]:
            response ["message"] = "Purge completed with errors."
        else:
            response["message"] = "Purge successful"

        return response

