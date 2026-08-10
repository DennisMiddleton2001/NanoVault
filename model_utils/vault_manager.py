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
    
    def get_sidecar_path(self, vault_file):
        return f"{vault_file}{self.env.sidecar_ext}"

    def read_sidecar(self, file_path):
        sidecar_path = self.get_sidecar_path(file_path)
        if os.path.exists(sidecar_path):
            with open(sidecar_path, 'r') as f:
                return f.read().strip()
        return None

    # Used to write a sidecar file containing the hash of the model file.
    def write_sidecar(self, file_path, file_hash):
        sidecar_path = self.get_sidecar_path(file_path)
        with open(sidecar_path, 'w') as f:
            f.write(file_hash)

    # Used internally to calculate the xxh128 hash of a file for integrity verification.
    def calculate_xxh_hash(self, filepath, chunk_size=8388608):
        hasher = xxhash.xxh128()
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    # Used internally to calculate the SHA-256 hash of a file for integrity verification.
    def calculate_sha_hash(self, file_path, chunk_size=4096*1024):
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    # Used to calculate the hash depending on value of self.env.fast_hash.
    # If True, uses xxh128 for speed; otherwise, uses SHA-256 for security.
    def calculate_hash(self, file_path):
            return self.calculate_xxh_hash(file_path) if self.env.fast_hash else self.calculate_sha_hash(file_path)

    # Used to walk through the vault directory and re-calculate hashes 
    # for all model files, updating their sidecar files accordingly.
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

    # Used to find a model file in the vault by its name.
    # Returns the full path if found, otherwise None.    
    def find_in_vault(self, model_name):
        exact_path = os.path.join(self.env.vault_dir, model_name)
        sidecar_hash = self.read_sidecar(exact_path)
        if os.path.exists(exact_path) and sidecar_hash:
            return exact_path
        else:
            return None

    # This method is used by ingest, trim, and fetch pipelines to move or copy a model file into the vault, calculate its hash, and write the corresponding sidecar metadata.
    # It returns the destination path in the vault if successful, or None if there was 
    # an error during the process (e.g., hash mismatch, file corruption).
    def ingest_to_vault(self, original_full_path, model_name, delete_source = True):

        # Step 0: Validate the source file is a valid model file by loading it with LoadModel.
        print(f"{self.env.ico.get('ACT',__class__)} Validating tensor data.")

        m = LoadModel(self.env, original_full_path)
        if not m.analyze():
            print(f"{self.env.ico.get('ERR',__class__)} Corrupted tensor data.")
            return None
        print(f"{self.env.ico.get('ACT',__class__)} Tensor data validated.")

        # Step 1: Calculate the hash of the original file before moving or copying it.
        print(f"{self.env.ico.get('ACT',__class__)} Calculating hash.")
        staged_file_hash = self.calculate_hash(original_full_path)
        print(f"{self.env.ico.get('KEY',__class__)} Staged file hash [{staged_file_hash}].")

        # Step 2: Move or copy the file into the vault directory.
        dest_path = os.path.join(self.env.vault_dir, model_name)
        if not delete_source:
            print(f"{self.env.ico.get('ACT',__class__)} Copying to NanoVault.")
            shutil.copy(original_full_path, dest_path)
        else:
            print(f"{self.env.ico.get('ACT',__class__)} Moving to NanoVault.")
            shutil.move(original_full_path, dest_path)

        # Step 3: Calculate the hash of the file in the vault and compare it to the staged 
        # hash to ensure integrity.
        print(f"{self.env.ico.get('KEY',__class__)} Calculating vault file hash.")
        file_hash = self.calculate_hash(dest_path)
        print(f"{self.env.ico.get('KEY',__class__)} Vaulted file hash [{file_hash}].")

        if not file_hash == staged_file_hash:
            print(f"{self.env.ico.get('ERR',__class__)} File corrupted during copy/move.")
            try:
                os.remove(dest_path)
            except Exception as e:
                print(f"{self.env.ico.get('ERR',__class__)} Unable to delete corrupted vault file. {e}")
            return None

        # Step 4: Write the sidecar metadata file containing the hash for future integrity checks.
        print(f"{self.env.ico.get('ACT',__class__)} Writing NanoVault metadata.")
        self.write_sidecar(dest_path, file_hash)
        print(f"{self.env.ico.get('BOX',__class__)} File secured in NanoVault.")
        return dest_path

    # Deploys a file from the vault to the active workspace, verifying its integrity against the sidecar hash.
    # Returns True if successful, False if there was a hash mismatch or other error.
    def deploy_to_active(self, src_path, active_subfolder, model_name):
            # Step 1: Ensure the active subfolder exists; if not prompt user to create it.
            active_dir = os.path.join(self.env.active_root, active_subfolder)
            if not os.path.exists(active_dir):
                print(f"{self.env.ico.get('ERR',__class__)} Active subfolder not found: Verify '{active_dir}' exists.")
                return False
            
            desination_path = os.path.join(active_dir, model_name)

            # Copy vault file to active ecosystem.
            print(f"{self.env.ico.get('BOX',__class__)} Retrieving from NanoVault.")
            shutil.copy2(src_path, desination_path) 
            
            # Verify it arrived intact by comparing against the sidecar if None, the sidecar doesn't exist.
            print(f"{self.env.ico.get('KEY',__class__)} Vault hash verification.")
            side_hash = self.read_sidecar(src_path)
            if side_hash is None:
                print(f"{self.env.ico.get('WRN',__class__)} No sidecar metadata found. Unable to verify integrity.")
                return False

            deployed_file_hash = self.calculate_hash(desination_path)

            print(f"{self.env.ico.get('KEY',__class__)} [{deployed_file_hash}] '{model_name}'. ")
            print(f"{self.env.ico.get('KEY',__class__)} [{side_hash}] NanoVault metadata hash.")
            
            if side_hash != deployed_file_hash:
                print (f"{self.env.ico.get('WRN',__class__)} Hash mismatch on {desination_path}. Deleting.")
                os.remove(desination_path)
                return False

            print(f"{self.env.ico.get('DONE',__class__)} Hash confirmed.")
            return True
