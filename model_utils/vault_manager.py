import os
import sys
import json
import hashlib
import xxhash
import shutil
from .load_model import LoadModel

class VaultManager:
    
    def __init__(self, env = None):
        self.env = env

    def clean(self, path):
        return path.strip(' \t\n\r"\'')

    def get_fq_vault_path(self, model_name):
        return self.clean(os.path.join(self.env.vault_dir, model_name))

    def get_model_subfolder(self, fq_path, model_name):
        # Extract the model subfolder from a fully qualified path.
        tag = 'ComfyUI/models/'

        start_idx = fq_path.find(tag)+len(tag)

        path_and_name = fq_path[start_idx:]
        if path_and_name.endswith(model_name):
            subfolder = path_and_name[:-len(model_name)-1]
        
        return self.clean(subfolder)

    def get_active_fq_path(self, model_subfolder, model_name):
         return self.clean(os.path.join(self.env.active_root, model_subfolder, model_name))

    def get_staging_fq_path(self, model_name):
         return self.clean(os.path.join(self.env.staging_cache, model_name))

    def get_fq_sidecar_path(self, vault_fq_path):
        return  self.clean(f"{vault_fq_path}{self.env.sidecar_ext}")

    def write_sidecar_entry(self, vault_fq_path, sidecar_entry):

        sidecar_path = self.get_fq_sidecar_path(vault_fq_path)
    
        try:
            with open(sidecar_path, "w") as f:
                json.dump(sidecar_entry, f, indent=4)
        except:
            return False

        return True

    def read_sidecar_entry(self, vault_fq_path):

        sidecar_path = self.get_fq_sidecar_path(vault_fq_path)
        sidecar_entry = None

        try:
            if os.path.exists(sidecar_path):
                with open(sidecar_path, "r") as f:
                    sidecar_entry = json.load(f)

        except:
            pass

        return sidecar_entry

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

    def validate_file_structure(self, source_fq_path):

        if not os.path.exists(source_fq_path):
            return False
        
        model_entry = LoadModel(self.env, source_fq_path).analyze()
        if not model_entry['valid']:
            return False

        return True

    def refresh_vault(self):
            #Much work to be done here.
            return
    
    def valid_active_fq_path(self, model_subfolder, model_name):

        active_fq_path = self.get_active_fq_path(model_subfolder, model_name)
        if not os.path.exists(active_fq_path):
            return None

        # There may be vault metadata to fix up.
        vault_fq_path = self.get_fq_vault_path(model_name)
        if vault_fq_path:
            try:
                # See if a model_subfolder exists.
                sidecar_entry = self.read_sidecar_entry(vault_fq_path)
                if sidecar_entry and not len(sidecar_entry["model_subfolder"]):
                    sidecar_entry["model_subfolder"] = model_subfolder
                    self.write_sidecar_entry(vault_fq_path, sidecar_entry)
            except KeyError:
                #This should never ever happen, but let's not crash over it.
                pass
        
        return active_fq_path

    def get_valid_vault_fq_path(self, model_name):
        vault_fq_path  = self.get_fq_vault_path(model_name)

        if not self.read_sidecar_entry(vault_fq_path):
            return None
        
        return vault_fq_path

    def free_vault_file(self, model_name):
        vault_fq_path = self.get_fq_vault_path(model_name)
        sidecar_fq_path = self.get_fq_sidecar_path(vault_fq_path)
        try:
            os.remove(sidecar_fq_path)
        except:
            pass

        try:
            os.remove(vault_fq_path)
        except:
            pass

        return True

    def ingest_to_vault(self, source_fq_path, model_name, delete_source = True):
        ingest_from_active = None

        if source_fq_path.find(self.env.active_root) >= 0:
            ingest_from_active = True
            model_subfolder = self.get_model_subfolder(source_fq_path, model_name)
            print(f"{self.env.ico.get('ACT',__class__)} Ingesting from active folder '{model_subfolder}'.")
        else:
            ingest_from_active = False
            print(f"{self.env.ico.get('ACT',__class__)} Ingesting from staging cache.")
            model_subfolder = ""
        
        print(f"{self.env.ico.get('ACT',__class__)} Validating tensor data.")
        if not self.validate_file_structure(source_fq_path):
            print(f"{self.env.ico.get('ERR',__class__)} Corrupted tensor data.")
            return False
        print(f"{self.env.ico.get('ACT',__class__)} Tensor data validated.")

        print(f"{self.env.ico.get('ACT',__class__)} Calculating file hash.")
        source_file_hash = self.calculate_hash(source_fq_path)
        print(f"{self.env.ico.get('KEY',__class__)} Source file hash [{source_file_hash}].")

        # Step 2: Move or copy the file into the vault directory.
        dest_fq_path = self.get_fq_vault_path(model_name)
        if not delete_source:
            print(f"{self.env.ico.get('ACT',__class__)} Copying to NanoVault.")
            shutil.copy(source_fq_path, dest_fq_path)
        else:
            print(f"{self.env.ico.get('ACT',__class__)} Moving to NanoVault.")
            shutil.move(source_fq_path, dest_fq_path)

        print(f"{self.env.ico.get('KEY',__class__)} Calculating vault file hash.")
        dest_file_hash = self.calculate_hash(dest_fq_path)
        print(f"{self.env.ico.get('KEY',__class__)} Vaulted file hash [{dest_file_hash}].")

        if not dest_file_hash == source_file_hash:
            print(f"{self.env.ico.get('ERR',__class__)} File corrupted during copy/move.")
            try:
                os.remove(dest_fq_path)
            except Exception as e:
                print(f"{self.env.ico.get('ERR',__class__)} Unable to delete corrupted vault file. {e}")
            return False

        print(f"{self.env.ico.get('ACT',__class__)} Writing NanoVault metadata.")

        sidecar_entry = {
            "hash"            : dest_file_hash,
            "model_subfolder" : model_subfolder if ingest_from_active else ""
        }

        if not self.write_sidecar_entry(dest_fq_path, sidecar_entry):
            print(f"{self.env.ico.get('ERR',__class__)} Unable to write sidecar file.")
            return False

        print(f"{self.env.ico.get('BOX',__class__)} File secured in NanoVault.")
        return True

    def deploy_from_vault(self, model_subfolder, model_name):
            
            vault_fq_path  = self.get_valid_vault_fq_path(model_name)
            if not vault_fq_path:
                print(f"{self.env.ico.get('ERR',__class__)} Vault file does not exist or metadata is corrupt")
                return False

            sidecar_entry = self.read_sidecar_entry(vault_fq_path)
            if not sidecar_entry:
                print(f"{self.env.ico.get('WRN',__class__)} No sidecar metadata found. Unable to verify integrity.")
                return False

            # Our path isn't really valid, so we just get the path string now.
            active_path = self.get_active_fq_path(model_subfolder, model_name)
            print(f"{self.env.ico.get('BOX',__class__)} Retrieving from NanoVault.")
            shutil.copy2(vault_fq_path, active_path) 
            
            print(f"{self.env.ico.get('ACT',__class__)} Starting hash verification.")

            try:
                side_hash = sidecar_entry['hash']
            except:
                side_hash = 'CORRUPT_VAULT_METADATA'

            print(f"{self.env.ico.get('KEY',__class__)} [{side_hash}] NanoVault hash.")
            active_hash = self.calculate_hash(active_path)
            print(f"{self.env.ico.get('KEY',__class__)} [{active_hash}] '{model_name}'. ")
            
            if side_hash != active_hash:
                print (f"{self.env.ico.get('WRN',__class__)} Hash mismatch. Deleting active file.")
                try:
                    os.remove(active_path)
                except:
                    pass
                return False
            '''
                IMPORTANT: In download situations, we ingest the file straight from download cache,
                so source model_subfolder == ''.  Then we immediately deploy to active assuming
                that the template knows the subfolder (the first time).  It's possible that other 
                templates won't tell us where the file goes, but we can deploy anyway using only the
                model_name as long as the model deployment worked once. This check updates the metadata.
                In theory, we shouldn't ever see this fail since we just deployed.
            '''
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

                if not self.validate_file_structure(staging_fq_path):
                    print(f"{self.env.ico.get('ERR',__class__)} File corrupted during download. Deleting.")
                    try:
                        os.remove(staging_fq_path)
                    except:
                        pass
                    return False
                print(f"{self.env.ico.get('ACT',__class__)} File structure validated.")
                
                print(f"{self.env.ico.get('ACT',__class__)} Calculating staging file hash.")
                staged_hash = self.calculate_hash(staging_fq_path)
                print(f"{self.env.ico.get('KEY',__class__)} [{staged_hash}] Staging file hash.")

                print(f"{self.env.ico.get('ACT',__class__)} Moving to active storage.")
                shutil.move(staging_fq_path, active_path)

                print(f"{self.env.ico.get('ACT',__class__)} Calculating desination file hash.")
                active_hash = self.calculate_hash(active_path)
                print(f"{self.env.ico.get('KEY',__class__)} [{staged_hash}] {active_path} hash.")
                
                if staged_hash != active_hash:
                    print(f"{self.env.ico.get('WRN',__class__)} Hash mismatch. Deleting active file.")
                    try:
                        os.remove(active_path)
                    except:
                        pass
                    return False

                print(f"{self.env.ico.get('DONE',__class__)} Hash confirmed.")
                return True
