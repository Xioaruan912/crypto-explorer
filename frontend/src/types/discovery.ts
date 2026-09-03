import { Paper } from './paper';

export type DiscoveryMode = 'papers' | 'authors' | 'venues';
export type PaperSort = 'relevance' | 'citations' | 'newest';
export type EntitySort = 'relevance' | 'citations' | 'works';

export interface PaperSearchParams {
  query: string;
  fromYear?: number;
  toYear?: number;
  author?: string;
  venue?: string;
  sort?: PaperSort;
  openAccess?: boolean;
}

export interface DiscoveryAuthor {
  id: string;
  name: string;
  worksCount: number;
  citedByCount: number;
  institutions: string[];
  orcid?: string;
  openAlexUrl?: string;
}

export interface DiscoveryAuthorDetail extends DiscoveryAuthor {
  topWorks: Paper[];
}

export interface DiscoveryVenue {
  id: string;
  name: string;
  type?: string;
  worksCount: number;
  citedByCount: number;
  issn?: string;
  homepageUrl?: string;
  isOpenAccess: boolean;
  isInDoaj: boolean;
  hostOrganization?: string;
  openAlexUrl?: string;
}

export interface DiscoveryVenueDetail extends DiscoveryVenue {
  topWorks: Paper[];
}
