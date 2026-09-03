import logging
import re
import urllib.parse
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("crypto_explorer.eprint")

def search_eprint_by_title(title: str) -> Optional[str]:
    """
    Attempts to find the IACR ePrint ID for a given paper title.
    We query the ePrint search page.
    """
    # ePrint search URL: https://eprint.iacr.org/search?q=...
    # The search endpoint can be basic.
    query = urllib.parse.quote_plus(title)
    url = f"https://eprint.iacr.org/search?q={query}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        normalized_title = re.sub(r"\W+", " ", title).strip().lower()
        
        # Find all <a> tags
        for a in soup.find_all('a'):
            href = a.get('href', '')
            # ePrint IDs are typically /YYYY/NNN
            if href.startswith('/') and len(href.split('/')) == 3:
                parts = href.split('/')
                normalized_link = re.sub(r"\W+", " ", " ".join(a.stripped_strings)).strip().lower()
                if (
                    parts[1].isdigit()
                    and len(parts[1]) == 4
                    and parts[2].isdigit()
                    and normalized_title
                    and normalized_link
                    and (normalized_title in normalized_link or normalized_link in normalized_title)
                ):
                    return f"{parts[1]}/{parts[2]}"
        
        return None
    except Exception as e:
        logger.warning("eprint search failed title=%r error=%s", title, e)
        return None

def get_eprint_url(eprint_id: str) -> str:
    return f"https://eprint.iacr.org/{eprint_id}"

def get_eprint_pdf_url(eprint_id: str) -> str:
    return f"https://eprint.iacr.org/{eprint_id}.pdf"
