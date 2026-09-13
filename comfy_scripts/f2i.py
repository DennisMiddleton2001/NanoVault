import json
import sys
'''
UTILITY: Converts flat json into indented format for readability.  To convert indented
json back to flat, change indent to zero.
'''
indent = 2

with open(sys.argv[1], 'r') as f:
    data = json.load(f)

with open(f"{sys.argv[1]}_converted.json", 'w') as f:
    if indent:
        json.dump(data, f, indent=indent)
    else:
        json.dump(data, f)


