import logging
from typing import Any, Dict, List, Protocol

from core.models import Paper, GraphNode, ResearchGraph

logger = logging.getLogger("crypto_explorer.graph")


class PaperProvider(Protocol):
    def search_paper(self, query: str, limit: int = 5) -> List[Dict[str, Any]]: ...

    def get_citations(self, paper_id: str, limit: int = 100) -> List[Dict[str, Any]]: ...

class GraphBuilder:
    def __init__(self, provider: PaperProvider):
        self.provider = provider

    def parse_author_list(self, raw_authors: List[Dict]) -> List[Dict]:
        return [{"authorId": a.get("authorId"), "name": a.get("name")} for a in raw_authors if a.get("name")]

    def dict_to_paper(self, p_dict: Dict) -> Paper:
        external_ids = p_dict.get("externalIds") or {}
        open_access_pdf = p_dict.get("openAccessPdf") or {}
        return Paper(
            paperId=p_dict["paperId"],
            title=p_dict.get("title", "Unknown"),
            authors=self.parse_author_list(p_dict.get("authors", [])),
            year=p_dict.get("year"),
            venue=p_dict.get("venue"),
            abstract=p_dict.get("abstract"),
            tldr=p_dict.get("tldr", {}).get("text") if isinstance(p_dict.get("tldr"), dict) else p_dict.get("tldr"),
            citationCount=p_dict.get("citationCount", 0),
            referenceCount=p_dict.get("referenceCount", 0),
            url=p_dict.get("url"),
            doi=external_ids.get("DOI"),
            pdf_url=open_access_pdf.get("url") if isinstance(open_access_pdf, dict) else None,
        )

    def build_graph(self, query: str, max_nodes: int = 50) -> ResearchGraph:
        logger.info("seed search query=%r", query)
        search_results = self.provider.search_paper(query, limit=1)
        if not search_results:
            raise ValueError(f"No papers found for query: {query}")
        return self.build_graph_from_seed(search_results[0], max_nodes=max_nodes)

    def build_graph_from_seed(self, seed_dict: Dict[str, Any], max_nodes: int = 50) -> ResearchGraph:
        seed_paper = self.dict_to_paper(seed_dict)
        seed_paper.role = "Foundation"
        
        graph = ResearchGraph(seed_paper_id=seed_paper.paperId)
        
        # Add seed to graph
        seed_node = GraphNode(paper=seed_paper)
        graph.nodes[seed_paper.paperId] = seed_node
        
        logger.info(
            "seed found paper_id=%s title=%r year=%s",
            seed_paper.paperId,
            seed_paper.title,
            seed_paper.year,
        )
        logger.info("citation fetch started seed_paper_id=%s", seed_paper.paperId)
        
        raw_citations = self.provider.get_citations(seed_paper.paperId, limit=100)
        unique_citations: Dict[str, Dict] = {}
        for citation in raw_citations:
            paper_id = citation.get("paperId")
            if not paper_id or paper_id == seed_paper.paperId:
                continue
            existing = unique_citations.get(paper_id)
            if existing is None or citation.get("citationCount", 0) > existing.get("citationCount", 0):
                unique_citations[paper_id] = citation
        raw_citations = list(unique_citations.values())
        logger.info("citation fetch completed unique_count=%s", len(raw_citations))
        
        # We only want to keep the most relevant/highly cited ones to keep the graph manageable
        # Sort by citation count (global) to find the most impactful descendants
        raw_citations.sort(key=lambda x: x.get("citationCount", 0), reverse=True)
        top_citations = raw_citations[:max_nodes]
        
        for p_dict in top_citations:
            p_id = p_dict["paperId"]
            if p_id not in graph.nodes:
                paper = self.dict_to_paper(p_dict)
                graph.nodes[p_id] = GraphNode(paper=paper)
            
            # Seed paper is cited by this node
            graph.nodes[seed_paper.paperId].cited_by.append(p_id)
            graph.nodes[p_id].citations.append(seed_paper.paperId)
            graph.nodes[seed_paper.paperId].in_degree_subgraph += 1

        # Try to find cross-citations among the nodes we kept
        # Note: In a real heavy system we'd query citations for ALL top nodes to find cross-edges.
        # But for MVP A, we can skip or do a lightweight check.
        # Actually, if we query references for each of the top nodes and see if they cite each other.
        logger.info("graph build completed depth=1 nodes=%s", len(graph.nodes))
        
        return graph
