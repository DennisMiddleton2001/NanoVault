import os
import sys
import shutil

from .model_fetcher import ModelFetcher
from .vault_manager import VaultManager

class SpotDeploymentPipeline:

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
            model_name = model['name']
            model_subfolder = model['directory']
            url = model['url']

            # Check if model exists in active path.
            print(f"{self.env.ico.get("ACT",__class__)} Evaluating dependency '{model_subfolder}' '{model_name}'.")
            active_fq_path = self.vault.get_active_fq_path(model_subfolder, model_name)
            if os.path.exists(active_fq_path):
                print(f"{self.env.ico.get("DONE",__class__)} Exists in active configuration.")
                print(self.env.ico.sep(2))
                response['active'] += 1
                continue

            # "Hail Mary" check to see if NanoVault has a copy.
            print(f"{self.env.ico.get("ACT",__class__)} Checking NanoVault for '{model_name}'.")
            vault_fq_path = self.vault.get_valid_vault_fq_path(model_name)
            if vault_fq_path:
                print(f"{self.env.ico.get("ACT",__class__)} Located in NanoVault.")
                if self.vault.deploy_from_vault(model_subfolder, model_name):
                    print(f"{self.env.ico.get("BOX",__class__)} Deployed from Nanovault.")
                    print(self.env.ico.sep(2))
                    response['deployed'] += 1
                    continue
                else:
                    print(f"{self.env.ico.get("ACT",__class__)} Error deploying from NanoVault.")

            print(f"{self.env.ico.get('WRN',__class__)} Vault file not found.")
            cached_path = self.vault.get_staging_fq_path(model_name)
            if not os.path.exists(cached_path):
                cached_path = None
                print(f"{self.env.ico.get('ACT',__class__)} Downloading to cache.")
                cached_path = self.fetcher.download_to_cache(url, model_name, model_subfolder)
                if cached_path:
                    response["downloaded"] += 1

            if not os.path.exists(cached_path):
                print(f"{self.env.ico.get("ERR",__class__)} Download failed.")
                response["failed"] += 1
                continue

            print(f"{self.env.ico.get("DONE",__class__)} Performing spot deployment.")
            if not self.vault.deploy_from_cache(model_subfolder, model_name):
                print(f"{self.env.ico.get("ERR",__class__)} Deployment failed.")
                response['failed'] += 1
                continue

            response['deployed'] += 1
            print(f"{self.env.ico.get("DONE",__class__)} Spot deployment complete.")

            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))

        if response['failed']:
            response["message"] = "Deployment completed with errors."
        else:
            response["message"] = "Deployment completed."

        return response
