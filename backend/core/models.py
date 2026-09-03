from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Author(BaseModel):
    authorId: Optional[str] = None
    name: str

class Paper(BaseModel):
    paperId: str
    title: str
    authors: List[Author] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    abstract: Optional[str] = None
    tldr: Optional[str] = None
    citationCount: int = 0
    referenceCount: int = 0
    url: Optional[str] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    
    # Specific Crypto fields
    eprint_id: Optional[str] = None
    
    # Analysis Fields (Filled by heuristic or LLM)
    role: str = "Node"  # e.g., "Foundation", "Milestone", "Node"
    category: str = "Uncategorized"  # taxonomy branch
    improves: Optional[str] = None
    security: Optional[str] = None
    assumptions: Optional[str] = None

class GraphNode(BaseModel):
    paper: Paper
    in_degree_subgraph: int = 0
    citations: List[str] = Field(default_factory=list)  # list of paperIds that this paper cites (outgoing edges)
    cited_by: List[str] = Field(default_factory=list)   # list of paperIds that cite this paper (incoming edges)

class ResearchGraph(BaseModel):
    seed_paper_id: str
    nodes: Dict[str, GraphNode] = Field(default_factory=dict)
    taxonomy: Dict[str, List[str]] = Field(default_factory=dict) # category -> list of paperIds
