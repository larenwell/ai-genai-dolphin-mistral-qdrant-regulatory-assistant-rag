"""
Query Parser - FASE C

Extracts entities and keywords from user queries for intelligent filtering.
"""

import re
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.retrieval_config import QUERY_PARSER_CONFIG


class QueryParser:
    """
    Parses user queries to extract:
    - Norms mentioned (Ley, DS, RM, NFPA, etc.)
    - Articles, chapters, sections
    - Keywords for sparse search
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize query parser.
        
        Args:
            config: Parser configuration (defaults to QUERY_PARSER_CONFIG)
        """
        self.config = config or QUERY_PARSER_CONFIG
        
        # Compile regex patterns for performance
        self.norm_patterns_compiled = {
            norm_type: re.compile(pattern, re.IGNORECASE)
            for norm_type, pattern in self.config["norm_patterns"].items()
        }
        
        self.article_pattern = re.compile(
            self.config["article_pattern"], 
            re.IGNORECASE
        )
        self.chapter_pattern = re.compile(
            self.config["chapter_pattern"], 
            re.IGNORECASE
        )
        self.section_pattern = re.compile(
            self.config["section_pattern"], 
            re.IGNORECASE
        )
        
        self.stopwords = set(self.config["stopwords"])
    
    def parse(self, query: str) -> Dict:
        """
        Parse query and extract all entities.
        
        Args:
            query: User query string
        
        Returns:
            Dict with extracted entities:
            {
                "norms": [{"type": "ley", "code": "29783", "full": "Ley 29783"}],
                "articles": ["39", "40"],
                "chapters": ["5"],
                "sections": ["5.2"],
                "keywords": ["capacitacion", "empleador"],
                "has_norm_reference": True,
                "has_article_reference": True
            }
        """
        result = {
            "norms": [],
            "articles": [],
            "chapters": [],
            "sections": [],
            "keywords": [],
            "has_norm_reference": False,
            "has_article_reference": False,
            "has_chapter_reference": False
        }
        
        # Extract norms
        if self.config["extract_norms"]:
            result["norms"] = self._extract_norms(query)
            result["has_norm_reference"] = len(result["norms"]) > 0
        
        # Extract articles
        if self.config["extract_articles"]:
            result["articles"] = self._extract_articles(query)
            result["has_article_reference"] = len(result["articles"]) > 0
        
        # Extract chapters
        if self.config["extract_chapters"]:
            result["chapters"] = self._extract_chapters(query)
            result["has_chapter_reference"] = len(result["chapters"]) > 0
        
        # Extract sections
        if self.config["extract_sections"]:
            result["sections"] = self._extract_sections(query)
        
        # Extract keywords
        result["keywords"] = self._extract_keywords(query)
        
        return result
    
    def _extract_norms(self, query: str) -> List[Dict]:
        """Extract norm references from query."""
        norms = []
        
        for norm_type, pattern in self.norm_patterns_compiled.items():
            matches = pattern.finditer(query)
            for match in matches:
                norm_code = match.group(1)
                full_match = match.group(0)
                
                norms.append({
                    "type": norm_type,
                    "code": norm_code,
                    "full": full_match.strip()
                })
        
        return norms
    
    def _extract_articles(self, query: str) -> List[str]:
        """Extract article numbers from query."""
        articles = []
        matches = self.article_pattern.finditer(query)
        
        for match in matches:
            article_num = match.group(1)
            articles.append(article_num)
        
        return articles
    
    def _extract_chapters(self, query: str) -> List[str]:
        """Extract chapter numbers from query."""
        chapters = []
        matches = self.chapter_pattern.finditer(query)
        
        for match in matches:
            chapter_num = match.group(1)
            chapters.append(chapter_num)
        
        return chapters
    
    def _extract_sections(self, query: str) -> List[str]:
        """Extract section numbers from query."""
        sections = []
        matches = self.section_pattern.finditer(query)
        
        for match in matches:
            section_num = match.group(1)
            sections.append(section_num)
        
        return sections
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query (removing stopwords).
        
        Args:
            query: User query
        
        Returns:
            List of keywords (lowercased, no stopwords)
        """
        # Normalize query
        query_lower = query.lower()
        
        # Remove punctuation
        query_clean = re.sub(r'[^\w\s]', ' ', query_lower)
        
        # Split into words
        words = query_clean.split()
        
        # Filter stopwords and short words
        keywords = [
            word for word in words
            if word not in self.stopwords and len(word) > 2
        ]
        
        return keywords
    
    def get_primary_norm(self, parsed: Dict) -> Optional[Dict]:
        """
        Get the primary (first) norm mentioned in query.
        
        Args:
            parsed: Parsed query result
        
        Returns:
            Primary norm dict or None
        """
        if parsed["norms"]:
            return parsed["norms"][0]
        return None
    
    def get_primary_article(self, parsed: Dict) -> Optional[str]:
        """Get the primary (first) article mentioned in query."""
        if parsed["articles"]:
            return parsed["articles"][0]
        return None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_parser_instance = None

def get_query_parser() -> QueryParser:
    """Get or create global query parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = QueryParser()
    return _parser_instance


def parse_query(query: str) -> Dict:
    """
    Convenience function to parse a query.
    
    Args:
        query: User query string
    
    Returns:
        Parsed entities dict
    """
    parser = get_query_parser()
    return parser.parse(query)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test cases
    test_queries = [
        "¿Qué dice el artículo 39 de la Ley 29783?",
        "¿Cuál es el plazo en el DS 005-2012-TR?",
        "¿Qué dice NFPA 11 sobre espumas?",
        "Capítulo 5 de la Ley 29783",
        "Sección 5.2 del artículo 39"
    ]
    
    parser = QueryParser()
    
    print("="*70)
    print("QUERY PARSER - TEST")
    print("="*70)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = parser.parse(query)
        
        print(f"   Norms: {result['norms']}")
        print(f"   Articles: {result['articles']}")
        print(f"   Chapters: {result['chapters']}")
        print(f"   Keywords: {result['keywords']}")
        print(f"   Has norm ref: {result['has_norm_reference']}")