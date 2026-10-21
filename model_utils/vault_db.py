import os
import sys
import json
import uuid
from datetime import datetime, date, time, timedelta

class VaultDatabase:
    def __init__(self, vault_path, fast_hash = True):
        vault_filename = ".vault.json"
        self.fast_hash = fast_hash
        self.hash_type = "xxh128" if self.fast_hash else "sha256"
        self.vault_db_path = os.path.join(vault_path, vault_filename)
        if not self.read_vault_db():
                self.set_values()
                self.write_vault_db()

    def set_values(self,vault_data = {}):
        self.vault_id       = vault_data.get("vault_id", str(uuid.uuid4()))
        self.vault_sequence = vault_data.get("vault_sequence", 0)
        self.vault_created  = vault_data.get("vault_dts", str(datetime.now()))
        self.increment_vault_sequence()

    def get_vault_data_json(self):
        vault_data = {
            "vault_id": self.vault_id,
            "vault_sequence": self.vault_sequence,
            "vault_hash_type": self.hash_type,
            "fast_hash": self.fast_hash,
            "vault_dts": self.vault_created
        }
        return vault_data

    def write_vault_db(self):
        try:
            with open(self.vault_db_path, "w") as f:
                self.vault_sequence += 1
                vault_data = self.get_vault_data_json()
                json.dump(vault_data, f, indent=4)
        except Exception as e:
            print(f"{e}")
            return False
        return True

    def read_vault_db(self):
        try:
            with open(self.vault_db_path, "r") as f:
                try:
                    vault_data = json.load(f)
                except json.JSONDecodeError:
                    return False
        except Exception as e:
            print(f"{e}")
            return False
        
        self.set_values(vault_data)
        return True

    def increment_vault_sequence(self):
        vault_data = self.get_vault_data_json()
        if not self.write_vault_db():
            return None
        return self.vault_sequence

class SidecarFile:
    def __init__(
            self,
            vault_path,
            query_data={},
            fast_hash=True
            ):
        
        self.vault = VaultDatabase(vault_path, fast_hash)
        
        # Extract model_name to locate the sidecar file in the vault.
        # Handles both sparse queries ({"model_name": "..."}) and nested queries
        model_name = query_data.get("model_name") or query_data.get("model_entry", {}).get("model_name")
        if not model_name:
            raise ValueError("model_name is required in the query payload.")
            
        self.fq_model_path = os.path.join(vault_path, model_name)
        self.fq_sidecar_path = os.path.join(vault_path, f'{model_name}.{self.vault.hash_type}')

        # Isolate inbound metadata
        inbound_model_entry = query_data.get("model_entry", {})
        if "model_name" in query_data and not inbound_model_entry:
            inbound_model_entry = {k: v for k, v in query_data.items() if k not in ["workflows", "hash_value"]}
                # Remove sizes from model before creating the file.
    
        inbound_workflows = query_data.get("workflows", [])
        inbound_hash = query_data.get("hash_value")

        # Read sidecar and update, or instantiate new baseline
        if self.read_sidecar_info():
            current_entry = self.sidecar_info.get("model_entry", {})
            current_entry.update(inbound_model_entry)
            self.sidecar_info["model_entry"] = current_entry
            
            for wf in inbound_workflows:
                self.add_workflow(wf)
                
            if inbound_hash:
                self.set_hash(inbound_hash)
        else:
            self.sidecar_info = {
                "vault_data": self.vault.get_vault_data_json(),
                "model_entry": inbound_model_entry,
                "workflows": inbound_workflows
            }
            if inbound_hash:
                self.sidecar_info["hash_value"] = inbound_hash

    def sidecar_exists(self):
        return True if os.path.exists(self.fq_sidecar_path) else False

    def delete_sidecar(self):
        if self.sidecar_exists():
            os.remove(self.fq_sidecar_path)

    def model_exists(self):
        return os.path.exists(self.fq_model_path) if True else False

    def delete_model(self):
        if self.model_exists():
            os.remove(self.fq_model_path)

    def set_model_entry(self, model_entry):
        if "model_entry" not in self.sidecar_info:
            self.sidecar_info["model_entry"] = {}
        self.sidecar_info["model_entry"].update(model_entry)

    def add_workflow(self, workflow_entry):
        workflow_id = workflow_entry.get("workflow_id")
        revision = workflow_entry.get("revision")
        workflow_names = workflow_entry.get("workflow_names", [])
        workflow_name = workflow_names[0] if workflow_names else "Unnamed"

        if "workflows" not in self.sidecar_info:
            self.sidecar_info["workflows"] = []

        workflow_list = self.sidecar_info["workflows"]

        if not workflow_list:
            workflow_list.append(workflow_entry)
            return

        found = False
        for entry in workflow_list:
            if entry.get("workflow_id") == workflow_id and entry.get("revision") == revision:
                found = True
                if workflow_name not in entry.get("workflow_names", []):
                    entry.setdefault("workflow_names", []).append(workflow_name)
                break
                
        if not found:
            workflow_list.append(workflow_entry)
        
    def reset_workflows(self):
        self.sidecar_info["workflows"] = []
    
    def set_hash(self, hash_value):
        self.sidecar_info["hash_value"] = hash_value

    def get_hash(self):
        return self.sidecar_info.get("hash_value", None)

    def match_hash(self, hash_value):
        return self.sidecar_info.get("hash_value") == hash_value

    def read_sidecar_info(self):
        try:
            with open(self.fq_sidecar_path, "r") as f:
                self.sidecar_info = json.load(f)
        except Exception:
            return False
        return True

    def write_sidecar_info(self):
        try:
            with open(self.fq_sidecar_path, "w") as f:
                json.dump(self.sidecar_info, f, indent=4)
        except Exception:
            return False
        return True
        self.fq_model_path = os.path.join(vault_path, model_name)
        self.fq_sidecar_path = os.path.join(vault_path, f'{model_name}.{self.vault.hash_type}')

        # Isolate inbound metadata
        inbound_model_entry = query_data.get("model_entry", {})
        if "model_name" in query_data and not inbound_model_entry:
            inbound_model_entry = {k: v for k, v in query_data.items() if k not in ["workflows", "hash_value"]}
            
        inbound_workflows = query_data.get("workflows", [])
        inbound_hash = query_data.get("hash_value")

        # Read sidecar and update, or instantiate new baseline
        if self.read_sidecar_info():
            current_entry = self.sidecar_info.get("model_entry", {})
            current_entry.update(inbound_model_entry)
            self.sidecar_info["model_entry"] = current_entry
            
            for wf in inbound_workflows:
                self.add_workflow(wf)
                
            if inbound_hash:
                self.set_hash(inbound_hash)
        else:
            self.sidecar_info = {
                "vault_data": self.vault.get_vault_data_json(),
                "model_entry": inbound_model_entry,
                "workflows": inbound_workflows
            }
            if inbound_hash:
                self.sidecar_info["hash_value"] = inbound_hash

    def delete_sidecar(self):
        if os.path.exists(self.fq_sidecar_path):
            os.remove(self.fq_sidecar_path)

    def delete_model(self):
        if os.path.exists(self.fq_model_path):
            os.remove(self.fq_model_path)

    def set_model_entry(self, model_entry):
        if "model_entry" not in self.sidecar_info:
            self.sidecar_info["model_entry"] = {}

        self.sidecar_info["model_entry"].update(model_entry)
        self.sidecar_info["model_entry"].pop("active_size", "0")
        self.sidecar_info["model_entry"].pop("vault_size", "0")

    def add_workflow(self, workflow_entry):
        if not workflow_entry:
            return
        
        workflow_id = workflow_entry.get("workflow_id")
        revision = workflow_entry.get("revision")
        workflow_names = workflow_entry.get("workflow_names", [])
        workflow_name = workflow_names[0] if workflow_names else "Unnamed"

        if "workflows" not in self.sidecar_info:
            self.sidecar_info["workflows"] = []

        workflow_list = self.sidecar_info["workflows"]

        if not workflow_list:
            workflow_list.append(workflow_entry)
            self.write_sidecar_info()
            return

        found = False

        for entry in workflow_list:
            if entry.get("workflow_id") == workflow_id and entry.get("revision") == revision:
                found = True
                if workflow_name not in entry.get("workflow_names", []):
                    entry.setdefault("workflow_names", []).append(workflow_name)
                    self.write_sidecar_info()
                break
                
        if not found:
            workflow_list.append(workflow_entry)
            self.write_sidecar_info()
        return
        
    def reset_workflows(self):
        self.sidecar_info["workflows"] = []
    
    def set_hash(self, hash_value):
        self.sidecar_info["hash_value"] = hash_value

    def get_hash(self):
        return self.sidecar_info.get("hash_value", None)

    def match_hash(self, hash_value):
        return self.sidecar_info.get("hash_value") == hash_value

    def read_sidecar_info(self):
        try:
            with open(self.fq_sidecar_path, "r") as f:
                self.sidecar_info = json.load(f)
        except Exception:
            return False
        return True

    def write_sidecar_info(self):
        try:
            with open(self.fq_sidecar_path, "w") as f:
                json.dump(self.sidecar_info, f, indent=4)
        except Exception:
            return False
        return True
