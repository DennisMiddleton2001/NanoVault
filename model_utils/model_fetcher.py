import os
import subprocess
from model_utils.log_icons import LogIcons
ico = LogIcons()

# Manages multi-connection network operations.
class ModelFetcher:
    def __init__(self, env = None):
        self.env = env

    # Download model to a cache folder defined by 'environement.json'.
    def download_to_cache(self, url, model_name, target_dir):

        staged_file_path = os.path.join(self.env.staging_cache, model_name)
        print(f"{ico.get('COMM',__class__)} Starting download.")
                
        wget_cmd = ["wget", "-c", "-O", staged_file_path]
        match url:
            case "huggingface.co":
                if len(self.env.hf_token) > 8:
                    print(f"{ico.get('KEY',__class__)} HF URL detected. Injecting Authorization header '{self.env.hf_token[:10]}...'")
                    wget_cmd.append(f"--header=Authorization: Bearer {self.env.hf_token}")
            case "civitai.com":
                if len(self.env.civitai_token) > 8:
                    print(f"{ico.get('KEY',__class__)} CivitAI URL detected. Injecting Authorization header '{self.env.hf_token[:10]}...'")
                    wget_cmd.append(f"--header=Authorization: Bearer {self.env.civitai_token}")

        wget_cmd.append(url)

        try:
            print(self.env.ico.sep(4))
            print(f"{ico.get('COMM',__class__)} COMMAND: {wget_cmd}.")
            print(self.env.ico.sep(4))
            subprocess.run(wget_cmd, check=True)
        except subprocess.CalledProcessError:
            print(f"{ico.get('ERR',__class__)} DOWNLOAD FAILED")
            print(f"MODEL    : {model_name}")
            print(f"DIRECTORY: {target_dir}")
            print(f"URL      : {url}")
            staged_file_path = None
        print(self.env.ico.sep(3))
        
        return staged_file_path

        
