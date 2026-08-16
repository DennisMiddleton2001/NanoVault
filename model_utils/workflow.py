import os
import json
import posixpath
from .vault_manager import VaultManager

class WorkflowEnumerator:
    def __init__(self, env, workflow_root):
        vault = VaultManager()
        self.target_dir = workflow_root
        self.env = env

    def run(self):
        workflow_summary = list()
        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.lower().endswith(".json"):
                    fq_path = os.path.join(root, file)

                    workflow_models = WorkflowParser(self.env, fq_path).get_required_models()
                    
                    for model in workflow_models:
                        print(json.dumps(model, indent=2))
                        

                    workflow_summary.append(model)


        return workflow_summary


class WorkflowParser:
    def __init__(self, env=None, workflow_path = None):
        self.workflow_path = workflow_path
        self.workflow = None
        self.valid_exts = ('.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.gguf', '.onnx', '.sft')
        self.env = env
        self.vault = VaultManager(self.env)
        self.NODE_TYPE_TO_FOLDER = {
            "CheckpointLoaderSimple": "checkpoints",
            "UNETLoader": "unet",
            "VAELoader": "vae",
            "LTXVAudioVAELoader": "vae",
            "LoraLoader": "loras",
            "LTXLoraStackAV": "loras",
            "ControlNetLoader": "controlnet",
            "LatentUpscaleModelLoader": "upscale_models",
            "CLIPVisionLoader": "clip_vision",
            "CLIPLoader" : "clip",
            "LTXAVTextEncoderLoader": "clip",
            "LTXVGemmaCLIPModelLoader": "clip"
        }

        with open(self.workflow_path, 'r') as f:
            self.workflow = json.load(f)


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

    def get_required_models(self):
        model_list = list()
        model_list = self.get_workflow_requirements()
        for model in model_list:
            active = self.get_active_size(model["model_folder"], model['model_name'])
            vault  = self.get_vault_size(model['model_name'])
            model.update({"active" : active})
            model.update({"vault"  : vault})
        return model_list

    def get_workflow_requirements(self):
            models_found = []
            
            # The extensions we actually care about (Method 2 logic)
            VALID_EXTENSIONS = ('.safetensors', '.pt', '.ckpt', '.bin')

            # 1. Build the subgraph lookup map from BOTH potential ComfyUI locations
            subgraph_map = {}
            
            # Location A: Standard definitions (Method 1)
            definitions = self.workflow.get("definitions", {})
            for sg in definitions.get("subgraphs", []):
                subgraph_map[sg["id"]] = sg.get("nodes", [])
                
            # Location B: Custom/Extra DS Subgraphs (Method 2)
            extra_subgraphs = self.workflow.get("extra", {}).get("ds", {}).get("subgraphs", [])
            for sg in extra_subgraphs:
                sg_id = sg.get("id")
                if sg_id:
                    subgraph_map[sg_id] = sg.get("nodes", [])

            # 2. The recursive harvester
            def traverse_nodes(nodes):
                for node in nodes:
                    node_type = node.get("type")

                    # Base Case: It's a recognized model loader based on your master folder map
                    if node_type in self.NODE_TYPE_TO_FOLDER:
                        model_name = None
                        model_url = ''
                        
                        # Extraction Strategy: Aggressive scan for valid weight extensions 
                        widgets = node.get("widgets_values", [])
                        for val in widgets:
                            if isinstance(val, str) and val.endswith(VALID_EXTENSIONS):
                                model_name = val
                                break 
                        
                        # Fallback check inside named widgets just in case
                        if not model_name:
                            widgets_named = node.get("widgets_values_named", {})
                            for key, val in widgets_named.items():
                                if isinstance(val, str) and val.endswith(VALID_EXTENSIONS):
                                    model_name = val
                                    break

                        if model_name:
                            # Extract URL if available (Method 1 logic)
                            node_props = node.get("properties", {})
                            prop_models = node_props.get("models", [])
                            
                            for m in prop_models:
                                if m.get("name") == model_name:
                                    model_url = m.get("url")
                                    break

                            models_found.append({
                                "node_type": node_type,
                                "model_name": model_name,
                                "model_path": self.NODE_TYPE_TO_FOLDER[node_type],
                                "model_url": model_url
                            })

                    # Recursive Case: The node 'type' is actually a Subgraph UUID
                    elif node_type in subgraph_map:
                        traverse_nodes(subgraph_map[node_type])

            # 3. Kick off the scan using main canvas + any unmapped extra subgraph nodes
            root_nodes = self.workflow.get("nodes", [])
            
            # If any extra subgraphs didn't have IDs to map, dump them into root to be scanned flatly
            for sg in extra_subgraphs:
                if "id" not in sg:
                    root_nodes.extend(sg.get("nodes", []))

            traverse_nodes(root_nodes)

            # 4. Deduplicate the final list to optimize spot instance downloads
            unique_models = []
            seen_models = set()

            for model in models_found:
                # Create a unique signature for the file based on its target folder and name
                file_signature = f"{model['model_path']}/{model['model_name']}"
                
                if file_signature not in seen_models:
                    seen_models.add(file_signature)
                    unique_models.append(model)

            return unique_models