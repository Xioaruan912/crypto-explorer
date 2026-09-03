import logging
import os
import re

from core.models import ResearchGraph
from fetchers.eprint import search_eprint_by_title

logger = logging.getLogger("crypto_explorer.heuristics")

TAXONOMY_RULES = {
    "Security Foundations": [r"standard assumption", r"lwe", r"cdh", r"ddh", r"pairing", r"adaptive security", r"adaptively secure"],
    "Efficiency": [r"efficien", r"compact", r"short", r"size"],
    "Large Identity Spaces": [r"large", r"identity space", r"cuckoo", r"dictionary"],
    "Post-Quantum": [r"post-quantum", r"lattice", r"quantum", r"qrom"],
    "Advanced Variants": [r"revocation", r"traceability", r"leakage", r"distributed", r"threshold"]
}

class HeuristicEngine:
    def __init__(self):
        self.resolve_eprint = os.getenv("ENABLE_EPRINT_LOOKUP", "false").lower() in {"1", "true", "yes"}
        
    def _categorize(self, text: str) -> str:
        if not text:
            return "General / Applications"
        text = text.lower()
        
        # simple regex search
        for category, patterns in TAXONOMY_RULES.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return category
                    
        return "General / Applications"

    def apply_heuristics(self, graph: ResearchGraph):
        logger.info("heuristic analysis started nodes=%s", len(graph.nodes))
        
        # Identify Milestones
        # Sort all non-seed nodes by their global citation count (as a proxy for milestone)
        nodes_list = [n for p_id, n in graph.nodes.items() if p_id != graph.seed_paper_id]
        nodes_list.sort(key=lambda n: n.paper.citationCount, reverse=True)
        
        # Mark top 3 as Key Milestone
        for i, node in enumerate(nodes_list):
            if i < 3:
                node.paper.role = "Key Milestone"
            else:
                node.paper.role = "Derivative Work"
                
        # Categorize
        for p_id, node in graph.nodes.items():
            if p_id == graph.seed_paper_id:
                node.paper.category = "Foundations"
            else:
                # Use title, abstract, and tldr for categorization
                combined_text = f"{node.paper.title} {node.paper.abstract or ''} {node.paper.tldr or ''}"
                cat = self._categorize(combined_text)
                node.paper.category = cat
                
            # Add to taxonomy dict
            cat = node.paper.category
            if cat not in graph.taxonomy:
                graph.taxonomy[cat] = []
            graph.taxonomy[cat].append(p_id)
            
            if self.resolve_eprint:
                logger.debug("eprint resolution title=%r", node.paper.title)
                eprint_id = search_eprint_by_title(node.paper.title)
                if eprint_id:
                    node.paper.eprint_id = eprint_id

        logger.info("heuristic analysis completed categories=%s", len(graph.taxonomy))
