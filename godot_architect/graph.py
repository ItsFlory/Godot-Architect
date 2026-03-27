import os
import json
import re
import argparse
from pathlib import Path

COLOR_GD = '#4e9af1'
COLOR_TSCN = '#5cf14e'

class GodotAntiChaosGraph:
    def __init__(self, project_path):
        self.root = Path(project_path)
        self.nodes = []
        self.links = []
        self.file_map = {}

    def scan(self):
        
        for file in self.root.rglob('*'):
            if file.suffix in ['.gd', '.tscn'] and '.godot' not in str(file):
                rel_path = str(file.relative_to(self.root)).replace('\\', '/')
                node_data = {
                    "id": rel_path,
                    "name": file.name,
                    "type": file.suffix[1:],
                    "links_count": 0
                }
                self.nodes.append(node_data)
                self.file_map[rel_path] = node_data

       
        links_set = set()
        for node in self.nodes:
            file_path = self.root / node['id']
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                raw_paths = re.findall(r'res://([^"\'\)\s>]+)', content)
                
                for p in raw_paths:
                    clean_p = p.split('"')[0].split("'")[0].split(" ")[0].strip()
                    if clean_p in self.file_map and clean_p != node['id']:
                        pair = tuple(sorted((node['id'], clean_p)))
                        if pair not in links_set:
                            self.links.append({"source": node['id'], "target": clean_p})
                            links_set.add(pair)
                            
                            self.file_map[node['id']]['links_count'] += 1
                            self.file_map[clean_p]['links_count'] += 1
            except: pass

    def save_html(self, output_file="project_graph.html"):
        data_json = json.dumps({"nodes": self.nodes, "links": self.links})
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Godot Architect - Anti-Chaos</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; background: #1a1a1a; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}
        #controls {{ position: absolute; top: 15px; left: 15px; background: rgba(30,30,30,0.9); padding: 15px; border-radius: 10px; border: 1px solid #444; z-index: 100; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
        .node-label {{ pointer-events: none; font-size: 10px; fill: #fff; opacity: 0.7; }}
        line {{ stroke: #555; stroke-opacity: 0.2; stroke-width: 1px; transition: stroke-opacity 0.3s; }}
        line.active {{ stroke: #fff; stroke-opacity: 1; stroke-width: 2px; }}
        circle {{ cursor: pointer; stroke: #fff; stroke-width: 1px; transition: r 0.3s; }}
        circle:hover {{ r: 15; }}
        .btn {{ background: #444; border: 0; color: white; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; margin-top: 5px; }}
        .btn:hover {{ background: #666; }}
    </style>
</head>
<body>
    <div id="controls">
        <b style="color: {COLOR_GD}">Godot Visual Audit</b><br>
        <small>Found links: {len(self.links)}</small>
        <div style="margin-top:10px;">
            <button class="btn" onclick="toggleLabels()">Toggle labels</button><br>
            <button class="btn" onclick="resetZoom()">Reset camera</button>
        </div>
        <p style="font-size: 10px; opacity: 0.6; margin-top: 10px;">* Hover over a node to<br>highlight its connections</p>
    </div>
    <div id="graph"></div>
    <script>
        const data = {data_json};
        let showLabels = true;

        const width = window.innerWidth;
        const height = window.innerHeight;

        const zoom = d3.zoom().on("zoom", (event) => g.attr("transform", event.transform));
        const svg = d3.select("#graph").append("svg")
            .attr("width", width).attr("height", height)
            .call(zoom);

        const g = svg.append("g");

        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(d => {{
                return 100 + (Math.max(d.source.links_count, d.target.links_count) * 2);
            }}))
            .force("charge", d3.forceManyBody().strength(-500))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide().radius(25));

        const link = g.append("g").selectAll("line")
            .data(data.links).join("line");

        const node = g.append("g").selectAll("circle")
            .data(data.nodes).join("circle")
            .attr("r", d => Math.min(15, 7 + (d.links_count / 2))) // Размер зависит от связей
            .attr("fill", d => d.type === 'gd' ? '{COLOR_GD}' : '{COLOR_TSCN}')
            .on("mouseover", highlight)
            .on("mouseout", unhighlight)
            .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

        const label = g.append("g").selectAll("text")
            .data(data.nodes).join("text")
            .attr("class", "node-label")
            .attr("dx", 15).attr("dy", ".35em")
            .text(d => d.name);

        function highlight(event, d) {{
            link.classed("active", l => l.source.id === d.id || l.target.id === d.id);
            d3.select(this).attr("stroke-width", 3);
        }}

        function unhighlight() {{
            link.classed("active", false);
            node.attr("stroke-width", 1);
        }}

        function toggleLabels() {{
            showLabels = !showLabels;
            label.style("display", showLabels ? "block" : "none");
        }}

        function resetZoom() {{
            svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
        }}

        simulation.on("tick", () => {{
            link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
            node.attr("cx", d => d.x).attr("cy", d => d.y);
            label.attr("x", d => d.x).attr("y", d => d.y);
        }});

        function dragstarted(event) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x; event.subject.fy = event.subject.y;
        }}
        function dragged(event) {{
            event.subject.fx = event.x; event.subject.fy = event.y;
        }}
        function dragended(event) {{
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null; event.subject.fy = null;
        }}
    </script>
</body>
</html>
"""
        Path(output_file).write_text(html_content, encoding='utf-8')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    
    gen = GodotAntiChaosGraph(args.path)
    gen.scan()
    gen.save_html()
    print("Graph ready! The 'chaos' problem is solved through link transparency.")