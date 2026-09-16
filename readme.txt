NanoVault install instructions (Python 3.12.xx).

Windows users (64 bit only):
==============================================
    Download and install Python 3.12.10 Windows installer from the link shown below.

        https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe

Linux users (members of the "cool kids club"):
==============================================
    a. Add the repository track for pre-compiled Python versions

        sudo add-apt-repository -y ppa:deadsnakes/ppa

    b. Update your package manager database

        sudo apt update

    c. Install python 3.12

        sudo apt install -y python3.12 python3.12-venv

    d. Create virtual environment in the NanoVault folder and activate it.

        python3.12 -m venv venv
        source venv/bin/activate

All users (including the "non-cool kids"):
==============================================
1. Ensure venv is activated (showing "(venv)" in the prompt header).

2. Install requirements.

    pip install -r requirements.txt

3. Setup paths and optional tokens in config.json with a text editor. 
   Be careful you don't hork up the JSON structure.

4. Run NanoVault CLI to verify folder paths.  If you see any red in the splash screen, something
   about your pathing needs to be fixed, or you horked up the JSON. :p

    python nv.py --config

5. If all green, launch the NanoVault server and CTRL+click the url shown in the terminal.

    python main.py

6. If you need assistance, visit http://www.amnanotech.com and use the contact page to open a 
   support request with Mia.  We usually respond within 12 hours.
