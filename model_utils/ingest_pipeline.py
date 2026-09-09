import os
from xml.parsers.expat import model
from .vault_manager import VaultManager

class IngestPipeline:

    def __init__(self, env = None, model_list = None):
        self.env = env
        self.vault = VaultManager(self.env)
        self.model_list = model_list
    
    def run(self):

        response = {
            "command"    : "IngestPipeline",
            "attempted"  : len(self.model_list),
            "successful" : int(0),
            "active"     : [],
            "download"   : [],
            "vault"      : [],
            "failed"     : [],
            "purged"     : [],
            "excluded"   : [],
            "message"    : "Ingest in progress."
        }

        print(f"{self.env.ico.get("SRCH",__class__)} Found {len(self.model_list)} model dependencies to evaluate.\n")

        print(self.env.ico.sep(1))
        for model in self.model_list:

            model_entry = model 
            model_name = model['model_name']
            model_path = model['model_path']

            active_fq_path = os.path.join(self.env.active_root, model_path, model_name)
            print(f"{self.env.ico.get("ACT",__class__)} '{model_name}' Evaluating model")

            # Step 1: Check if the file actually exists on the NVMe
            active_fq_path = self.vault.get_active_fq_path(model_path, model_name)
            if not os.path.exists(active_fq_path):
                print(f"{self.env.ico.get("WRN",__class__)} Model not found in active folder: {active_fq_path}")

                # Check to see if a valid copy exists in the vault.
                if self.vault.get_valid_vault_fq_path(model_name):
                    print(f"{self.env.ico.get("BOX",__class__)} Existing copy found in NanoVault.")
                    response["successful"] += 1
                    response["vault"].append(model_name)
                    print(self.env.ico.sep(2))
                    continue
                else:
                    print(f"{self.env.ico.get("ERR",__class__)} Model not found in NanoVault either.")
                    response["failed"].append(model_name)
                    print(self.env.ico.sep(2))
                    continue

            # Model was found on active NVMe save in active list.
            response["active"].append(model_name)

            # Check if VALIDATED model ALREADY in the NanoVault vault
            if self.vault.get_valid_vault_fq_path(model_name):
                print(f"{self.env.ico.get("BOX",__class__)} Existing copy found in NanoVault.")
                response["successful"] += 1
                response["vault"].append(model_name)
                print(self.env.ico.sep(2))
                continue

            # If not, ingest the model into the NanoVault without deleting the source file.
            if not self.vault.ingest_to_vault(active_fq_path, model_entry, delete_source=False):
                print(f"{self.env.ico.get('BOX',__class__)} Ingest failure.")
                response['failed'].append(model_name)
                print(self.env.ico.sep(2))
                continue
            else:
                response["successful"] += 1
                response["vault"].append(model_name)
                print(self.env.ico.sep(2))
                continue

        if not response["successful"]:
            response["message"] = "Ingest failed."
        elif response["attempted"] != response["successful"]:
            response["message"] = "Ingest completed with errors."
        else:
            response["message"] = "Ingest successful."

        return response


