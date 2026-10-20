import argparse
import json
import re
import sys

def convert_paths(data, target_platform):
    """Recursively search and convert relative path separators in strings."""
    if isinstance(data, dict):
        return {k: convert_paths(v, target_platform) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_paths(item, target_platform) for item in data]
    elif isinstance(data, str):
        if data.startswith("http://") or data.startswith("https://"):
            return data
        
        if target_platform == 'L' and '\\' in data:
            return data.replace('\\', '/')
            
        elif target_platform == 'W' and '/' in data:
            return data if re.fullmatch(r'\d{2,4}[/-]\d{1,2}[/-]\d{1,4}', data) else data.replace('/', '\\')
            
    return data

def main():
    parser = argparse.ArgumentParser(
        prog="template_convert.py",
        description="Template Converter: JSON path syntax standardizer (Windows <-> Linux)",
        epilog="Examples:\n  python template_convert.py -i in.json -o out.json -p L\n  python template_convert.py --input in.json --output out.json --platform W",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument('-i', '--input', required=True, help="Input JSON file path")
    parser.add_argument('-o', '--output', required=True, help="Output JSON file path")
    parser.add_argument('-p', '--platform', required=True, choices=['W', 'L'], help="Target platform: 'W' (Windows) or 'L' (Linux)")
    
    # Trigger help text automatically if no arguments are passed
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        converted_data = convert_paths(data, args.platform)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=4)
            
        print(f"Station! Conversion successful. Data aligned for platform '{args.platform}' and secured at: {args.output}")
        
    except Exception as e:
        print(f"Pipeline error encountered during conversion: {e}")

if __name__ == "__main__":
    main()