# region - Imports
import os
import sys
import json

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
from model_utils.workflow import WorkflowParser
from model_utils.output_schema import OutputSchema
# endregion

class SovereignManager:
    """The universal runtime management class. Routes CLI commands to the correct pipeline."""
    def __init__(self):
        self.env = EnvironmentConfig()

    def execute(self, args_list):
        self.target_path = None
        self.command = args_list[0].lower()
        argc = len(args_list)
        
        if not self.command in self.env.valid_commands:
            return False
                
        if argc > 1:
            self.target_path = args_list[1]
            clean_path = self.target_path.strip(' \t\n\r"\'')

        if '.json' in clean_path.lower():
            model_list = WorkflowParser(self.env, clean_path).get_required_models()
            if not len(model_list):
                return False

        if self.command in ['--a']:
            print(f"{self.env.ico.get('ACT',__class__)} DEPLOY: '{clean_path}'")
            reply = DeploymentPipeline(self.env, model_list).run()
        elif self.command in ['--t']:
            print(f"{self.env.ico.get('ACT',__class__)} TRIM: '{clean_path}'")
            reply = TrimPipeline(self.env, model_list).run()
        elif self.command in ['--e']:
            print(f"{self.env.ico.get("ACT",__class__)} Starting template-driven PURGE for: {clean_path}")
            ans = input('This operation will remove NanoVault files.  Confirm (Y/n)')
            if (ans.lower() == 'y' or ans == ''):
                reply = PurgePipeline(self.env,model_list).run()
            else:
                print(f"{self.env.ico.get('ERR',__class__)} Purge aborted.")
        elif self.command in ['--i']:
            print(f"{self.env.ico.get("ACT",__class__)} Starting template-driven INGEST for: {clean_path}")
            reply = IngestPipeline(self.env, model_list).run()
        elif self.command in ['--scan-vault','--scan-active']:
            vault = True if '--scan-vault' in args_list else False
            print(f"{self.env.ico.get("ACT",__class__)} Starting scan for: {"NanoVault" if vault else "Active Configuration"}")
            reply = AnalyzeModelsFolder(self.env).run(vault)
        elif self.command in ['--model']:
            print(f"{self.env.ico.get("INFO",__class__)} Analyzing '{clean_path}'")
            reply = LoadModel(self.env, clean_path, debug=True).analyze()
        elif self.command in ['--scan-workflows']:
            reply = WorkflowParser(self.env).scan_workflow_path(clean_path)
        else:
            print(f"{self.env.ico.get("ERR",__class__)} Unrecognized command line '{self.command}'")
        print()

'''

UI defaults to the ComfyUI/user/default/workflows folder, but is selectable with a 
folder picker or copy/paste.  Once a folder is selected, the available workflows 
(workflow_name) are shown in a list view (in the main pane).

Each list item has four buttons "add", "trim", "evict", and "storage". The storage option
populates another colum in the view to show how much active space is occupied for that
specific Workflow.

is the hidden fq workflow path in the list.

'''
workflow_path = '/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/'
workflow_name = 'Ernie_T2I3.json'
fq_path = os.path.join(workflow_path, workflow_name)

'''
command_id depends on the selected workflow and the button pressed
by the user.  Buttons for global operations should be in the header 
outside the list view.
'''
command_id=1

commands = [
    ['--a', fq_path],
    ['--t', fq_path],
    ['--i', fq_path],
    ['--s', fq_path],
    ['--scan-active'],
    ['--scan-vault'],
    ['--scan-workflows', workflow_path]
    ]

retval = SovereignManager().execute(commands[command_id])

