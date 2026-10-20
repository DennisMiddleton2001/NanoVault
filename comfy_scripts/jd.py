import sys
import json

if len(sys.argv) != 2:
        print("JSON path required.")
else:
        with open(sys.argv[1], 'r') as f:
          try:
                print(json.dumps(json.load(f), indent=2))
          except KeyError as ke:
            print(ke)


'''
jd.py - JSON dump utility. Create human readable text instantly from a flat JSON file.  This is
        useful for when using curl or analyzing any JSON metadata.  Just pipe ">" your API output to a
        result.json file.

To install:

1. Copy this file to your home folder as "~/jd.py" (If Windows, a path where you store your batch files.)
        Linux: 
          #assuming you're in the NanoVault folder.
          cp comfy_scripts/jd.py ~/

2. Add the jd command to your terminal.
        Linux: Add the jd alias to your .bash_aliases.

          echo "#" >> ~/.bash_aliases
          echo "# JSON Dump" >> ~/.bash_aliases
          echo "#" >> ~/.bash_aliases
          echo "alias jd='python3 ~/jd.py'" >> ~/.bash_aliases

        Windows: Create a file named jd.bat and drop it in a folder in your search path.

                ```FILENAMEjd.cmd```
                        python3 jd.py

3. Close and restart your terminal session.  That's it!  Now you don't have to go online
   to use a json parsing web site to see what's inside. Now you're slicker than a steer!!!

Usage example:

jd /run/media/NanoVault/flux2_klein_4b_mia_lora.safetensors.xxh128
{
  "vault_data": {
    "vault_id": "03d6ce80-61a5-4dd2-885d-c4077c1582d0",
    "vault_sequence": 1225,
    "vault_hash_type": "xxh128",
    "fast_hash": true,
    "vault_dts": "2026-10-19 00:32:18.308962"
  },
  "model_entry": {
    "model_name": "flux2_klein_4b_mia_lora.safetensors",
    "model_subfolder": "loras",
    "node_type": "LoraLoaderModelOnly",
    "url": ""
  },
  "workflows": [
    {
      "workflow_id": "989c649f-d4f0-4234-a799-73caa468e760",
      "revision": 0,
      "workflow_names": [
        "F2_Klein_4B_Lora.json"
      ]
    }
  ],
  "hash_value": "78e9cfd3ebff61207fcd8fb06063d41d"
}

'''
