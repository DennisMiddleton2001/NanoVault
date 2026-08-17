import os
import json
import posixpath
from .vault_manager import VaultManager

class WorkflowEnumerator:
    def __init__(self, env, workflow_root):
        self.env = env
        self.vault = VaultManager(self.env)
        self.workflow_root = workflow_root

    def run(self):

        all_workflows = list()

        for root, _, files in os.walk(self.workflow_root):

            for file in files:
                if file.lower().endswith(".json"):

                    fq_path = os.path.join(root, file)
                    models = WorkflowParser(self.env, fq_path).get_required_models()

                    worflow_entry = {
                        "name"        : file,
                        "fq_path"     : fq_path,
                        "active_size" : int(0),
                        "vault_size"  : int(0),
                        "models"      : models
                    }

                    for m in models:
                        worflow_entry["vault_size"] += m["vault_size"]
                        worflow_entry["active_size"] += m["active_size"]

                else:
                    continue
                all_workflows.append(worflow_entry)
           
        return all_workflows

class WorkflowParser:
    def __init__(self, env=None, fq_path = None):
        
        self.fq_path = fq_path
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

        with open(self.fq_path, 'r') as f:
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
        model_list = self.get_workflow_model_list()
        for model in model_list:
            # Aggregate sizes
            active_size = self.get_active_size(model["model_path"], model['model_name'])
            vault_size  = self.get_vault_size(model['model_name'])

            model.update({"active_size" : active_size})
            model.update({"vault_size"  : vault_size})
        if not len(model_list):
            print("HALT!!!")
        return model_list

    def get_workflow_model_list(self):
        models_found = []
        VALID_EXTENSIONS = ('.safetensors', '.pt', '.ckpt', '.bin')

        # 1. Build the subgraph lookup map from BOTH potential ComfyUI locations
        subgraph_map = {}
        
        definitions = self.workflow.get("definitions", {})
        for sg in definitions.get("subgraphs", []):
            subgraph_map[sg["id"]] = sg.get("nodes", [])
            
        extra_subgraphs = self.workflow.get("extra", {}).get("ds", {}).get("subgraphs", [])
        for sg in extra_subgraphs:
            sg_id = sg.get("id")
            if sg_id:
                subgraph_map[sg_id] = sg.get("nodes", [])

        # 2. The completely autonomous & DEFENSIVE recursive harvester
        def traverse_nodes(nodes):
            if not nodes:
                return
                
            for node in nodes:
                node_type = node.get("type")

                # Block pure text nodes from being scanned for extensions
                if node_type in {"MarkdownNote", "Note", "PrimitiveString"}:
                    continue

                # Recursive Case: The node 'type' is actually a Subgraph UUID
                if node_type in subgraph_map:
                    traverse_nodes(subgraph_map[node_type])
                    continue

                model_name = None
                model_url = ''
                model_path = None
                
                # DEFENSIVE: Protect against "widgets_values": null in JSON
                widgets = node.get("widgets_values")
                if not widgets: 
                    widgets = []
                    
                # Extraction Strategy: Scan untyped widget arrays 
                for val in widgets:
                    if isinstance(val, str) and val.endswith(VALID_EXTENSIONS):
                        if '\n' in val:
                            continue
                        model_name = val.replace('\\', '/')
                        break 
                
                # Fallback check inside named widgets
                if not model_name:
                    # DEFENSIVE: Protect against "widgets_values_named": null
                    widgets_named = node.get("widgets_values_named")
                    if not widgets_named:
                        widgets_named = {}
                        
                    for key, val in widgets_named.items():
                        if isinstance(val, str) and val.endswith(VALID_EXTENSIONS):
                            if '\n' in val:
                                continue
                            model_name = val.replace('\\', '/')
                            break

                if model_name:
                    # Search the node's properties for the URL and Target Directory
                    node_props = node.get("properties") or {}
                    prop_models = node_props.get("models") or []
                    
                    for m in prop_models:
                        # Normalize the property name just in case it also has Windows slashes
                        prop_name = m.get("name", "").replace('\\', '/')
                        
                        if prop_name == model_name:
                            model_url = m.get("url") or ''
                            model_path = m.get("directory")
                            break

                    # If the node didn't provide a directory, fallback to your master dictionary
                    if not model_path:
                        # Safely call self.NODE_TYPE_TO_FOLDER just in case it's missing
                        folder_map = getattr(self, 'NODE_TYPE_TO_FOLDER', {})
                        model_path = folder_map.get(node_type, "models")

                    models_found.append({
                        "node_type": node_type,
                        "model_name": model_name,
                        "model_path": model_path,
                        "model_url": model_url
                    })

        # 3. Kick off the scan using main canvas + any unmapped extra subgraph nodes
        root_nodes = self.workflow.get("nodes", [])
        for sg in extra_subgraphs:
            if "id" not in sg:
                root_nodes.extend(sg.get("nodes", []))

        traverse_nodes(root_nodes)

        # 4. Deduplicate the final list to optimize spot instance downloads
        unique_models = []
        seen_models = set()

        for model in models_found:
            file_signature = f"{model['model_path']}/{model['model_name']}"
            if file_signature not in seen_models:
                seen_models.add(file_signature)
                unique_models.append(model)

        return unique_models

   
        models_found = []
        
        # The extensions we actually care about
        VALID_EXTENSIONS = ('.safetensors', '.pt', '.ckpt', '.bin')

        # 1. Build the subgraph lookup map from BOTH potential ComfyUI locations
        subgraph_map = {}
        
        # Location A: Standard definitions
        definitions = self.workflow.get("definitions", {})
        for sg in definitions.get("subgraphs", []):
            subgraph_map[sg["id"]] = sg.get("nodes", [])
            
        # Location B: Custom/Extra DS Subgraphs
        extra_subgraphs = self.workflow.get("extra", {}).get("ds", {}).get("subgraphs", [])
        for sg in extra_subgraphs:
            sg_id = sg.get("id")
            if sg_id:
                subgraph_map[sg_id] = sg.get("nodes", [])

        # 2. The completely autonomous recursive harvester
        # 2. The completely autonomous recursive harvester
        def traverse_nodes(nodes):
            for node in nodes:
                node_type = node.get("type")

                # Block pure text nodes from being scanned for extensions
                if node_type in {"MarkdownNote", "Note", "PrimitiveString"}:
                    continue

                # Recursive Case: The node 'type' is actually a Subgraph UUID
                if node_type in subgraph_map:
                    traverse_nodes(subgraph_map[node_type])
                    continue

                # Base Case: Aggressively scan EVERY node for model extensions
                model_name = None
                model_url = ''
                model_path = None
                
                # Extraction Strategy: Scan untyped widget arrays 
                widgets = node.get("widgets_values", [])
                for val in widgets:
                    if isinstance(val, str) and val.endswith(VALID_EXTENSIONS):
                        # Sanity check: Ensure it's not a multi-line paragraph masquerading as a file
                        if '\n' in val:
                            continue
                        
                        # Normalize Windows backslashes into standard Unix forward slashes
                        model_name = val.replace('\\', '/')
                        break 
                
                # Fallback check inside named widgets
                if not model_name:
                    widgets_named = node.get("widgets_values_named", {})
                    for key, val in widgets_named.items():
                        if isinstance(val, str) and val.endswith(VALID_EXTENSIONS):
                            if '\n' in val:
                                continue
                            model_name = val.replace('\\', '/')
                            break
                
        def traverse_nodes_original(nodes):
            for node in nodes:
                node_type = node.get("type")

                # Recursive Case: The node 'type' is actually a Subgraph UUID
                if node_type in subgraph_map:
                    traverse_nodes(subgraph_map[node_type])
                    continue

                # Base Case: Aggressively scan EVERY node for model extensions
                model_name = None
                model_url = ''
                model_path = None
                
                # Extraction Strategy: Scan untyped widget arrays 
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
                    # Search the node's properties for the URL and Target Directory!
                    node_props = node.get("properties", {})
                    prop_models = node_props.get("models", [])
                    
                    for m in prop_models:
                        if m.get("name") == model_name:
                            model_url = m.get("url") or ''
                            model_path = m.get("directory") # The workflow tells us where it goes
                            break

                    # If the node didn't provide a directory, fallback to your master dictionary
                    if not model_path:
                        # Default to "models" if it's a totally unknown custom node missing metadata
                        model_path = self.NODE_TYPE_TO_FOLDER.get(node_type, "models")

                    models_found.append({
                        "node_type": node_type,
                        "model_name": model_name,
                        "model_path": model_path,
                        "model_url": model_url
                    })

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