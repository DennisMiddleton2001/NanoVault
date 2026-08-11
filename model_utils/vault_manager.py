import os
import sys
import json
import hashlib
import xxhash
import shutil
from load_model import LoadModel

class VaultManager:
    
    def __init__(self, env = None):
        self.env = env

    def clean(self, path):
        return path.strip(' \t\n\r"\'')

    def get_vault_path(self, name):
        return self.clean(os.path.join(self.env.vault_dir, name))

    def get_active_path(self, folder, name):
        return self.clean(os.path.join(self.env.active_root, folder, name))

    def get_sidecar_path(self, vault_file_path):
        return  self.clean(f"{vault_file_path}{self.env.sidecar_ext}")

    def write_sidecar_hash(self, vault_file, hash):
        sidecar_path = self.get_sidecar_path(vault_file)
        try:
            with open(sidecar_path, "w") as f:
                f.write(hash)
        except:
            return False
        return True

    def read_sidecar(self, vault_file):
        sidecar_path = self.get_sidecar_path(vault_file)
        try:
            if os.path.exists(sidecar_path):
                with open(sidecar_path, 'r') as f:
                    return f.read()
        except:
            return None

    def calculate_xxh_hash(self, filepath, chunk_size=8388608):
        hasher = xxhash.xxh128()
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    def calculate_sha_hash(self, file_path, chunk_size=4096*1024):
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def calculate_hash(self, file_path):
            return self.calculate_xxh_hash(file_path) if self.env.fast_hash else self.calculate_sha_hash(file_path)

    def refresh_vault(self):
        if not os.path.exists(self.env.vault_dir):
            return False

        for item in os.listdir(self.env.vault_dir):
            if item.lower().endswith(".safetensors"):
                full_path = self.get_vault_path(item)
                if os.path.isfile(full_path):
                    hash_val = self.calculate_hash(full_path)
                    self.write_sidecar_hash(full_path, hash_val)
                    print(f"{self.env.ico.get('INFO',__class__)} HASH {hash_val} {full_path}")

    def find_valid_active_file(self, folder, name):
        active_path = self.get_active_path(folder, name)
        if not os.path.exists(active_path):
            return None
        return active_path

    def find_valid_vault_file(self, model_name):
        vault_file_path = self.get_vault_path(model_name)
        sidecar_hash    = self.read_sidecar(vault_file_path)
        if os.path.exists(vault_file_path) and sidecar_hash:
            return vault_file_path
        else:
            return None

    def free_vault_file(self, name):
        vault_path = self.get_vault_path(name)
        sidecar_path = self.get_sidecar_path(vault_path)
        try:
            os.remove(sidecar_path)
        except:
            pass
        try:
            os.remove(vault_path)
        except:
            pass

    def ingest_to_vault(self, full_source_path, model_name, delete_source = True):
        
        print(f"{self.env.ico.get('ACT',__class__)} Validating tensor data.")
        m = LoadModel(self.env, full_source_path)
        if not m.analyze():
            print(f"{self.env.ico.get('ERR',__class__)} Corrupted tensor data.")
            return False
        print(f"{self.env.ico.get('ACT',__class__)} Tensor data validated.")

        # Step 1: Calculate the hash of the original file before moving or copying it.
        print(f"{self.env.ico.get('ACT',__class__)} Calculating file hash.")
        source_file_hash = self.calculate_hash(full_source_path)
        print(f"{self.env.ico.get('KEY',__class__)} Source file hash [{source_file_hash}].")

        # Step 2: Move or copy the file into the vault directory.
        dest_path = self.get_vault_path(model_name)
        if not delete_source:
            print(f"{self.env.ico.get('ACT',__class__)} Copying to NanoVault.")
            shutil.copy(full_source_path, dest_path)
        else:
            print(f"{self.env.ico.get('ACT',__class__)} Moving to NanoVault.")
            shutil.move(full_source_path, dest_path)

        # Step 3: Calculate the hash of the file in the vault and compare it to the staged 
        # hash to ensure integrity.
        print(f"{self.env.ico.get('KEY',__class__)} Calculating vault file hash.")
        dest_file_hash = self.calculate_hash(dest_path)
        print(f"{self.env.ico.get('KEY',__class__)} Vaulted file hash [{dest_file_hash}].")

        if not dest_file_hash == source_file_hash:
            print(f"{self.env.ico.get('ERR',__class__)} File corrupted during copy/move.")
            try:
                os.remove(dest_path)
            except Exception as e:
                print(f"{self.env.ico.get('ERR',__class__)} Unable to delete corrupted vault file. {e}")
            return False

        print(f"{self.env.ico.get('ACT',__class__)} Writing NanoVault metadata.")
        if not self.write_sidecar_hash(dest_path, dest_file_hash):
            print(f"{self.env.ico.get('ERR',__class__)} Unable to write sidecar file.")
            return False

        print(f"{self.env.ico.get('BOX',__class__)} File secured in NanoVault.")
        return True

    def deploy_from_vault(self, active_subfolder, model_name):
            # Step 1: Ensure the active subfolder exists; if not prompt user to create it.
            active_path = self.get_active_path(active_subfolder, model_name)
            vault_path  = self.find_valid_vault_file(model_name)
            if not vault_path:
                print(f"{self.env.ico.get('ERR',__class__)} Vault file does not exist or metadata is corrupt")
                return False
                        
            print(f"{self.env.ico.get('BOX',__class__)} Retrieving from NanoVault.")
            shutil.copy2(vault_path, active_path) 
            
            print(f"{self.env.ico.get('ACT',__class__)} Starting hash verification.")

            side_hash = self.read_sidecar(vault_path)
            if side_hash is None:
                print(f"{self.env.ico.get('WRN',__class__)} No sidecar metadata found. Unable to verify integrity.")
                return False

            print(f"{self.env.ico.get('KEY',__class__)} [{side_hash}] Vault hash.")
            active_hash = self.calculate_hash(active_path)
            print(f"{self.env.ico.get('KEY',__class__)} [{active_hash}] '{model_name}'. ")
            
            if side_hash != active_hash:
                print (f"{self.env.ico.get('WRN',__class__)} Hash mismatch. Deleting active file.")
                try:
                    os.remove(active_path)
                except:
                    pass
                return False

            print(f"{self.env.ico.get('DONE',__class__)} Hash confirmed.")
            return True

