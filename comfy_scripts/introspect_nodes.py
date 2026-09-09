import json
import os
import sys
import folder_paths
import nodes

def build_node_folder_map():
    # Ensure custom nodes are loaded
    nodes.init_extra_nodes()

    registry = {}
    known_folders = set(folder_paths.folder_names_and_paths.keys())

    for node_name, node_cls in nodes.NODE_CLASS_MAPPINGS.items():
        if not hasattr(node_cls, "INPUT_TYPES"):
            continue
        try:
            inputs = node_cls.INPUT_TYPES()
            all_inputs = {**inputs.get("required", {}), **inputs.get("optional", {})}

            for param_name, param_spec in all_inputs.items():
                if isinstance(param_spec, tuple) and len(param_spec) > 0:
                    first_arg = param_spec[0]

                    # Direct string folder key match
                    if isinstance(first_arg, str) and first_arg in known_folders:
                        registry[node_name] = first_arg
                        break

                    # Match against filename lists provided by folder_paths
                    elif isinstance(first_arg, list) and first_arg:
                        matched = False
                        for folder_key in known_folders:
                            known_files = folder_paths.get_filename_list(folder_key)
                            if known_files and set(first_arg).issubset(set(known_files)):
                                registry[node_name] = folder_key
                                matched = True
                                break
                        if matched:
                            break
        except Exception:
            continue

    return registry

if __name__ == "__main__":
    folder_map = build_node_folder_map()
    
    with open(os.path.join(os.path.dirname(__file__), "../NanoVault/node_folder_map.json"), "w") as f:
        json.dump(build_node_folder_map(), f, indent=4)
