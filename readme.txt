NanoVault Setup Guide (Python 3.12)
===================================
Before you begin, please refer to the technical_specifications.txt file for NanoVault.

1. Prerequisites

    Windows Setup (64-bit)

        Download and run the Python 3.12.10 installer:
        https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe

        Crucial: Ensure the "Add python.exe to PATH" checkbox is checked before proceeding with installation.

        Open PowerShell or Command Prompt, navigate to the NanoVault directory, and initialize your virtual environment:
        
            CMD Prompt
            ---------------------------------------------
            python -m venv venv
            venv\Scripts\activate

    Linux Setup (The "Cool Kids Club")

        Add the deadsnakes repository and install Python 3.12:

            Bash
            ---------------------------------------------
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt update
            sudo apt install -y python3.12 python3.12-venv

        Enter your cloned NanoVault directory, set up your virtual environment, and activate it:

            Bash
            ---------------------------------------------
            python3.12 -m venv venv
            source venv/bin/activate

2. Installation & Environment Configuration

    Confirm your terminal prompt displays the active (venv) prefix.

    Install the required dependencies:

        Bash
        ---------------------------------------------
        pip install -r requirements.txt

    Open config.json in a text editor to set your baseline directory routes (vault_storage_dir, comfy_root, and download_cache_dir).

    (Optional) To authenticate model downloads from restricted repositories, set your Hugging Face or Civitai tokens directly via environment variables rather than hardcoding them into the config:

        Bash
        ---------------------------------------------
        export HF_TOKEN="your_huggingface_token"
        export CIVITAI_TOKEN="your_civitai_api_key"
        (On Windows PowerShell, use $env:HF_TOKEN="your_huggingface_token").

3. Verification & Server Launch

    Edit and create the paths in config.json --OR-- run config_ui.py (optional GUI). If you use the GUI, remember to
    click "Apply" to save the updated config.json.

    Run the CLI configuration check to sanity check directory pathing and JSON integrity before starting the server:

        Bash
        ---------------------------------------------
        python nv.py --config
        Scroll through the output.  If you see red stop sign icons, double-check directory permissions
        and syntax in config.json.

    Once all checks are green, spin up the local server:

        Bash / CMD
        ---------------------------------------------
        python main.py
        Hold Ctrl and click the local endpoint shown in the terminal (typically [http://0.0.0.0:8000] or [http://127.0.0.1:8000])
        This will open the web console in your browser.


4. After Prerequisites are met, subsequent runs only require venv activation and "python main.py".

Support & Community
===================
We sincerely hope NanoVault adds to the quality of your ComfyUI experience and welcome your
feedback for improvements.

    Need help?????
    Open support requests with Mia via the AM Nanotech portal: https://www.amnanotech.com
    
    Please support community development: https://www.patreon.com/cw/AmNanotech
