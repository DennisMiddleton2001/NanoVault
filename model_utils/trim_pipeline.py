import os
from .vault_manager import VaultManager

class TrimPipeline:
    def __init__(self, env = None, model_list = None):
        self.env = env
        self.vault = VaultManager(self.env)
        self.model_list = model_list

    def run(self):
        response = {
            "command"    : "TrimPipeline",
            "attempted"  : len(self.model_list),
            "successful" : int(0),
            "active"     : [],
            "download"   : [],
            "vault"      : [],
            "failed"     : [],
            "purged"     : [],
            "excluded"   : [],
            "message"    : "Trim in progress."
        }

        print(self.env.ico.sep(1))
        for model in self.model_list:
            model_entry = model
            model_name = model['model_name']
            model_path = model['model_path']
            # This has the side effect of writing the model_subfolder to the NanoVault metadata.
            active_fq_path = self.vault.get_active_fq_path(model_path, model_name)
            valid_vault_fq_path = self.vault.get_valid_vault_fq_path(model_name)

            #If not active or vaulted, trim automatically fails.
            if not active_fq_path:
                print(f"{self.env.ico.get('DONE',__class__)} '{model_name}' Not on active NVMe.")
                if not valid_vault_fq_path:
                    print(f"{self.env.ico.get('WRN',__class__)} '{model_name}' Not secured in Nanovault.")
                    print(self.env.ico.sep(2))
                    response['failed'].append(model_name)
                    continue

            # Check to see if it's ALREADY in the NanoVault
            if valid_vault_fq_path:
                print(f"{self.env.ico.get('BOX',__class__)} '{model_name}' Secured in NanoVault.")

                #Mark this model as vaulted.
                response['vault'].append(model_name)

                # Delete the active file.
                valid_active_fq_path = self.vault.valid_active_fq_path(model_path, model_name)
                if valid_active_fq_path:
                    os.remove(valid_active_fq_path)
                    print(f"{self.env.ico.get('DONE',__class__)} Removed from active NVMe.")
                print(self.env.ico.sep(2))

                #Mark this as successful.
                response['successful'] += 1
                continue

            # We have an active copy, but no vault file.
            print(f"{self.env.ico.get('ALRT',__class__)} '{model_name}' Not found in NanoVault.")
            print(f"{self.env.ico.get('INFO',__class__)} Securing in NanoVault.")

            # The active file is probably corrupted if this fails.
            if not self.vault.ingest_to_vault(active_fq_path, model_entry, delete_source=True):
                print(f"{self.env.ico.get('ERR',__class__)} Unable to secure file.")
                response["failed"].append(model_name)
                print(self.env.ico.sep(1))
                continue

            #Everything is good.
            print(f"{self.env.ico.get('BOX',__class__)} Secured in NanoVault.")
            print(self.env.ico.sep(2))
            response['successful'] += 1
            response['vault'].append(model_name)
            print(self.env.ico.sep(1))
            continue

        if not response['successful']:
            response['message'] = "Trim failed."
        elif response['successful'] != response['attempted']:
            response['message'] = "Trim completed with errors."
        else:
            response['message'] = "Trim successful."

        return response
