import os
import sys
import json
import uuid
from datetime import datetime, date, time, timedelta

class VaultDatabase:
    def __init__(self, vault_path):
        vault_filename = ".vault.json"
        self.vault_db_path = os.path.join(vault_path, vault_filename)
        
        if not self.read_vault_db():
                self.set_values({})
                self.write_vault_db()                    

    def set_values(self,vault_data = {}):
        try:
            now = str(datetime.now())
            self.vault_id       = vault_data.get("vault_id", str(uuid.uuid4()))
            self.vault_sequence = vault_data.get("vault_sequence", 0)
            self.vault_created  = vault_data.get("vault_dts", now)
            self.active_dts     = vault_data.get("active_dts", now)
        except:
            return False

        return True

    def write_vault_db(self):
        now = str(datetime.now())
        try:
            with open(self.vault_db_path, "w") as f:
                vault_data = {
                    "vault_id": self.vault_id,
                    "vault_sequence": self.vault_sequence,
                    "vault_dts": f"{self.vault_created}",
                    "active_dts": f"{now}"
                }
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

        return self.set_values(vault_data=vault_data)

    def increment_vault_sequence(self):
        self.vault_sequence += 1
        if not self.write_vault_db():
            return None
        return self.vault_sequence

class SidecarFile:
    def __init__(
            self, 
            vault_path, 
            model_name,
            node_type='', 
            model_subfolder='',
            model_url='',
            hash_value='', 
            fast_hash=True,
            workflows=[]):

        self.vault = VaultDatabase(vault_path) if vault_path else None
        self.set_default_info(
            model_name, 
            node_type, 
            model_subfolder, 
            model_url, 
            hash_value, 
            fast_hash, 
            workflows)
        
        self.fq_sidecar_path = os.path.join(vault_path,f'{model_name}.{self.sidecar_info["file_info"]["hash_type"]}')
        if not self.read_sidecar_info():
            self.write_sidecar_info()

    def set_default_info(
            self, 
            model_name,
            node_type='', 
            model_subfolder='',
            model_url='',
            hash_value='', 
            fast_hash=True,
            workflows=[]):

        self.sidecar_info = {
            "file_info": {
                "vault_id" : self.vault.vault_id,
                "model_name" : model_name,
                "hash_value": hash_value,
                "hash_type" : "xxh-128" if fast_hash else "sha-256",
                "model_name": model_name,
                "model_subfolder": model_subfolder,
                "node_type": node_type,
            }
        }

    def add_workflow(self, workflow_id, revision, workflow_name):
        workflow_entry = {
            "workflow_id": workflow_id,
            "revision": revision,
            "workflow_names": [workflow_name]
        }
        
        try:
            workflow_list = self.sidecar_info["file_info"]["workflows"]
        except KeyError:
            self.sidecar_info["file_info"].update({"workflows" : []})

        workflow_list = self.sidecar_info["file_info"]["workflows"]

        if not len(workflow_list):
            workflow_list.append(workflow_entry)
            return

        for entry in workflow_list:
            if entry["workflow_id"] == workflow_id and entry["revision"] == revision:
                if workflow_name in entry["workflow_names"]:
                    continue
                else:
                    entry["workflow_names"].append(workflow_name)

        found = False
        for entry in workflow_list:
            if entry["workflow_id"] == workflow_id and entry["revision"] == revision:
                found = True
                
        if not found:
            workflow_list.append(workflow_entry)
        

    def reset_workflows(self):
        self.sidecar_info["file_info"]["workflows"] = []
    
    def set_hash(self, hash_value):
        self.sidecar_info["file_info"]["hash_value"] = hash_value

    def match_hash(self, hash_value):
        return self.sidecar_info["file_info"]["hash_value"] == hash_value

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

'''
workflow_id="e3f2b845-8f2c-4b5a-9caf-eac1029d3e7e"
revision = "0"
node_type = "CLIPLoader"
model_subfolder = "text_encoders"
node_type = "UNETLoader"
valid_hash = "d152f5b2101816dcc64b6cf419c4d590"
invalid_hash = "d152f5b2101816dcc64b6cf419c43590"
model_name = "qwen_image_2.1.safetensors"
url = "https://www.somewhere?download=True"
db = 'test/vault'

sc = SidecarFile(db, model_name)
for i in range(0,2):
    sc.add_workflow(workflow_id,revision,f"/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/H3_CUSTOM_{i}.json")
    sc.write_sidecar_info()
    sc.add_workflow(workflow_id,revision,f"/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/H3_CUSTOM_{i}.json")
    sc.reset_workflows()
    sc.write_sidecar_info()

sc.add_workflow(workflow_id,f"{revision}1",f"/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/H3_CUSTOM_{i}.json")
sc.write_sidecar_info()
sc.add_workflow(workflow_id,f"{revision}1",f"/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/H3_CUSTOM_{i}.json")
sc.add_workflow(workflow_id,f"{revision}1",f"/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/H3_CUSTOM_{i}.json")
sc.add_workflow(workflow_id,f"{revision}1",f"/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/H3_CUSTOM_{i}.json")
sc.write_sidecar_info()

sc.set_hash(invalid_hash)
if not sc.match_hash(valid_hash):
    sc.set_hash(valid_hash)
    sc.write_sidecar_info()

if not sc.match_hash(valid_hash):
    sc.set_hash(valid_hash)
    sc.write_sidecar_info()

sc.write_sidecar_info()

'''