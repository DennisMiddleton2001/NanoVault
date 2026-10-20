import os
import sys
import json
import hashlib
import xxhash
import shutil
from .load_model import LoadModel
from .vault_db import SidecarFile

class VaultManager:
    
    def __init__(self, env = None, workflow_data = None):
        self.env = env
        self.id = workflow_data.get("id", 0) if workflow_data else 0
        self.revision = workflow_data.get("revision", 0) if workflow_data else 0
        self.workflow_name = workflow_data.get("workflow_name", "") if workflow_data else ""
        
    def clean(self, path):
        return path.strip(' \t\n\r"\'')

    def get_fq_vault_path(self, model_name):
        return self.clean(os.path.join(self.env.vault_dir, model_name))

    def get_model_subfolder(self, fq_path, model_name):
        tag = 'ComfyUI/models/'
        start_idx = fq_path.find(tag) + len(tag)
        path_and_name = fq_path[start_idx:]
        if path_and_name.endswith(model_name):
            subfolder = path_and_name[:-len(model_name)-1]
        return self.clean(subfolder)

    def get_active_fq_path(self, model_subfolder, model_name):
        return self.clean(os.path.join(self.env.active_root, model_subfolder, model_name))

    def get_staging_fq_path(self, model_name):
        return self.clean(os.path.join(self.env.staging_cache, model_name))

    def _get_hasher(self):
        """Returns the appropriate hasher instance based on fast_hash configuration."""
        return xxhash.xxh128() if self.env.fast_hash else hashlib.sha256()

    def calculate_xxh_hash(self, model_fq_path, chunk_size=8388608):
        hash_method = xxhash.xxh128()
        with open(model_fq_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_method.update(chunk)
        return hash_method.hexdigest()

    def calculate_sha_hash(self, model_fq_path, chunk_size=4096*1024):
        hash_method = hashlib.sha256()
        with open(model_fq_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_method.update(chunk)
        return hash_method.hexdigest()

    def calculate_hash(self, model_fq_path):
        return self.calculate_xxh_hash(model_fq_path) if self.env.fast_hash else self.calculate_sha_hash(model_fq_path)

    def robust_copy_and_verify(self, src_path, dst_path, chunk_size=8388608):
        src_hasher = self._get_hasher()
        tmp_dst_path = f"{dst_path}.tmp"

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        # 1. Stream copy to .tmp and calculate source hash concurrently
        try:
            with open(src_path, 'rb') as fsrc, open(tmp_dst_path, 'wb') as fdst:
                while chunk := fsrc.read(chunk_size):
                    src_hasher.update(chunk)
                    fdst.write(chunk)
                fdst.flush()
                os.fsync(fdst.fileno())
        except Exception as e:
            print(f"{self.env.ico.get('ERR', __class__)} Transfer failed during write: {e}")
            if os.path.exists(tmp_dst_path):
                try:
                    os.remove(tmp_dst_path)
                except Exception:
                    pass
            return False, None, None

        source_digest = src_hasher.hexdigest()

        # 2. Independent read-back pass over .tmp destination to verify physical media
        dst_hasher = self._get_hasher()
        try:
            with open(tmp_dst_path, 'rb') as fdst:
                while chunk := fdst.read(chunk_size):
                    dst_hasher.update(chunk)
        except Exception as e:
            print(f"{self.env.ico.get('ERR', __class__)} Transfer failed during readback: {e}")
            if os.path.exists(tmp_dst_path):
                try:
                    os.remove(tmp_dst_path)
                except Exception:
                    pass
            return False, source_digest, None

        dest_digest = dst_hasher.hexdigest()
        is_valid = (source_digest == dest_digest)

        # 3. Rename on success, purge on failure
        if is_valid:
            try:
                # Remove existing file if replacing an active/corrupted file
                if os.path.exists(dst_path):
                    os.remove(dst_path)
                os.rename(tmp_dst_path, dst_path)
            except Exception as e:
                print(f"{self.env.ico.get('ERR', __class__)} Failed to finalize file rename: {e}")
                if os.path.exists(tmp_dst_path):
                    try:
                        os.remove(tmp_dst_path)
                    except Exception:
                        pass
                return False, source_digest, dest_digest
        else:
            if os.path.exists(tmp_dst_path):
                try:
                    os.remove(tmp_dst_path)
                except Exception:
                    pass

        return is_valid, source_digest, dest_digest

    def validate_file_structure(self, source_fq_path):
        model_entry = LoadModel(self.env, source_fq_path).analyze()
        return model_entry
    
    def refresh_vault(self):
        return
    
    def valid_active_fq_path(self, model_subfolder, model_name):
        active_fq_path = self.get_active_fq_path(model_subfolder, model_name)
        if not os.path.exists(active_fq_path):
            return None

        return active_fq_path

    def get_valid_vault_fq_path(self, model_name):
        fq_vault_path = self.get_fq_vault_path(model_name)
        sc = SidecarFile(
            vault_path=self.env.vault_dir,
            query_data={"model_name" : model_name},
            fast_hash=self.env.fast_hash
            )
        
        if not sc.get_hash() or not os.path.exists(sc.fq_model_path):
            return None

        return fq_vault_path

    def free_vault_file(self, model_name):
        vault_fq_path = self.get_fq_vault_path(model_name)
        try:            
            sc = SidecarFile(
                    vault_path=self.env.vault_dir,
                    query_data={"model_name" : model_name},
                    fast_hash=self.env.fast_hash)
            sc.delete_sidecar()
            sc.delete_model()
        except Exception:
            pass

    def ingest_to_vault(self, source_fq_path=None, model_entry=None, workflow_data=None, delete_source=True):
        self.workflow_data = workflow_data
        model_path = model_entry.get("model_path")
        model_name = model_entry.get("model_name")
        node_type  = model_entry.get("node_type", "UNKNOWN")
        model_url  = model_entry.get("model_url", "")

        print(f"{self.env.ico.get('ACT',__class__)} Validating tensor data.")
        loaded_model = self.validate_file_structure(source_fq_path)
        if not loaded_model['valid']:
            print(f"{self.env.ico.get('ERR',__class__)} {loaded_model['error']}.")
            return False

        dest_fq_path = self.get_fq_vault_path(model_name)
        transfer_action = "Moving" if delete_source else "Copying"
        print(f"{self.env.ico.get('ACT',__class__)} {transfer_action} to NanoVault with live hash & fsync.")

        # Stream, fsync, read-back verify
        success, source_hash, vault_hash = self.robust_copy_and_verify(source_fq_path, dest_fq_path)

        print(f"{self.env.ico.get('KEY',__class__)} Active file hash [{source_hash}].")
        print(f"{self.env.ico.get('KEY',__class__)} Vaulted file hash [{vault_hash}].")

        if not success:
            print(f"{self.env.ico.get('ERR',__class__)} File corrupted during transfer or storage write failed.")
            return False

        # If move was requested, wipe the verified source file
        if delete_source:
            try:
                os.remove(source_fq_path)
            except Exception as e:
                print(f"{self.env.ico.get('WRN',__class__)} Could not remove source file after move: {e}")

        print(f"{self.env.ico.get('ACT',__class__)} Writing NanoVault metadata.")

        sc = SidecarFile(
                vault_path=self.env.vault_dir,
                query_data=model_entry,
                fast_hash=self.env.fast_hash)

        sc.set_hash(hash_value=vault_hash)
        sc.set_model_entry(model_entry=model_entry)

        sc.add_workflow({
                "id": self.workflow_data["id"],
                "revision": self.workflow_data["revision"],
                "workflow_names": [self.workflow_data["workflow_name"]]
            })

        if not sc.write_sidecar_info():
            print(f"{self.env.ico.get('ERR',__class__)} Unable to write sidecar file.")
            return False

        print(f"{self.env.ico.get('BOX',__class__)} File secured in NanoVault.")
        return True

    def deploy_from_vault(self, model_subfolder=None, model_name=None):
        vault_fq_path = self.get_valid_vault_fq_path(model_name)
        if not vault_fq_path:
            print(f"{self.env.ico.get('ERR',__class__)} Vault file does not exist or metadata is corrupt")
            return False

        sc = SidecarFile(
                vault_path=self.env.vault_dir,
                query_data={"model_name" : model_name, "model_subfolder" : model_subfolder},
                fast_hash=self.env.fast_hash)
        
        if not sc.get_hash():
            print(f"{self.env.ico.get('WRN',__class__)} Vault entry for model cannot be verified.")
            return False

        active_path = self.get_active_fq_path(model_subfolder, model_name)
        print(f"{self.env.ico.get('BOX',__class__)} Retrieving from NanoVault.")

        # Stream write to active folder, fsync, read-back verify
        success, vault_hash, active_hash = self.robust_copy_and_verify(vault_fq_path, active_path)
        
        
        print(f"{self.env.ico.get('KEY',__class__)} [{sc.get_hash()}] NanoVault sidecar hash.")
        print(f"{self.env.ico.get('KEY',__class__)} [{active_hash}] '{model_name}' active hash.")

        if not success or not sc.match_hash(active_hash):
            print(f"{self.env.ico.get('WRN',__class__)} Hash mismatch. Deleting active file.")
            if os.path.exists(active_path):
                try:
                    os.remove(active_path)
                except Exception:
                    pass
            return False

        if not self.valid_active_fq_path(model_subfolder, model_name):
            print(f"{self.env.ico.get('ERR',__class__)} An error occurred during deployment.")
            return False

        print(f"{self.env.ico.get('DONE',__class__)} Hash confirmed.")
        return True

    def deploy_from_cache(self, model_subfolder, model_name):
        active_path = self.get_active_fq_path(model_subfolder, model_name)
        staging_fq_path = self.get_staging_fq_path(model_name)

        if not os.path.exists(staging_fq_path):
            print(f"{self.env.ico.get('ERR',__class__)} File not found in cache.")
            return False

        print(f"{self.env.ico.get('BOX',__class__)} Spot deployment.")
        loaded_model = self.validate_file_structure(staging_fq_path)
        if not loaded_model['valid']:
            print(f"{self.env.ico.get('ERR',__class__)} {loaded_model['error']}..")
            try:
                os.remove(staging_fq_path)
            except Exception:
                pass
            return False
        print(f"{self.env.ico.get('ACT',__class__)} File structure validated.")

        # Stream move from cache to active storage with read-back verification
        print(f"{self.env.ico.get('ACT',__class__)} Moving to active storage.")
        success, staged_hash, active_hash = self.robust_copy_and_verify(staging_fq_path, active_path)
        
        print(f"{self.env.ico.get('KEY',__class__)} [{staged_hash}] Staging file hash.")
        print(f"{self.env.ico.get('KEY',__class__)} [{active_hash}] Active storage hash.")

        if not success:
            print(f"{self.env.ico.get('WRN',__class__)} Hash mismatch during spot deployment.")
            return False

        # Clean staging source file
        try:
            os.remove(staging_fq_path)
        except Exception:
            pass

        print(f"{self.env.ico.get('DONE',__class__)} Hash confirmed.")
        return True

    def rebuild_vault(self, workflows_data=None, force=False):
        print(f"{self.env.ico.get('ACT',__class__)} Starting vault metadata rebuild.")
        vault_dir = self.env.vault_dir
        
        files = []
        reply = {
            "files" : files,
            "total" : int(0),
            "rebuilt" : int(0),
            "errors"  : int(0),
            "message" : "Rebuild in progress."
        }
        
        # 1. Iterate through each workflow from the enumerator
        for wf in workflows_data:
            
            workflow_entry = {
                "workflow_id": wf.get("workflow_id"),
                "revision": wf.get("revision", 0),
                "workflow_names": [wf.get("name", "Unknown_Workflow")]
            }

            # 2. Iterate through every model attached to this workflow
            for model in wf.get("models", []):
                model_name = model.get("model_name")
                vp = os.path.join(vault_dir, model_name)
                
                # If no vault path or model, nothing to do.
                if not model_name or not os.path.exists(vp):
                    continue

                print(f"{self.env.ico.get('ACT',__class__)} Rebuilding '{model_name}'")
                reply["total"]
                # Set up a query to get the sidecar data (if present).
                query_data = {
                    "model_name": model_name,
                    "model_subfolder": model.get("model_path", ""),
                    "node_type": model.get("node_type", ""),
                    "url": model.get("model_url", "")
                }
                
                # Instantiate, query, append, commit.
                try:
                    sc = SidecarFile(
                        vault_path=vault_dir,
                        query_data=query_data,
                        fast_hash=self.env.fast_hash
                    )

                    # Add this workflow to the sidecar_data.
                    print(f"{self.env.ico.get('ACT',__class__)} Adding workflow entry to sidecar. {wf.get("workflow_id")}.Rev({wf.get("revision")})")
                    sc.add_workflow(workflow_entry)

                    # Check for a sidecar hash.
                    vh = sc.get_hash()
                    print(f"{self.env.ico.get('KEY',__class__)} [{sc.get_hash()}] Sidecar hash.")

                    # Validate file structure.
                    loaded_model = LoadModel(self.env, vp).analyze()
                    if loaded_model["valid"]:
                        print(f"{self.env.ico.get('DONE',__class__)} Vault file structure valid.")
                    else:
                        print(f"{self.env.ico.get('DONE',__class__)} Invalid file structure.")
                        if loaded_model["error"].find("CONTINUE") != -1:
                            print(f"{self.env.ico.get('ACT',__class__)} Truncated file moved to download cache.")
                            os.rename(vp, os.path.join(self.env.staging_cache, os.path.join(self.env.staging_cache, model_name)))
                            sc.delete_sidecar()
                            print(self.env.ico.sep(4, 20))
                            vh = None
                        else:
                            print(f"{self.env.ico.get('LIGHT',__class__)} Removing corrupted file from vault '{model_name}'")
                            sc.delete_sidecar()
                            sc.delete_model()
                            print(self.env.ico.sep(4, 20))
                            vh = None
                    
                    if vh and not force:
                        # Skip this file if not forcing hash since it has sidecar hash.
                        print(f"{self.env.ico.get('BOX',__class__)} [{vh}] Hash found in vault. Skipping calculation.")
                    else:
                        # Otherwise, calculate and add it.
                        print(f"{self.env.ico.get('KEY',__class__)} Performing hash calculation.")
                        vh = self.calculate_hash(vp)
                        sc.set_hash(vh)
                        print(f"{self.env.ico.get('ACT',__class__)} [{vh}] Adding hash to sidecar.")
                    
                    # Update sidecar.
                    sc.write_sidecar_info()

                    if vh:
                        reply["rebuilt"] += 1
                    else:
                        reply["errors"] += 1

                    files.append({
                        "model_name" : model_name,
                        "hash_value" : vh,
                        "rebuilt"    : True if vh else False
                        })

                    print(f"{self.env.ico.get('BOX',__class__)} Rebuilt sidecar baseline for: {model_name}")
                    print(self.env.ico.sep(4, 20))
                except Exception as e:
                    print(f"{self.env.ico.get('ERR',__class__)} Failed to rebuild {model_name}: {e}")

        message = f"Vault {vault_dir} Rebuild completed."

        reply.update({
            "files" : files,
            "message" : message,
            "total" : len(files)
            })
        
        print(f"{self.env.ico.get('DONE',__class__)} {message}")

        return reply