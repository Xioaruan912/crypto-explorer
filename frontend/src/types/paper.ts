export interface Paper {
  id: string;
  titleZh?: string;
  titleEn: string;
  authors: string[];
  year: number;
  venue: string;
  venueFull?: string;
  category:
    | "foundation"
    | "security"
    | "efficiency"
    | "scalability"
    | "variant"
    | "application";
  citations?: number;
  references?: number;
  abstractZh?: string;
  abstractEn?: string;
  eprint?: string;
  doi?: string;
  pdfUrl?: string;
  semanticScholarUrl?: string;
  dblpUrl?: string;
  contributionsZh?: string[];
  topicsZh?: string[];
}

