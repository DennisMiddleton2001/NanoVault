# region - Imports
import os
import sys
import json
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
comfyui_root = os.path.abspath(os.path.join(current_dir, ".."))
if comfyui_root not in sys.path:
    sys.path.insert(0, comfyui_root)

from .env_config import EnvironmentConfig
from .ingest_pipeline import IngestPipeline
from .deployment_pipeline import DeploymentPipeline
from .purge_pipeline import PurgePipeline
from .trim_pipeline import TrimPipeline
from .test_sweep import AnalyzeModelsFolder
from .load_model import LoadModel
from .workflow import WorkflowParser
from .workflow import WorkflowEnumerator

# endregion

class SovereignManager:
    """The universal runtime management class. Routes CLI commands to the correct pipeline."""
    def __init__(self, banner=False):
        self.env = EnvironmentConfig(banner = banner)
        self.valid_commands = [
            '--a',
            '--as',
            '--t',
            '--i',
            '--e',
            '--s',
            '--single-add',
            '--model',
            '--scan-active',
            '--scan-vault',
            '--scan-workflow',
            '--list-workflows',
            '--query-metal-storage',
            '--scan-all',
            '--config']

    def is_valid_command(self, command):
        return True if command in self.valid_commands else False

    def execute(self, args_list):
        start_time = datetime.now()
        print(f"[{start_time}] Command: {args_list}")

        self.target_path = None
        self.command = args_list[0].lower()
        argc = len(args_list)
                
        if not self.is_valid_command(self.command):
            return {"message" : "Invalid command."}

        if argc > 1:
            self.target_path = args_list[1]
            clean_path = self.target_path.strip(' \t\n\r"\'')
        else:
            clean_path = ''

        if '.json' in clean_path.lower():
            model_list = WorkflowParser(self.env, clean_path).get_required_models()
            if not len(model_list):
                print(f"{self.env.ico.get('WRN',__class__)} No models found in '{clean_path}'")
                reply = {
                    "command" : "Parse Workflow",
                    "message" : f"No models found in '{clean_path}'"
                }
                return reply
        
        if self.command in ['--config']:
            if self.env.print_config():
                message = "Valid configuration found."
            else:
                message = f"NanoVault configuration is invalid. Check '{self.env.env_path}' file."
            reply = {
                "command"    : "CheckAppConfiguration",
                "message"    : message
                }
        elif self.command in ['--a']:
                    print(f"{self.env.ico.get('ACT',__class__)} DEPLOY: '{clean_path}'")
                    reply = DeploymentPipeline(self.env, model_list).run()
        elif self.command in ['--as']:
                    print(f"{self.env.ico.get('ACT',__class__)} DEPLOY: '{clean_path}'")
                    reply = DeploymentPipeline(self.env, model_list, spot_install = True).run()
        elif self.command in ['--t']:
            print(f"{self.env.ico.get('ACT',__class__)} TRIM: '{clean_path}'")
            reply = TrimPipeline(self.env, model_list).run()
        elif self.command in ['--e']:
            print(f"{self.env.ico.get("ACT",__class__)} Starting template-driven PURGE for: {clean_path}")
            reply = PurgePipeline(self.env,model_list).run()
        elif self.command in ['--i']:
            print(f"{self.env.ico.get("ACT",__class__)} Starting template-driven INGEST for: {clean_path}")
            reply = IngestPipeline(self.env, model_list).run()
        elif self.command in ['--scan-vault','--scan-active']:
            vault = True if '--scan-vault' in args_list else False
            print(f"{self.env.ico.get("ACT",__class__)} Starting scan for: {"NanoVault" if vault else "Active Configuration"}")
            reply = AnalyzeModelsFolder(self.env).run(vault)
        elif self.command in ['--single-add']:
            if argc > 3:
                # For single install, just create a model list with one entry.
                model_list = [
                    {"model_name": args_list[1], 'model_path': args_list[2],'model_url' : args_list[3] if argc == 4 else ""}
                ]
                reply = DeploymentPipeline(self.env,model_list).run()
        elif self.command in ['--model']:
            print(f"{self.env.ico.get("INFO",__class__)} Analyzing '{clean_path}'")
            reply = LoadModel(self.env, clean_path, debug=True).analyze()
        elif self.command in ['--scan-workflow']:
            reply = WorkflowParser(self.env,args_list[1]).get_required_models()
        elif self.command in ['--list-workflows']:
            reply = WorkflowEnumerator(self.env,args_list[1]).run()
        elif self.command in ['--query-metal-storage','--scan-all']:
            vault_info  = AnalyzeModelsFolder(self.env).run(True)
            active_info = AnalyzeModelsFolder(self.env).run(False)
            reply = {"active_usage" : active_info["active_usage"],
                     "vault_usage" : vault_info["vault_usage"]}
        else:
            print(f"{self.env.ico.get("ERR",__class__)} Unrecognized command line '{self.command}'")
            reply = None
        
        # Don't bloat the log with these functions.
        if not self.command in ["--list-workflows", "--query-metal-storage"]:
            lines = []
            lines.append(f"[START]   : {start_time}\n")
            lines.append(f"[COMMAND] : {args_list}\n")
            lines.append(f"[END]     : {datetime.now()}\n")
            lines.append('=' * 80 + "\n")
            lines.append(json.dumps(reply, indent=2) + "\n")
            lines.append('=' * 80 + '\n')

            log_folder = os.path.join(".","logs")
            if not os.path.exists(log_folder):
                os.makedirs(log_folder, exist_ok=True)


            logfile_path = os.path.join(log_folder, f"{datetime.now().strftime('%Y%m%d')}.log")
            with open(logfile_path, 'a') as f:
                for l in lines:
                    f.write(l)
        
        return reply