import os
from .vault_manager import VaultManager

class TrimPipeline:
    def __init__(self, env = None, model_list = None):
        self.env = env
        self.vault = VaultManager(self.env)
        self.model_list = model_list

    def run(self):
        response = {
            "success"    : True,
            "command"    : "TrimPipeline",
            "message"    : "Trim in progress.",
            "total"      : len(self.model_list),
            "missing"    : 0,
            "trimmed"    : 0,
            "secured"    : 0,
            "failed"     : 0
        }

        print(self.env.ico.sep(1))
        for model in self.model_list:

            name = model['name']
            subfolder = model['directory']
            active_path = self.vault.find_valid_active_file(subfolder, name)
            vault_path = self.vault.find_valid_vault_file(name)

            if not active_path:
                print(f"{self.env.ico.get('DONE',__class__)} '{name}' Not on active NVMe.")
    
                if not vault_path:
                    print(f"{self.env.ico.get('WRN',__class__)} '{name}' Not secured in Nanovault.")
                    response['missing'] += 1
                    print(self.env.ico.sep(2))
                    continue

            # Step 2: Check if it's ALREADY in the NanoVault vault
            if vault_path:
                print(f"{self.env.ico.get('BOX',__class__)} '{name}' Secured in NanoVault.")
                if active_path:
                    os.remove(active_path)
                    response['trimmed'] += 1
                    print(f"{self.env.ico.get('DONE',__class__)} Removed from active NVMe.")
                print(self.env.ico.sep(2))
                continue

            # Step 3: Ingest the model file into the NanoVault
            print(f"{self.env.ico.get('ALRT',__class__)} '{name}' Not found in NanoVault.")
            print(f"{self.env.ico.get('INFO',__class__)} Securing in NanoVault.")
            if not self.vault.ingest_to_vault(active_path, name, delete_source=True):
                print(f"{self.env.ico.get('ERR',__class__)} Unable to secure file to NanoVault.")
                response["failed"] += 1
                continue
            response['secured'] += 1
            print(f"{self.env.ico.get('BOX',__class__)} Secured in NanoVault.")
            print(self.env.ico.sep(2))
            continue
        print(self.env.ico.sep(1))

        if response['failed']:
            response['message'] = "Trim completed with errors."
        else:
            response['message'] = "Trim completed."

        return response
