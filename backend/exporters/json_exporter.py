import json
from core.models import ResearchGraph

class JsonExporter:
    def export(self, graph: ResearchGraph, output_path: str):
        print(f"[*] Exporting JSON data to {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph.model_dump(), f, indent=2, ensure_ascii=False)
