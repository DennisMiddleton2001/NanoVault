class LogIcons:
    def __init__(self):
        self.debug = False
        self.icons = standard_icons = {
            "ERR"  : "🛑 ",  # Hard errors (e.g., JSON decode failure, missing template)
            "ACT"  : "⚙️  ", # Action/Execution (e.g., moving files, downloading)
            "SRCH" : "🔍 ",  # Searching/Hunting (e.g., parsing the nodes)
            "DONE" : "⭐ ",  # Success/Completion
            "WRN"  : "☢️  ",  # Warning (e.g., Metadata missing, but posixpath auto-routed it)
            "ALRT" : "⚠️ ",  # Alert (e.g., The "Oh Well" failsafe: no URL or directory found, manual review needed)
            "INFO" : "🔷 ",  # General Info (e.g., Vault status, skipping an existing file. A bit more sci-fi/terminal than a boring 'i')
            "COMM" : "📡 ",  # Communication
            "SCAN" : "🕵 ",  # Scanning a resource
            "BOX"  : "📦 ",   # Packaging reference
            "KEY"  : "🔑 ",
            "LOCK" : "🔒 ",
            "LIGHT": "🚨 ",
            "FOLD" : "📂 "
        }

    def get(self, id, class_name=None):
        
        if (class_name and self.debug):
            n = f'{class_name}'
            ret = f'{self.icons.get(id)} [{n[8:-2]}]'
        else:
            ret = f'{self.icons.get(id,__class__)}'
        return ret
    
    def sep(self,lvl, sep_len = 100):
        val = ["#","=","-",".","`"]
        bar = ""
        for i in range(0,sep_len):
            bar = bar+val[lvl]
        return bar


    




        
