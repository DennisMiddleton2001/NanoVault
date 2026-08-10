import os
import json
import posixpath

class WorkflowParser:
    """Extracts required model assets using structured metadata, with a brute-force fallback."""

    def __init__(self, env=None, workflow_path=None):
        self.workflow_path = workflow_path
        self.valid_exts = ('.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.gguf', '.onnx', '.sft')
        self.env = env

        if not os.path.exists(self.workflow_path):
            print(f"{self.env.ico.get('ERR',__class__)} Error: Workflow template missing at '{self.workflow_path}'")
            return

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

    def get_required_models(self):

        with open(self.workflow_path, 'r', encoding='utf-8') as f:
            try:
                workflow = json.load(f)
            except json.JSONDecodeError:
                print(f"{self.env.ico.get("ERR",__class__)} Error: Failed to parse workflow JSON format.")
                return []

        # --- TIER 1: The Clean Path (ComfyUI-Manager Metadata) ---
        definitions = workflow.get("definitions", {})
        subgraphs = definitions.get("subgraphs", [])

        if subgraphs:
            nodes = subgraphs[0].get("nodes", [])
            models_to_restore = []

            for node in nodes:
                models = node.get("properties", {}).get("models")
                if isinstance(models, list):
                    for model in models:
                        name = model.get("name")
                        if name:
                            url = model.get("url", "")
                            directory = model.get("directory", "")

                            # If Manager gave us a URL but forgot the directory, route it!
                            if not directory and url:
                                directory = self._guess_directory_from_url(url)

                            models_to_restore.append({
                                "name": name,
                                "directory": directory,
                                "url": url
                            })

            # If the clean path actually found models, return them immediately!
            if models_to_restore:
                return models_to_restore

        # --- TIER 2: The Brute-Force Fallback (Native ComfyUI Export) ---
        # If we reach this point, the file has no manager metadata. Unleash the crawler.
        models_dict = {}

        def extract_models(data):
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

        extract_models(workflow)
        return list(models_dict.values())
