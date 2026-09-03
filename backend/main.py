import argparse
import os
from rich.console import Console
from fetchers.semantic_scholar import SemanticScholarClient
from analyzer.graph_builder import GraphBuilder
from analyzer.heuristic_engine import HeuristicEngine
from exporters.markdown_exporter import MarkdownExporter
from exporters.json_exporter import JsonExporter

def main():
    parser = argparse.ArgumentParser(description="Cryptography Research Explorer (MVP A)")
    parser.add_argument("--query", type=str, required=True, help="Topic or Seed paper title to search")
    parser.add_argument("--max-nodes", type=int, default=20, help="Max number of descendant papers to analyze")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory to save the reports")
    args = parser.parse_args()

    console = Console()
    console.print(f"[bold blue]🚀 Starting Crypto Research Explorer[/bold blue] (Topic: [green]{args.query}[/green])\n")

    os.makedirs(args.output_dir, exist_ok=True)

    # Init modules
    s2_client = SemanticScholarClient()
    builder = GraphBuilder(s2_client)
    engine = HeuristicEngine()
    md_exporter = MarkdownExporter()
    json_exporter = JsonExporter()

    try:
        with console.status("[bold green]Building citation graph (this may take a minute)...[/bold green]"):
            graph = builder.build_graph(args.query, max_nodes=args.max_nodes)
        
        with console.status("[bold green]Applying Heuristic Engine...[/bold green]"):
            engine.apply_heuristics(graph)
            
        with console.status("[bold green]Generating Reports...[/bold green]"):
            safe_query = args.query.replace(" ", "_").replace("/", "_")
            md_path = os.path.join(args.output_dir, f"{safe_query}_report.md")
            json_path = os.path.join(args.output_dir, f"{safe_query}_data.json")
            
            md_exporter.export(graph, args.query, md_path)
            json_exporter.export(graph, json_path)
            
        console.print("\n[bold green]✅ Pipeline Complete![/bold green]")
        console.print(f"📄 Markdown Report: [bold]{md_path}[/bold]")
        console.print(f"📊 JSON Data: [bold]{json_path}[/bold]")

    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    main()
