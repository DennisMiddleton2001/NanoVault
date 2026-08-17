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
            model_name = model['model_name']
            model_subfolder = model['model_path']
            model_url = model['model_url']

            # Check if model exists in active path.
            print(f"{self.env.ico.get("ACT",__class__)} Evaluating dependency '{model_subfolder}' '{model_name}'.")
            active_fq_path = self.vault.get_active_fq_path(model_subfolder, model_name)
            if os.path.exists(active_fq_path):
                print(f"{self.env.ico.get("DONE",__class__)} Exists in active configuration.")
                print(self.env.ico.sep(2))
                response['active'] += 1
                continue

            # Check if model exists in NanoVault
            print(f"{self.env.ico.get("ACT",__class__)} Checking NanoVault for '{model_name}'.")
            vault_path = self.vault.get_valid_vault_fq_path(model_name)
            if vault_path:
                print(f"{self.env.ico.get("ACT",__class__)} Located in NanoVault.")
                if self.vault.deploy_from_vault(model_subfolder, model_name):
                    print(f"{self.env.ico.get("BOX",__class__)} Deployed from Nanovault.")
                    print(self.env.ico.sep(2))
                    response['deployed'] += 1
                    continue
                else:
                    print(f"{self.env.ico.get("ACT",__class__)} Error deploying from NanoVault.")

            # File doesn't exist in vault.  Fetch from URL.
            print(f"{self.env.ico.get('WRN',__class__)} Vault file not found.")
            
            staging_fq_path = self.vault.get_staging_fq_path(model_name)
            if os.path.exists(staging_fq_path) and self.vault.validate_file_structure(staging_fq_path):
                print(f"{self.env.ico.get("COMM",__class__)} Downloaded file found in cache.")
            else:
                staging_fq_path = None
                print(f"{self.env.ico.get('ACT',__class__)} Downloading to cache.")
                staging_fq_path = self.fetcher.download_to_cache(model_url, model_name, model_subfolder)

            if staging_fq_path:
                if not self.vault.ingest_to_vault(staging_fq_path, model_name, delete_source=True):
                    print(f"{self.env.ico.get("ERR",__class__)} Ingestion failed.")
                    response['failed'] += 1
                    continue

                response['downloaded'] += 1
                print(f"{self.env.ico.get("COMM",__class__)} Ingested from internet download.")
                print(f"{self.env.ico.get("ACT",__class__)} Starting deployment.")
                if not self.vault.deploy_from_vault(model_subfolder, model_name):
                    print(f"{self.env.ico.get("ERR",__class__)} Deployment failed.")
                    response["failed"] += 1
                    continue

                response['deployed'] += 1
                print(f"{self.env.ico.get("DONE",__class__)} Deployment complete.")
            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))

        if response['failed']:
            response["message"] = "Deployment completed with errors."
        else:
            response["message"] = "Deployment completed."

        return response
