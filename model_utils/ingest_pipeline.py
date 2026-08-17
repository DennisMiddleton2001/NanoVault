import os
from .vault_manager import VaultManager

class IngestPipeline:

    def __init__(self, env = None, required_models = None):
        self.env = env
        self.vault = VaultManager(self.env)
        self.required_models = required_models
    
    def run(self):
        response = {
            "success"    : True,
            "command"    : "IngestPipeline",
            "message"    : "Ingest in progress.",
            "total"      : len(self.required_models),
            "secured"    : 0,
            "ingested"   : 0,
            "failed"     : 0,
            "not_active" : 0
        }

        print(f"{self.env.ico.get("SRCH",__class__)} Found {len(self.required_models)} model dependencies to evaluate.\n")

        print(self.env.ico.sep(1))
        for model in self.required_models:
            model_name = model['model_name']
            model_path = model['model_path']
            active_file_path = os.path.join(self.env.active_root, model_path, model_name)

            print(f"{self.env.ico.get("ACT",__class__)} '{model_name}' Evaluating model")

            # Step 1: Ensure the file actually exists on the NVMe
            active_file_path = self.vault.get_active_fq_path(model_path, model_name)
            if not os.path.exists(active_file_path):
                print(f"{self.env.ico.get("ALRT",__class__)} Not found on active. Cannot ingest.")
                if self.vault.get_valid_vault_fq_path(model_name):
                    print(f"{self.env.ico.get("BOX",__class__)} Existing copy secured in NanoVault.")
                    response["secured"] += 1
                    print(self.env.ico.sep(2))
                    continue

                response['not_active'] += 1
                print(self.env.ico.sep(2))
                continue

            # Step 2: Check if it's ALREADY in the NanoVault vault
            vault_path = self.vault.get_valid_vault_fq_path(model_name)
            if vault_path:
                print(f"{self.env.ico.get("BOX",__class__)} Secured in NanoVault.")
                response['secured']
                print(self.env.ico.sep(2))
                continue
            
            if not self.vault.ingest_to_vault(active_file_path, model_name, delete_source=False):
                print(f"{self.env.ico.get('BOX',__class__)} Ingest failure.")
                response['failed'] += 1
                print(self.env.ico.sep(2))
                continue
            response['ingested'] += 1
            print(self.env.ico.sep(2))
        print(self.env.ico.sep(1))

        if response["failed"]:
            response["message"] = "Ingest completed with errors."
        else:
            response["message"] = "Ingest complete."

        return response


