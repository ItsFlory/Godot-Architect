import argparse
from pathlib import Path
from .scanner import GodotContextScanner
from .graph import GodotAntiChaosGraph

def run_cli():
    parser = argparse.ArgumentParser(description="Godot Architect - Visualization & Context Tool")
    parser.add_argument("path", help="Path to the Godot project")
    parser.add_argument("--graph", action="store_true", help="Generate HTML graph")
    parser.add_argument("--tree", action="store_true", help="Generate text tree of context")
    parser.add_argument("-l", "--limit", type=int, default=3, help="Limit for one type before grouping")
    parser.add_argument("-c", "--code", action="store_true", help="Add API scripts to the tree")

    args = parser.parse_args()
    project_path = Path(args.path)

    if not project_path.exists():
        print(f"Error: Path {project_path} not found.")
        return

    if args.graph:
        print("Generating graph...")
        gen = GodotAntiChaosGraph(project_path)
        gen.scan()
        gen.save_html("project_graph.html")
        print("File 'project_graph.html' complete.")

    if args.tree:
        print("Generating context tree...")
        scanner = GodotContextScanner(project_path, collapse_limit=args.limit)
        output = ["=== PROJECT TREE (Collapsed assets) ===\n", "res://", scanner.get_tree_ascii(scanner.root_path)]
        
        if args.code:
            output.append("\n=== CODEBASE SUMMARY ===")
            for file in scanner.root_path.rglob('*.gd'):
                if not scanner._should_ignore(file):
                    output.append(scanner.parse_gd_script(file))
        
        result = "\n".join(output)
        Path("godot_context.txt").write_text(result, encoding="utf-8")
        print("File 'godot_context.txt' complete.")