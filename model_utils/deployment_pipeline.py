import os
import sys
import shutil

from model_utils.model_fetcher import ModelFetcher
from model_utils.load_model import LoadModel
from model_utils.vault_manager import VaultManager
from model_utils.workflow import WorkflowParser


class DeploymentPipeline:

    def __init__(self, env = None, model_list = None):

        self.env = env
        self.vault = VaultManager(self.env)
        self.fetcher = ModelFetcher(self.env)
        self.model_list = model_list
        self.url       = None
        self.subfolder = None
        self.name      = None

    def run(self):

        if not self.model_list:
            print(f"{self.env.ico.get("ALRT",__class__)} Audit finished: No model definitions found.")
            return

        print(self.env.ico.sep(1))
        for model in self.model_list:
            name = model['name']
            subfolder = model['directory']
            url = model['url']


            # Check if model exists in active path.
            print(f"{self.env.ico.get("ACT",__class__)} Evaluating dependency '{subfolder}' '{name}'.")
            if self.exists_in_active(subfolder, name):
                print(f"{self.env.ico.get("DONE",__class__)} Exists in active configuration.")
                print(self.env.ico.sep(2))
                continue

            # Check if model exists in NanoVault
            print(f"{self.env.ico.get("ACT",__class__)} Checking NanoVault for '{name}'.")
            vault_path = self.vault.find_in_vault(name)
            if vault_path:
                print(f"{self.env.ico.get("ACT",__class__)} Located in NanoVault.")
                self.vault.deploy_to_active(vault_path, subfolder, name)
                print(f"{self.env.ico.get("BOX",__class__)} Deployed from Nanovault.")
                print(self.env.ico.sep(2))
                continue

            # File doesn't exist.  Fetch from URL.
            print(f"{self.env.ico.get('WRN',__class__)} Local file not found.")
            print(f"{self.env.ico.get('ACT',__class__)} Downloading to cache.")

            cached_path = self.fetcher.download_to_cache(url, name, subfolder)
            if cached_path:
                if self.deploy_and_vault(cached_path, subfolder, name):
                    print(f"{self.env.ico.get("COMM",__class__)} Deployed from internet download.")
                else:
                    print(f"{self.env.ico.get("DONE",__class__)} Deployment failed.")
            else:
                print(f"{self.env.ico.get("DONE",__class__)} Download folder '{cached_path}' does not exist.")
            print(self.env.ico.sep(2))
        print(self.env.ico.sep(1))

    def exists_in_active(self, subfolder, name):
        
        active_path = os.path.join(self.env.active_root, subfolder, name)
        if not os.path.exists(active_path):
            return False
        
        print(f"{self.env.ico.get("DONE",__class__)} Already deployed.")
        return True

    def deploy_and_vault(self, cached_path, subfolder, name):

        # 1. Perform Structural Check
        print(f"{self.env.ico.get('SCAN',__class__)} '{name}' Checking tensor structure.")
        lm = LoadModel(self.env, cached_path)
        entry = lm.analyze()
        if not entry["valid"]:
            print(f"{self.env.ico.get('ERR',__class__)} '{name}' File structure invalid.")
            q_path = f"{cached_path}.QUARANTINED"
            shutil.move(cached_path, q_path)
            print(f"{self.env.ico.get('WRN',__class__)} Quarantined to '{q_path}'.")
            print(f"{self.env.ico.get('ERR',__class__)} Tensor file corrput.")
            return False

        print(f"{self.env.ico.get('DONE',__class__)} '{name}' Tensor structure validated.")
        
        # 2. Ingest to Vault (Moves file from cache to vault, cache is now empty)
        print(f"{self.env.ico.get('ACT',__class__)} Ingesting to NanoVault.")
        vault_path = self.vault.ingest_to_vault(cached_path, name)
        if not vault_path:
            print(f"{self.env.ico.get('ERR',__class__)} Ingest to vault failed.")
            return False
        
        print(f"{self.env.ico.get('DONE',__class__)} Ingestion complete.")

        # 3. Deploy to Active (Copies from vault to NVMe, original stays in vault)
        print(f"{self.env.ico.get('ACT',__class__)} Deploying to active.")
        if not self.vault.deploy_to_active(vault_path, subfolder, name):
            print(f"{self.env.ico.get('ERR',__class__)} Deploy to active failed.")
            return False
        
        print(f"{self.env.ico.get('DONE',__class__)} Deployed.")
        return True

    def download_and_deploy(self):
        #Download file to cache.
        print(f"{self.env.ico.get('ACT',__class__)} Download start.")
        cached_path = self.fetcher.download_to_cache(self.url, self.name, self.subfolder)
        if not cached_path:
            print(f"{self.env.ico.get('ERR',__class__)} Download failed.")
            return False

        return self.deploy_and_vault(cached_path, self.subfolder, self.name)
