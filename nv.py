

from model_utils.nano_arch import SovereignManager

args = ['--list-workflows', '/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/']

results = SovereignManager().execute(args)