import os
import sys
import shutil

from .model_fetcher import ModelFetcher
from .vault_manager import VaultManager

class DeploymentPipeline:

    def __init__(self, env = None, model_list = None, spot_install = False):

        self.env = env
        self.spot_install = spot_install
        self.vault = VaultManager(self.env)
        self.fetcher = ModelFetcher(self.env)
        self.model_list = model_list
        self.url       = None
        self.subfolder = None
        self.name      = None

    def run(self):
        response = {
            "command"    : "DeploymentPipeline" if not self.spot_install else "SpotDeploymentPipeline",
            "attempted"  : len(self.model_list),
            "successful" : int(0),
            "active"     : [],
            "download"   : [],
            "vault"      : [],
            "failed"     : [],
            "purged"     : [],
            "excluded"   : [],
            "message"    : "Deployment in progress."
        }

        print(self.env.ico.sep(1))
        for model in self.model_list:
            model_entry = model
            model_name = model['model_name']
            model_subfolder = model['model_path']
            model_url = model['model_url']

            # Check if model exists in active path.
            print(f"{self.env.ico.get("ACT",__class__)} Evaluating dependency '{model_subfolder}' '{model_name}'.")
            active_fq_path = self.vault.get_active_fq_path(model_subfolder, model_name)
            if os.path.exists(active_fq_path):
                model_entry = self.vault.validate_file_structure(active_fq_path)
                if (model_entry['valid']):
                    print(f"{self.env.ico.get("DONE",__class__)} Exists in active configuration.")
                    print(self.env.ico.sep(2))
                    response['active'].append(model_name)
                    response["successful"] += 1
                    continue
                else:
                    print(f"{self.env.ico.get("WRN",__class__)} Exists, but corrupted in active configuration.")
                    os.remove(active_fq_path)

            # Check if model exists in NanoVault
            print(f"{self.env.ico.get("ACT",__class__)} Checking NanoVault for '{model_name}'.")
            vault_path = self.vault.get_valid_vault_fq_path(model_name)
            if vault_path and os.path.exists(vault_path):
                print(f"{self.env.ico.get("ACT",__class__)} Located in NanoVault.")
                if self.vault.deploy_from_vault(model_subfolder, model_name):
                    print(f"{self.env.ico.get("BOX",__class__)} Deployed from Nanovault.")
                    print(self.env.ico.sep(2))
                    response["vault"].append(model_name)
                    response["successful"] += 1
                    continue
                else:
                    # Don't set failed here.  We can still recover.
                    print(f"{self.env.ico.get("ACT",__class__)} Error deploying from NanoVault.")

            # File doesn't exist in vault. Not a failure yet.
            print(f"{self.env.ico.get('WRN',__class__)} Valid vault file not found.")

            # See if we downloaded it completely or partially.
            staging_fq_path = self.vault.get_staging_fq_path(model_name)

            if not os.path.exists(staging_fq_path):
                # If the file doesn't exist in the cache, it's easy. Just download it.
                staging_fq_path = self.fetcher.download_to_cache(model_url, model_name, model_subfolder)
            else:
                # If it does exist, we need to know whether it's worth continuing the download or deleting it.
                cache_model_entry = self.vault.validate_file_structure(staging_fq_path)
                if not cache_model_entry["valid"] and cache_model_entry["error"].find("CONTINUE_DOWNLOAD") >= 0:
                    print(f"{self.env.ico.get("COMM",__class__)} Truncated tensor found, continuing download.")
                elif not cache_model_entry["valid"]:
                    print(f"{self.env.ico.get("WRN",__class__)} Corrupted download found. Attempting new download.")
                    os.remove(staging_fq_path)
            
                if not cache_model_entry["valid"]:
                    if not len(model_url):
                        print(f"{self.env.ico.get("WRN",__class__)} No download url. Checking download cache folder.")
                    else:
                        print(f"{self.env.ico.get('COMM',__class__)} Downloading to cache.")
                    staging_fq_path = self.fetcher.download_to_cache(model_url, model_name, model_subfolder)

            if not staging_fq_path or not os.path.exists(staging_fq_path):
                print(f"{self.env.ico.get("ERR",__class__)} Missing or invalid file in download cache.")
                response["failed"].append(model_name)
                print(self.env.ico.sep(2))
                continue

            # Skip vault ingest if spot install.
            if not self.spot_install:
                if not self.vault.ingest_to_vault(staging_fq_path, model_entry, delete_source=True):
                    print(f"{self.env.ico.get("ERR",__class__)} Ingestion failed.")
                    response["failed"].append(model_name)
                    print(self.env.ico.sep(2))
                    continue
                print(f"{self.env.ico.get("COMM",__class__)} Ingested from internet download.")

            print(f"{self.env.ico.get("ACT",__class__)} Starting deployment.")

            if not self.spot_install:
                if not self.vault.deploy_from_vault(model_subfolder, model_name):
                    print(f"{self.env.ico.get("ERR",__class__)} Deployment failed.")
                    response["failed"].append(model_name)
                    print(self.env.ico.sep(2))
                    continue
            else:
                if not self.vault.deploy_from_cache(model_subfolder, model_name):
                    print(f"{self.env.ico.get("ERR",__class__)} Deployment failed.")
                    response["failed"].append(model_name)
                    print(self.env.ico.sep(2))
                    continue

            print(f"{self.env.ico.get("DONE",__class__)} Deployment complete.")
            response["download"].append(model_name)
            response["successful"] += 1
            print(self.env.ico.sep(2))

        print(self.env.ico.sep(1))

        if not response['successful']:
            response["message"] = "Deployment failed."
        elif response['successful'] != response['attempted']:
            response["message"] = "Deployment completed with errors."
        else:
            response["message"] = "Deployment successful."

        return response
