import os
import json
import posixpath
from .vault_manager import VaultManager

class WorkflowParser:
    """Extracts required model assets using structured metadata, with a brute-force fallback."""

    def __init__(self, env=None, workflow_path=None):
        self.workflow_path = workflow_path
        self.valid_exts = ('.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.gguf', '.onnx', '.sft')
        self.env = env
        self.vault = VaultManager(self.env)

        # The universal router list
        self.known_folders = [
            "checkpoints", "diffusion_models", "unet", "loras",
            "text_encoders", "vae", "controlnet", "clip_vision",
            "clip", "upscale_models", "embeddings"
        ]

    def _guess_directory_from_url(self, url):
        """Slices a HuggingFace URL at a known ComfyUI folder and extracts the relative path."""
        if not url:
            return ""

        url_lower = url.lower()
        for folder in self.known_folders:
            search_str = f"/{folder}/"
            if search_str in url_lower:
                # 1. Find the starting index of the well-known folder (+1 to drop leading slash)
                idx = url_lower.find(search_str) + 1

                # 2. Slice from the folder name forward (preserving original casing)
                sliced_path = url[idx:]

                # 3. Let posixpath do the heavy lifting to split directory from filename
                directory, filename = posixpath.split(sliced_path)

                return directory

        return ""

    def get_required_models(self, workflow_path=None):
        models = self.get_required_models_ex(workflow_path)
        return models
    
    def get_required_models_ex(self, workflow_path=None):
        # Resolve the active path to use for this call
        target_path = workflow_path or self.workflow_path
        
        if not target_path:
            print(f"{self.env.ico('ERR', __class__)}  No workflow path specified.")
            return []

        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                try:
                    workflow = json.load(f)
                except KeyError as e:
                    print(f"{self.env.ico.get('ERR',__class__)} {target_path} - {e}.")
                    return []
        except Exception as e:
            print(f"{self.env.ico.get('ERR',__class__)} {e}")
            return []
        
        definitions = workflow.get("definitions", {})
        subgraphs = definitions.get("subgraphs", [])

        if subgraphs:
            nodes = subgraphs[0].get("nodes", [])
            models_dict = {}  # Track unique models by name to prevent duplication at the root

            for node in nodes:
                models = node.get("properties", {}).get("models")
                if isinstance(models, list):
                    for model in models:
                        name = model.get("name")
                        if name:
                            url = model.get("url", "")
                            directory = model.get("directory", "")

                            # If Manager gave us a URL but forgot the directory, route it!
                            if (not directory or len(directory) < 2) and url:
                                directory = self._guess_directory_from_url(url)

                            # Ensure exactly one instance per model name
                            if name not in models_dict:
                                models_dict[name] = {
                                    "name": name,
                                    "directory": directory,
                                    "url": url,
                                    "active_size" : int(self.get_active_size(directory, name)),
                                    "vault_size"  : int(self.get_vault_size(name))
                                }
                            else:
                                if url and not models_dict[name]["url"]:
                                    models_dict[name]["url"] = url
                                if directory and not models_dict[name]["directory"]:
                                    models_dict[name]["directory"] = directory

            # Done with loop. If the clean path actually found models, return them immediately as a unique list!
            if models_dict:
                return list(models_dict.values())
            else:
                return []


        models_dict = dict()

        def extract_models(data):
            # Do NOT initialize models_dict in here!
            if isinstance(data, dict):
                for value in data.values():
                    extract_models(value)
            elif isinstance(data, list):
                for item in data:
                    extract_models(item)
            elif isinstance(data, str):
                clean_data = data.strip(" \t\r\n\"'")

                # Ignore essays, allow URLs
                if '\n' in clean_data or len(clean_data) > 1024:
                    return

                if clean_data.lower().endswith(self.valid_exts):
                    is_url = "http://" in clean_data.lower() or "https://" in clean_data.lower()
                    clean_name = clean_data.split('/')[-1] if is_url else clean_data.strip("/\\")

                    if clean_name not in models_dict:
                        # Guess the directory from the URL if we have one
                        guessed_dir = self._guess_directory_from_url(clean_data) if is_url else ""

                        models_dict[clean_name] = {
                            "name": clean_name,
                            "directory": guessed_dir,
                            "url": clean_data if is_url else ""
                        }
                    else:
                        if is_url and not models_dict[clean_name]["url"]:
                            models_dict[clean_name]["url"] = clean_data
                            # If we didn't have a directory before, grab it now from the new URL
                            if not models_dict[clean_name]["directory"]:
                                models_dict[clean_name]["directory"] = self._guess_directory_from_url(clean_data)

        # 2. Kick off the recursion. It will populate the outer models_dict
        extract_models(workflow)
        
        # 3. Safely return the populated dictionary
        return list(models_dict.values())
    
    def scan_workflow_path(self, workflow_path=None, return_models=True):
        scan_results = list()

        target_dir = workflow_path
        # Basic scan for JSON files.
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith(".json"):
                    fq_path = os.path.join(root, file)
                    if return_models:
                        models = self.get_required_models(fq_path)
                    else:
                        models = []
                    
                    result = {
                        "fq_path" : fq_path,
                        "name" : file,
                        "active_size" : int(0),
                        "vault_size" : int(0),
                        "models" : models
                    }
                    for m in models:
                        # Freaking dev templates. Grrr!!!
                        try:
                            result['active_size'] += m['active_size']
                        except KeyError:
                            pass
                        try:
                            result['vault_size']  += m['vault_size']
                        except KeyError:
                            pass                        
                    scan_results.append(result)

        #self.print_workflow_folder_info(scan_results)
        return scan_results

    def print_workflow_folder_info(self, scan_results):
        # For debugging purposes
        for workflow in scan_results:
            name = workflow.get('name')
            print(f"\n")
            print(f"WORKFLOW: {name}")
            print(f"MODELS:")
            print(self.env.ico.sep(3,40))
            models = workflow.get('models')
            for m in models:
                name = m.get('name')
                path = m.get('path')
                print(f'   {name}')
            print(self.env.ico.sep(3,40))

    def get_active_size(self, model_folder, model_name):
        valid_active_fq_path = self.vault.valid_active_fq_path(model_folder, model_name)
        if not valid_active_fq_path:
            return 0
        else:
            return os.path.getsize(valid_active_fq_path)

    def get_vault_size(self, model_name):
        valid_vault_fq_path = self.vault.get_valid_vault_fq_path(model_name)
        if not valid_vault_fq_path:
            return 0
        else:
            return os.path.getsize(valid_vault_fq_path)
        