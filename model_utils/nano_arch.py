import os
import sys
import json
import hashlib
import shutil
import subprocess

# Add model_tools to the system path so libraries import properly.
current_dir = os.path.dirname(os.path.abspath(__file__))
comfyui_root = os.path.abspath(os.path.join(current_dir, ".."))
if comfyui_root not in sys.path:
    sys.path.insert(0, comfyui_root)

from model_utils.env_config import EnvironmentConfig
from model_utils.ingest_pipeline import IngestPipeline
from model_utils.deployment_pipeline import DeploymentPipeline
from model_utils.purge_pipeline import PurgePipeline
from model_utils.trim_pipeline import TrimPipeline
from model_utils.test_sweep import AnalyzeModelsFolder
from model_utils.load_model import LoadModel
from model_utils.vault_manager import VaultManager
from workflow import WorkflowParser

class SovereignManager:
    """The universal runtime management class. Routes CLI commands to the correct pipeline."""
    def __init__(self):
        self.env = EnvironmentConfig()


    def execute(self, args_list):
        self.target_path = None
        self.command = None
        argc = len(args_list)

        if not sys.argv[1] in ['--a', '--t', '--e', '--i']:
            return False

        self.command = sys.argv[1]
        
        if argc > 2:
            self.target_path = args_list[2]
            clean_path = self.target_path.strip(' \t\n\r"\'')

        #If we're here, we are scanning a workflow file.
        model_list = WorkflowParser(self.env, clean_path).get_required_models()

        if self.command in ['--t']:

            print(f"{self.env.ico.get('ACT',__class__)} TRIM: '{clean_path}'")
            TrimPipeline(self.env, model_list).run()
        elif self.command in ['--a']:

            print(f"{self.env.ico.get('ACT',__class__)} DEPLOY: '{clean_path}'")
            DeploymentPipeline(self.env, model_list).run()
        elif self.command in ['--e']:
            #TESTED
            print(f"{self.env.ico.get("ACT",__class__)} Starting template-driven PURGE for: {clean_path}")
            ans = input('This operation will remove NanoVault files.  Confirm (Y/n)')
            if (ans.lower() == 'y' or ans == ''):
                pipe = PurgePipeline(self.env,model_list).run()
            else:
                print(f"{self.env.ico.get('ERR',__class__)} Purge aborted.")
        elif self.command in ['--i']:
            #TESTED
            print(f"{self.env.ico.get("ACT",__class__)} Starting template-driven INGEST for: {clean_path}")
            IngestPipeline(self.env, model_list).run()
        elif self.command in ['--scan-vault','--scan-active']:
            ### TESTED
            pipe = AnalyzeModelsFolder(self.env)
            if ('--scan-vault' in args_list):
                vault = True
            else:
                vault = False
            print(json.dumps(pipe.run(vault), indent=4))
        elif self.command in ['--model']:
            ### TESTED
            print(f"{self.env.ico.get("INFO",__class__)} Analyzing '{clean_path}'")
            pipe = LoadModel(self.env, clean_path, debug=True)
            pipe.analyze()
        else:
            print(f"{self.env.ico.get("ERR",__class__)} Unrecognized command flag '{self.command}'")

sm = SovereignManager()
sm.execute(sys.argv)
