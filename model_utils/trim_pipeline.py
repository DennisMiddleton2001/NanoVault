import os
from model_utils.vault_manager import VaultManager

class TrimPipeline:
    def __init__(self, env = None, model_list = None):
        self.env = env
        self.vault = VaultManager(self.env)
        self.model_list = model_list

    def run(self):
        if not self.model_list:
            print(f"{self.env.ico.get('ALRT',__class__)} No model definitions found.")
            return False

        print(self.env.ico.sep(1))
        for model in self.model_list:
            name = model['name']
            subfolder = model['directory']
            active_path = os.path.join(self.env.active_root, subfolder, name)

            # Step 1: Ensure the file actually exists on the NVMe
            if not os.path.exists(active_path):
                print(f"{self.env.ico.get('DONE',__class__)} '{name}' Not on active NVMe.")
                print(self.env.ico.sep(2))
                continue

            # Step 2: Check if it's ALREADY in the NanoVault vault
            vault_path = self.vault.find_in_vault(name)
            if vault_path:

                print(f"{self.env.ico.get('BOX',__class__)} '{name}' Secured in NanoVault.")
                if os.path.exists(active_path):
                    os.remove(active_path)
                print(f"{self.env.ico.get('DONE',__class__)} Removed from active NVMe.")

                print(self.env.ico.sep(2))
                continue

            # Step 3: Ingest the model file into the NanoVault
            print(f"{self.env.ico.get('ALRT',__class__)} '{name}' Not found in NanoVault.")

            print(f"{self.env.ico.get('INFO',__class__)} Securing in NanoVault.")
            self.vault.ingest_to_vault(active_path, name, delete_source=True)
            print(f"{self.env.ico.get('BOX',__class__)} Secured in NanoVault.")

            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))
        return True
