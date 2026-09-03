from core.models import ResearchGraph
from fetchers.eprint import get_eprint_url, get_eprint_pdf_url

class MarkdownExporter:
    def __init__(self):
        pass

    def _format_authors(self, authors: list) -> str:
        if not authors:
            return "Unknown Authors"
        names = [a.name for a in authors if hasattr(a, 'name') and a.name]
        if len(names) > 3:
            return f"{names[0]} et al."
        return ", ".join(names)

    def export(self, graph: ResearchGraph, query: str, output_path: str):
        print(f"[*] Exporting Markdown report to {output_path}...")
        
        with open(output_path, "w", encoding="utf-8") as f:
            # Header
            f.write(f"# 🔍 Cryptography Research Explorer\n\n")
            f.write(f"**Topic:** {query}\n\n")
            f.write("---\n\n")
            
            # Evolution Taxonomy Tree
            f.write(f"## 🌳 Research Evolution Taxonomy\n\n")
            f.write(f"```text\n")
            f.write(f"{query}\n")
            f.write(f"│\n")
            
            cats = list(graph.taxonomy.keys())
            for i, cat in enumerate(cats):
                is_last_cat = (i == len(cats) - 1)
                branch_char = "└──" if is_last_cat else "├──"
                pipe_char = " " if is_last_cat else "│"
                
                f.write(f"{branch_char} {cat}\n")
                
                # List papers in this category
                papers_in_cat = graph.taxonomy[cat]
                # Sort papers by year
                papers_in_cat.sort(key=lambda pid: (graph.nodes[pid].paper.year or 0), reverse=False)
                
                for j, pid in enumerate(papers_in_cat):
                    node = graph.nodes[pid]
                    is_last_paper = (j == len(papers_in_cat) - 1)
                    paper_branch_char = "└──" if is_last_paper else "├──"
                    
                    year = node.paper.year or "Unknown"
                    author_str = self._format_authors(node.paper.authors)
                    
                    f.write(f"{pipe_char}     {paper_branch_char} {author_str} {year}\n")
                
                f.write(f"{pipe_char}\n")
            
            f.write(f"```\n\n")
            f.write("---\n\n")
            
            # Paper Details
            f.write(f"## 📄 Detailed Paper Map\n\n")
            
            # Sort all nodes by category, then year
            sorted_pids = []
            for cat in cats:
                pids = graph.taxonomy[cat]
                pids.sort(key=lambda pid: (graph.nodes[pid].paper.year or 0), reverse=True)
                sorted_pids.extend(pids)
                
            for pid in sorted_pids:
                node = graph.nodes[pid]
                p = node.paper
                
                # Links
                links = []
                if p.eprint_id:
                    links.append(f"[[ePrint]({get_eprint_url(p.eprint_id)})]")
                    links.append(f"[[PDF]({get_eprint_pdf_url(p.eprint_id)})]")
                if p.url:
                    links.append(f"[[S2]({p.url})]")
                
                links_str = " ".join(links)
                role_icon = "★★★★★ Foundation Paper" if p.role == "Foundation" else (
                    "⭐ Key Milestone" if p.role == "Key Milestone" else "📄 Derivative Work"
                )
                
                f.write(f"### {p.title}\n")
                f.write(f"- **Authors:** {self._format_authors(p.authors)}\n")
                f.write(f"- **Venue / Year:** {p.venue or 'Unknown Venue'} / {p.year or 'Unknown'}\n")
                f.write(f"- **Role:** {role_icon}\n")
                f.write(f"- **Category:** {p.category}\n")
                f.write(f"- **Metrics:** References: {len(node.citations)} | Cited by: {p.citationCount}\n")
                if p.tldr:
                    f.write(f"- **TLDR:** {p.tldr}\n")
                f.write(f"- **Links:** {links_str}\n\n")
        
        print(f"[*] Export complete!")
