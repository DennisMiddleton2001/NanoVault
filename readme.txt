NanoVault install instructions (Python 3.12.13).

# 1. Add the repository track for pre-compiled Python versions

sudo add-apt-repository -y ppa:deadsnakes/ppa

# 2. Update your package manager database

sudo apt update

# 3. Install python 3.12

sudo apt install -y python3.12 python3.12-venv

# 4. Create virtual environment and activate it.

python3.12 -m venv venv
source venv/bin/activate

# 5. Install requirements.

pip install -r requirements.txt

# 6. Adjust paths in config.json.

nano config.json

# 7. Run NanoVault CLI to verify folder paths

python nv.py --config

# 8. Launch the NanoVault server and CTRL+click the url

python main.py
