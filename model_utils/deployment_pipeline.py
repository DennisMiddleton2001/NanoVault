import os
import sys
import shutil

from .model_fetcher import ModelFetcher
from .vault_manager import VaultManager

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
        response = {
            "success"    : True,
            "command"    : "DeploymentPipeline",
            "message"    : "Deployment in progress.",
            "total"      : len(self.model_list),
            "active"     : 0,
            "downloaded" : 0,
            "deployed"   : 0,
            "failed"     : 0
        }

        print(self.env.ico.sep(1))
        for model in self.model_list:
            name = model['name']
            subfolder = model['directory']
            url = model['url']

            # Check if model exists in active path.
            print(f"{self.env.ico.get("ACT",__class__)} Evaluating dependency '{subfolder}' '{name}'.")
            active_fq_path = self.vault.get_active_fq_path(subfolder, name)
            if os.path.exists(active_fq_path):
                print(f"{self.env.ico.get("DONE",__class__)} Exists in active configuration.")
                print(self.env.ico.sep(2))
                response['active'] += 1
                continue

            # Check if model exists in NanoVault
            print(f"{self.env.ico.get("ACT",__class__)} Checking NanoVault for '{name}'.")
            vault_path = self.vault.get_valid_vault_fq_path(name)
            if vault_path:
                print(f"{self.env.ico.get("ACT",__class__)} Located in NanoVault.")
                if self.vault.deploy_from_vault(subfolder, name):
                    print(f"{self.env.ico.get("BOX",__class__)} Deployed from Nanovault.")
                    print(self.env.ico.sep(2))
                    response['deployed'] += 1
                    continue
                else:
                    print(f"{self.env.ico.get("ACT",__class__)} Error deploying from NanoVault.")

            # File doesn't exist in vault.  Fetch from URL.
            print(f"{self.env.ico.get('WRN',__class__)} Vault file not found.")
            
            cached_path = os.path.join(self.env.staging_cache, name)
            if os.path.exists(cached_path) and self.vault.validate_file_structure(cached_path):
                print(f"{self.env.ico.get("COMM",__class__)} Downloaded file found in cache.")
            else:
                cached_path = None
                print(f"{self.env.ico.get('ACT',__class__)} Downloading to cache.")
                cached_path = self.fetcher.download_to_cache(url, name, subfolder)

            if cached_path:
                if not self.vault.ingest_to_vault(cached_path, name, delete_source=True):
                    print(f"{self.env.ico.get("ERR",__class__)} Ingestion failed.")
                    response['failed'] += 1
                    continue

                response['downloaded'] += 1
                print(f"{self.env.ico.get("COMM",__class__)} Ingested from internet download.")
                print(f"{self.env.ico.get("ACT",__class__)} Starting deployment.")
                if not self.vault.deploy_from_vault(subfolder, name):
                    print(f"{self.env.ico.get("ERR",__class__)} Deployment failed.")
                    response["failed"] += 1
                    continue
                print(f"{self.env.ico.get("DONE",__class__)} Deployment complete.")
            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))

        if response['failed']:
            response["message"] = "Deployment completed with errors."
        else:
            response["message"] = "Deployment completed."

        return response
