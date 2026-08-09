import os
import sys
import json
import hashlib
import xxhash
import shutil
import subprocess
import posixpath

from load_model import LoadModel

class VaultManager:
    
    def __init__(self, env = None):
        self.env = env
    
    def get_sidecar_path(self, vault_file):
        return f"{vault_file}.xxh128" if self.env.fast_hash else f"{vault_file}.sha256"

    def read_sidecar(self, file_path):
        sidecar_path = self.get_sidecar_path(file_path)
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r') as f:
                return f.read().strip()
        return None

    def write_sidecar(self, file_path, file_hash):
        sidecar_path = self.get_sidecar_path(file_path)
        with open(sidecar_path, 'w') as f:
            f.write(file_hash)

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
            return
        for item in os.listdir(self.env.vault_dir):
            if item.lower().endswith(".safetensors"):
                full_path = os.path.join(self.env.vault_dir, item)
                if os.path.isfile(full_path):
                    hash_val = self.calculate_hash(full_path)
                    self.write_sidecar(full_path, hash_val)
                    print(f"{self.env.ico.get('INFO',__class__)} HASH {hash_val} {full_path}")
        
    def find_in_vault(self, model_name):
        exact_path = os.path.join(self.env.vault_dir, model_name)
        if not os.path.exists(exact_path):
            return None
        return exact_path

    def ingest_to_vault(self, staged_path, original_name, delete_source = True):
        print(f"{self.env.ico.get('ACT',__class__)} Calculating hash.")
        staged_file_hash = self.calculate_hash(staged_path)
        print(f"{self.env.ico.get('KEY',__class__)} Staged file hash [{staged_file_hash}].")

        # Either copy or move the file to the vault.
        dest_path = os.path.join(self.env.vault_dir, original_name)
        if not delete_source:
            print(f"{self.env.ico.get('ACT',__class__)} Copying to NanoVault.")
            shutil.copy(staged_path, dest_path)
        else:
            print(f"{self.env.ico.get('ACT',__class__)} Moving to NanoVault.")
            shutil.move(staged_path, dest_path)

        # It's expensive, but we calculate hash again when the file hits the vault.
        print(f"{self.env.ico.get('KEY',__class__)} Calculating vault file hash.")
        file_hash = self.calculate_hash(dest_path)
        print(f"{self.env.ico.get('KEY',__class__)} Vaulted file hash [{file_hash}].")
        if not file_hash == staged_file_hash:
            print(f"{self.env.ico.get('ERR',__class__)} File corrupted during copy/move.")
            try:
                os.remove(dest_path)
            except Exception as e:
                print(f"{self.env.ico.get('ERR',__class__)} Unable to delete corrupt vault file. {e}")
            return None

        # Everything checks out.  Write metadata to the vault.
        print(f"{self.env.ico.get('ACT',__class__)} Writing NanoVault metadata.")
        self.write_sidecar(dest_path, file_hash)
        print(f"{self.env.ico.get('BOX',__class__)} File secured in NanoVault.")
        return dest_path

    def deploy_to_active(self, src_path, target_subfolder, model_name):
            active_dir = os.path.join(self.env.active_root, target_subfolder)
            os.makedirs(active_dir, exist_ok=True)
            active_path = os.path.join(active_dir, model_name)

            # Copy vault file to active storage
            print(f"{self.env.ico.get('BOX',__class__)} Retrieving from NanoVault.")
            shutil.copy2(src_path, active_path) 
            
            # Verify it arrived intact by comparing against the existing sidecar
            print(f"{self.env.ico.get('KEY',__class__)} Calculating active file hash.")
            side_hash = self.read_sidecar(src_path)
            hash_value = self.calculate_hash(active_path)
            print(f"{self.env.ico.get('KEY',__class__)} [{hash_value}] '{model_name}'. ")
            print(f"{self.env.ico.get('KEY',__class__)} [{side_hash}] NanoVault metadata hash.")
            
            if not side_hash == hash_value:
                print (f"{self.env.ico.get('WRN',__class__)} Hash mismatch on {active_path}. Deleting.")
                os.remove(active_path)
                return False

            print(f"{self.env.ico.get('DONE',__class__)} Hash confirmed.")
            return True
