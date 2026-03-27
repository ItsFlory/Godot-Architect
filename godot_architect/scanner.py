import os
import re
import argparse
from pathlib import Path
from collections import Counter


IGNORE_DIRS = {'.godot', '.git', 'addons', '.vscode', '__pycache__'}
IGNORE_EXTS = {'.import', '.uid', '.getkeep'}

CORE_EXTS = {'.gd', '.tscn', '.godot'}

class GodotContextScanner:
    def __init__(self, root_path, search_term=None, collapse_limit=3):
        self.root_path = Path(root_path)
        self.search_term = search_term.lower() if search_term else None
        self.collapse_limit = collapse_limit

    def _should_ignore(self, path: Path):
        return path.suffix in IGNORE_EXTS or any(p in IGNORE_DIRS for p in path.parts)

    def get_tree_ascii(self, path, prefix=""):

        if not path.exists(): return ""
        

        items = sorted([e for e in path.iterdir() if not self._should_ignore(e)])
        

        dirs = [i for i in items if i.is_dir()]
        files = [i for i in items if i.is_file()]
        

        asset_counts = Counter(f.suffix for f in files if f.suffix not in CORE_EXTS)
        
        lines = []
        

        for i, d in enumerate(dirs):
            is_last = (i == len(dirs) - 1 and not files)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{d.name}")
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(self.get_tree_ascii(d, new_prefix))

       
        core_files = [f for f in files if f.suffix in CORE_EXTS]
        for i, f in enumerate(core_files):
            
            has_more_assets = any(count > 0 for count in asset_counts.values())
            is_last = (i == len(core_files) - 1 and not has_more_assets)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{f.name}")

        
        active_groups = [(ext, count) for ext, count in asset_counts.items() if count > 0]
        for i, (ext, count) in enumerate(active_groups):
            is_last = (i == len(active_groups) - 1)
            connector = "└── " if is_last else "├── "
            ext_name = ext.replace('.', '') or "no-ext"
            
           
            if count <= self.collapse_limit:
                group_files = [f for f in files if f.suffix == ext]
                for j, f in enumerate(group_files):
                    is_sub_last = (is_last and j == len(group_files) - 1)
                    sub_conn = "└── " if is_sub_last else "├── "
                    lines.append(f"{prefix}{sub_conn}{f.name}")
            else:
                lines.append(f"{prefix}{connector}{count} {ext_name} files")

        return "\n".join(filter(None, lines))

    def parse_gd_script(self, file_path):
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            summary = [f"\nFILE: {file_path.relative_to(self.root_path)}"]
            for line in content.split('\n'):
                line = line.strip()
                if any(line.startswith(k) for k in ['class_name', 'extends', 'signal', '@export', 'func ']):
                    if line.startswith('func '): line = line.split(':')[0]
                    summary.append(f"  {line}")
            return "\n".join(summary)
        except: return ""

def main():
    parser = argparse.ArgumentParser(description="Godot 4 Context Extractor")
    parser.add_argument("path", help="Путь к проекту")
    parser.add_argument("-l", "--limit", type=int, default=3, help="Limit for one type before grouping (default: 3)")
    parser.add_argument("-f", "--filter", help="Filter by name")
    parser.add_argument("-c", "--code", action="store_true", help="Only API scripts")
    
    args = parser.parse_args()
    scanner = GodotContextScanner(args.path, args.filter, args.limit)
    
    output = []
    output.append("=== PROJECT TREE (Collapsed assets) ===\n")
    output.append(f"res://")
    output.append(scanner.get_tree_ascii(scanner.root_path))
    
    if args.code:
        output.append("\n=== CODEBASE SUMMARY ===")
        for file in scanner.root_path.rglob('*.gd'):
            if not scanner._should_ignore(file):
                output.append(scanner.parse_gd_script(file))

    result = "\n".join(output)
    Path("godot_context.txt").write_text(result, encoding="utf-8")
    print(f"Done! Result in godot_context.txt")

if __name__ == "__main__":
    main()