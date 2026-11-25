# NanoVault Technical Description

**NanoVault** is a robust model and workflow manager that allows single-click installation and validation of ComfyUI workflow models. To get started, NanoVault provides two GUI interfaces:

1. `config_ui.py` (Configuration Utility)
2. `main.py` (API Server & Web Command Center)

---

## User Interfaces

### `config_ui.py` — Configuration Interface (Optional)

Allows you to configure application options in `config.json`. It features a rich interface that displays all installed model files in a sortable list. To protect specific models from accidental deletion, you can optionally sort the model files by size and click the lock icon for individual files.

Once the configuration is saved, the protected models are stored in `config.json` along with the application settings. Tokens can be specified in the UI, or left blank to fall back to the `HF_TOKEN` and `CIVITAI_TOKEN` environment variables.

#### Example `config.json`

```json
{
  "application": "NanoVault",
  "version": "1.3.0",
  "paths": {
    "comfy_ui_root": "/home/darth-tedious/.sovereign-ai/ComfyUI",
    "vault_dir": "/run/media/darth-tedious/5eb65f8c-6e86-46ab-beaa-c2bec31b620c/NanoVault",
    "staging_cache": "/mnt/nvme-storage/download_cache"
  },
  "fast_hash": true,
  "tokens": {},
  "exclude_from_purge": [
    "gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors",
    "krea2_turbo_fp8_scaled.safetensors"
  ]
}
```

> **Note:** To perform a quick sanity check of `config.json`, run `python nv.py --config`.

### `main.py` — API Server & Web UI

Launches the FastAPI server hosting the web-based UI on port `8000`. Once launched, `Ctrl+Click` the URL shown in the server terminal (`http://127.0.0.1:8000`).

---

## Basic Operations

The web server (`main.py`) provides a browser interface (`http://127.0.0.1:8000`) for quick and easy access to common features.
>Additional features are available through nv.py or the API server (while `main.py` is running).

### General Commands

* `--config`: Print NanoVault configuration and show any errors.

### Commands (run python nv.py --help for more...)

*Most common operations are described below:*

* `--list-workflows`: Creates a JSON report of all dependencies in a folder.
* `--a`: **Add models** (`Download ==> Vault ==> Deploy`).
* `--as`: **Add spot** (`Download ==> Deploy`) — ideal for staging spot instances where a Vault archive isn't needed.
* `--t`: **Trim models** (`VaultActive ==> DeleteActive`).
* `--i`: **Ingest models** (`VaultActive`, no deletion from Active).
* `--e`: **Evict models** (`DeleteActive`, `DeleteVaulted`, unless excluded by policy in `config.json`).
* `--rebuild-vault`: **Rebuild Vault** Rebuilds the vault metadata sidecar files (useful if switching from xxh128 "fast_hash" to sha256), or if sidecar files don't exist.
* `--audit-model`: **Audit Model** Lists workflows associated with a model file's name ("ae.safetensors", etc.).

---

## Download Process Overview

NanoVault ensures that files downloaded from the internet come from a valid authoritative source using the following verification pipeline:

1. **Header Inspection:** Tensor headers are read and validated.  If a truncated file is found, the download of the file will be retried/continued if the file is in the download cache folder.
> NOTE: If manually downloading model files, download them to the download cache folder and NanoVault will validate them as if they were obtained via the  "--a" or "--as" pipeline during installation.  This is useful when obtaining files from gated repos or 3rd parties.
2. **Structure Validation:** The tensors are validated. If the structure is invalid (for example, an HTML/text download error page), the invalid file is automatically deleted.
3. **Offset & Truncation Walk:** NanoVault crawls through the tensors and verifies that all byte offsets stay within bounds. If it attempts to walk past the end of the file, the download is flagged as valid but truncated.
4. **Automatic Resume:** If a file is flagged as truncated, NanoVault automatically attempts to resume and complete the download.
5. **Retry Preservation:** If a download fails due to server availability, the partial file remains in `staging_cache` so it can be retried later.
6. **Node Type Validation**: Target model folder is determined in the following order...
* Workflow's specified model subfolder
* ComfyUI default pathing based on known node_type names
* Custom node pathing as specified in *config_path_map.json*.

> **Important:** If you choose to manually download a file via a web browser, save it directly to the `staging_cache` folder. NanoVault will perform all integrity checks and honor the file as a completed download during deployment (or delete it if it is corrupt).

---

## Vault Specifications

Vault storage should reside on a separate physical disk from your ComfyUI models folder so it serves as a reliable low-cost, persistent local source of models (SATA or USB4.0+ storage recommended).

Vault sidecar metadata stores the file's upstream URL (if present in the workflow), referenced workflow details, and cryptographic hashes.

**SIDECAR FILE:** qwen3.5_9b_w4a8_gptq.safetensors.xxh128
```json
{
    "vault_data": {
        "vault_id": "03d6ce80-61a5-4dd2-885d-c4077c1582d0",
        "vault_sequence": 33985,
        "vault_hash_type": "xxh128",
        "fast_hash": true,
        "vault_dts": "2026-10-19 00:32:18.308962"
    },
    "model_entry": {
        "node_type": "CLIPLoader",
        "model_name": "qwen3.5_9b_w4a8_gptq.safetensors",
        "model_path": "text_encoders",
        "model_url": "https://huggingface.co/Comfy-Org/Qwen3.5/resolve/main/text_encoders/qwen3.5_9b_w4a8_gptq.safetensors"
    },
    "workflows": [
        {
            "id": "6e5d96b7-1687-4e3d-8559-6c3e5468c193",
            "revision": 0,
            "workflow_names": [
                "/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/image_minimax_h3_image_t2i.json"
            ]
        }
    ],
    "hash_value": "8ede9984053801b7530f52b211b487f9"
}
```

If you change `fast_hash` in *config.json* from its default of `true` to `false`. Ensure that you run `--rebuild-vault` to recalculate the hash values for all vaulted models and generate new sidecar files matching the hash algorithm (`xxh128` for fast hash, or `sha256` for cryptographic hash). 
>NOTE: Deleting unused sidecar files after rebuild is recommended to prevent confusion.

### Vault Disk Recommendations (Inexpensive)
Any large, reliable, inexpensive secondary storage drive will work.

* USB 4.0
* SATA (IDE or SSD)
* PCIE Attached Storage

### 5-Step Vault Ingest Pathway

1. Validate the source file's tensor structure.
2. Compute the hash of the source file.
3. Perform a robust copy with readback hashing to ensure the entire file is written intact to the Vault.
4. Validate the vaulted file's hash against the original source file hash.
5. Write a JSON sidecar file containing the hash and metadata to the NanoVault folder.

#### Example Sidecar (`birefnet.safetensors.xxh128`)

```json
{
  "vault_data": {
    "vault_id": "03d6ce80-61a5-4dd2-885d-c4077c1582d0",
    "vault_sequence": 29725,
    "vault_hash_type": "xxh128",
    "fast_hash": true,
    "vault_dts": "2026-10-19 00:32:18.308962"
  },
  "model_entry": {
    "node_type": "LoadBackgroundRemovalModel",
    "model_name": "birefnet.safetensors",
    "model_path": "background_removal",
    "model_url": "https://huggingface.co/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors"
  },
  "workflows": [
    {
      "id": "afd7ae55-5ffe-481f-b965-5ec4f4f86eee",
      "revision": 0,
      "workflow_names": [
        "/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/BG_REMOVAL_BIREF.json"
      ]
    }
  ],
  "hash_value": "4724a411e275159ab90473d5cda42e96"
}
```

---

## Server API Logs

Log files are stored in the `logs` folder and indexed by date (`YYYYMMDD.log`). The log format mirrors the JSON returned by the NanoVault server API alongside start and end timestamps.

### Example 1: Spot Install (`--as`) on Cloud/Borrowed Hardware

Spot installs are recommended for borrowed cloud instances connected via SSH, where a single NVMe drive will be wiped after the session. Bypassing the Vault avoids duplicating multi-gigabyte files. In this run over consumer Wi-Fi, the authoritative source was `download` and completed in ~4 hours 12 minutes:

```json
((venv) ) darth-tedious@darkmatter:~/.sovereign-ai/NanoVault$ cat logs/20260920.log 
[START]   : 2026-09-20 02:42:23.996612
[COMMAND] : ['--as', '/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/video_minimax_h3_i2v.json']
[END]     : 2026-09-20 06:54:58.515169
========================================
{
  "command": "SpotDeploymentPipeline",
  "attempted": 5,
  "successful": 5,
  "active": [],
  "download": [
    "minimax_h3_video_vae_fp16.safetensors",
    "minimax_h3_audio_vae_fp32.safetensors",
    "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
    "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"
  ],
  "vault": [],
  "failed": [],
  "purged": [],
  "excluded": [],
  "message": "Deployment successful."
}
========================================
```

### Example 2: Restoring from Vault (`--a`)

LTX 2.3 had previously been trimmed to a USB 4 Vault flash drive to free up NVMe space. Running `--a` restored all 5 models from the Vault as the authoritative source in 7 minutes:

```json
========================================
[START]   : 2026-09-17 03:34:12.573631
[COMMAND] : ['--a', '/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/video_ltx2_3_i2v.json']
[END]     : 2026-09-17 03:41:14.977167
========================================
{
  "command": "DeploymentPipeline",
  "attempted": 5,
  "successful": 5,
  "active": [],
  "download": [],
  "vault": [
    "ltx-2.3-22b-dev-fp8.safetensors",
    "ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors",
    "ltx-2.3-spatial-upscaler-x2-1.1.safetensors",
    "gemma_3_12B_it_fp4_mixed.safetensors",
    "gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors"
  ],
  "failed": [],
  "purged": [],
  "excluded": [],
  "message": "Deployment successful."
}
========================================
```

### Example 3: Trimming Active Storage (`--t`)

423 MiB was ingested into the Vault and freed from `ComfyUI/models` using `--t`, completing in milliseconds:

```json
========================================
[START]   : 2026-09-17 03:43:28.230841
[COMMAND] : ['--t', '/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/EDIT_BG_REMOVE.json']
[END]     : 2026-09-17 03:43:28.245499
========================================
{
  "command": "TrimPipeline",
  "attempted": 1,
  "successful": 1,
  "active": [],
  "download": [],
  "vault": [
    "birefnet.safetensors"
  ],
  "failed": [],
  "purged": [],
  "excluded": [],
  "message": "Trim successful."
}
========================================
```

### Example 4: Fast Vault-to-Active Redeployment (`--as`)

Once a model is vaulted, redeploying the workflow with `--a` or `--as` restores it directly from the Vault—completing in ~1 second:

```json
========================================
[START]   : 2026-09-17 03:43:32.850665
[COMMAND] : ['--as', '/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/EDIT_BG_REMOVE.json']
[END]     : 2026-09-17 03:43:33.935773
========================================
{
  "command": "SpotDeploymentPipeline",
  "attempted": 1,
  "successful": 1,
  "active": [],
  "download": [],
  "vault": [
    "birefnet.safetensors"
  ],
  "failed": [],
  "purged": [],
  "excluded": [],
  "message": "Deployment successful."
}
========================================
```

---

## Advanced: Remote API Scripting

Because NanoVault runs an HTTP API server, you can use `curl` to trigger any operation remotely as part of an automation or admin script:

```bash
curl -X POST "http://127.0.0.1:8000/api/execute" \
     -H "Content-Type: application/json" \
     -H "Origin: http://127.0.0.1:8000" \
     -d '{"command": ["--as", "/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/video_minimax_h3_i2v.json"]}'
```

### Example API Response

```json
{
  "status": "SUCCESS",
  "command_echo": [
    "--as",
    "/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/video_minimax_h3_i2v.json"
  ],
  "retval": {
    "command": "SpotDeploymentPipeline",
    "attempted": 5,
    "successful": 5,
    "active": [
      "minimax_h3_video_vae_fp16.safetensors",
      "minimax_h3_audio_vae_fp32.safetensors",
      "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
      "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
      "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"
    ],
    "download": [],
    "vault": [],
    "failed": [],
    "purged": [],
    "excluded": [],
    "message": "Deployment successful."
  },
  "message": "Successfully executed --as on /home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/video_minimax_h3_i2v.json"
}
```

---

## Conclusion

Consider this technical description a quick-start reference for both new users and power users alike—additional CLI flags and utilities are documented in nv.py.

```bash
python nv.py --help
```
If you want to support the future development of NanoVault, please consider supporting the project on Patreon—every little bit helps keep the tensor cores warm and the community rich with new innovations:

* **Patreon:** https://patreon.com/AmNanotech