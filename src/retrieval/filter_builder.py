"""
Filter Builder - FASE C (CORREGIDO)

Constructs intelligent Qdrant filters based on parsed query entities.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.retrieval_config import FILTER_BUILDER_CONFIG


class FilterBuilder:
    """
    Builds Qdrant filters from parsed query entities.
    
    Features:
    - Code variation generation (Ley 29783, L. 29783, Ley N° 29783)
    - RNE special handling (A.130, E.060, etc.)
    - Thematic area mapping
    - Flexible OR filters (should) vs strict AND filters (must)
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize filter builder.
        
        Args:
            config: Builder configuration (defaults to FILTER_BUILDER_CONFIG)
        """
        self.config = config or FILTER_BUILDER_CONFIG
    
    def build_filters(self, parsed_query: Dict) -> Optional[Filter]:
        """
        Build Qdrant filter from parsed query.
        
        Args:
            parsed_query: Output from QueryParser.parse()
        
        Returns:
            Qdrant Filter object or None if no filters needed
        """
        should_conditions = []
        must_conditions = []
        
        # Filter by norm codes (if mentioned)
        if parsed_query.get("has_norm_reference") and parsed_query["norms"]:
            norm_conditions = self._build_norm_filters(parsed_query["norms"])
            should_conditions.extend(norm_conditions)
        
        # Filter by article (if mentioned)
        if parsed_query.get("has_article_reference") and parsed_query["articles"]:
            article_conditions = self._build_article_filters(parsed_query["articles"])
            should_conditions.extend(article_conditions)
        
        # Filter by chapter (if mentioned)
        if parsed_query.get("has_chapter_reference") and parsed_query["chapters"]:
            chapter_conditions = self._build_chapter_filters(parsed_query["chapters"])
            should_conditions.extend(chapter_conditions)
        
        # Filter by thematic area (from keywords)
        if parsed_query.get("keywords"):
            thematic_conditions = self._build_thematic_filters(parsed_query["keywords"])
            if thematic_conditions:
                should_conditions.extend(thematic_conditions)
        
        # Build final filter
        if not should_conditions and not must_conditions:
            return None
        
        filter_dict = {}
        
        if self.config["use_should_filters"] and should_conditions:
            filter_dict["should"] = should_conditions
        
        if self.config["use_must_filters"] and must_conditions:
            filter_dict["must"] = must_conditions
        
        if filter_dict:
            return Filter(**filter_dict)
        
        return None
    
    def _build_norm_filters(self, norms: List[Dict]) -> List[FieldCondition]:
        """
        Build filters for norm references.
        
        ✨ MEJORADO: Genera más variaciones y hace filtros más flexibles
        
        Args:
            norms: List of norm dicts from parser
        
        Returns:
            List of FieldCondition objects
        """
        conditions = []
        
        for norm in norms:
            norm_type = norm["type"]
            norm_code = norm["code"]
            norm_full = norm.get("full", f"{norm_type} {norm_code}")
            
            # ✨ NUEVO: Map RNE subtypes to generic "rne" for variations
            variation_type = norm_type
            norm_code_full = norm_code
            
            if norm_type.startswith("rne_"):
                variation_type = "rne"
                # Reconstruct full code (ej: "A.130" de code "130")
                prefix = norm_type.replace("rne_", "").upper()
                norm_code_full = f"{prefix}.{norm_code}"
            
            # Generate code variations from configuration
            if self.config["generate_code_variations"]:
                variations = self._generate_code_variations(variation_type, norm_code_full)
            else:
                variations = [norm_full]
            
            # ✨ MEJORADO: Agregar variaciones adicionales comunes para TODAS las normas
            # Esto asegura que todas las normas tengan las mismas variaciones básicas
            # (ya incluidas en la configuración, pero agregamos el código original completo)
            variations.append(norm_full)  # Asegurar que el código original completo esté incluido
            
            # Remover duplicados
            variations = list(set(variations))
            
            # Create filter for code field (matches any variation)
            conditions.append(
                FieldCondition(
                    key="code",
                    match=MatchAny(any=variations)
                )
            )
            
            # Also check in code_variations field if it exists
            conditions.append(
                FieldCondition(
                    key="code_variations",
                    match=MatchAny(any=variations)
                )
            )
        
        return conditions
    
    def _build_article_filters(self, articles: List[str]) -> List[FieldCondition]:
        """Build filters for article references."""
        conditions = []
        
        # Match article field
        conditions.append(
            FieldCondition(
                key="article",
                match=MatchAny(any=articles)
            )
        )
        
        return conditions
    
    def _build_chapter_filters(self, chapters: List[str]) -> List[FieldCondition]:
        """Build filters for chapter references."""
        conditions = []
        
        # Match chapter field
        conditions.append(
            FieldCondition(
                key="chapter",
                match=MatchAny(any=chapters)
            )
        )
        
        return conditions
    
    def _build_thematic_filters(self, keywords: List[str]) -> List[FieldCondition]:
        """Build filters for thematic area based on keywords."""
        conditions = []
        thematic_mapping = self.config.get("thematic_mapping", {})
        
        matched_areas = set()
        
        # Map keywords to thematic areas
        for keyword in keywords:
            if keyword in thematic_mapping:
                matched_areas.add(thematic_mapping[keyword])
        
        if matched_areas:
            conditions.append(
                FieldCondition(
                    key="thematic_area",
                    match=MatchAny(any=list(matched_areas))
                )
            )
        
        return conditions
    
    def _generate_code_variations(self, norm_type: str, code: str) -> List[str]:
        """
        Generate variations of a norm code.
        
        ✨ MEJORADO: Handles complex codes (ISO 9001-2015, NTP 350.026)
        
        Args:
            norm_type: Type of norm (ley, decreto, rne, etc.)
            code: Norm code
        
        Returns:
            List of code variations
        """
        patterns = self.config.get("code_variation_patterns", {})
        type_patterns = patterns.get(norm_type, ["{num}"])
        
        variations = []
        
        # ✨ NUEVO: Parse code components
        code_parts = self._parse_code_components(code)
        
        for pattern in type_patterns:
            # Replace placeholders
            variation = pattern
            for key, value in code_parts.items():
                placeholder = "{" + key + "}"
                if placeholder in variation and value:
                    variation = variation.replace(placeholder, value)
            
            # Only add if all placeholders were replaced
            if "{" not in variation:
                variations.append(variation)
        
        # Add original code
        variations.append(code)
        
        # Remove duplicates
        return list(set(variations))
    
    def _parse_code_components(self, code: str) -> Dict[str, str]:
        """
        Parse code into components (num, year, subnum, etc.).
        
        Examples:
            "9001-2015" → {"num": "9001", "year": "2015"}
            "350.026" → {"num": "350", "subnum": "026"}
            "005-2012-TR" → {"num": "005-2012-TR"}
            "A.130" → {"num": "A.130"}
        """
        components = {}
        
        # Check for ISO format (9001-2015)
        if "-" in code:
            parts = code.split("-")
            # If last part is 4-digit year
            if len(parts[-1]) == 4 and parts[-1].isdigit():
                components["num"] = "-".join(parts[:-1])
                components["year"] = parts[-1]
            else:
                # Complex code like 005-2012-TR
                components["num"] = code
        
        # Check for NTP format (350.026)
        elif "." in code and not code.startswith(("A.", "E.", "G.", "IS.", "TH.", "EM.", "OS.", "CE.", "EC.", "GE.", "GH.")):
            parts = code.split(".")
            components["num"] = parts[0]
            components["subnum"] = parts[1] if len(parts) > 1 else ""
        
        # Default: everything is num
        else:
            components["num"] = code
        
        return components


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_builder_instance = None

def get_filter_builder() -> FilterBuilder:
    """Get or create global filter builder instance."""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = FilterBuilder()
    return _builder_instance


def build_filters(parsed_query: Dict) -> Optional[Filter]:
    """Convenience function to build filters."""
    builder = get_filter_builder()
    return builder.build_filters(parsed_query)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from query_parser import parse_query
    
    test_queries = [
        "¿Qué dice el artículo 39 de la Ley 29783?",
        "¿Cuál es el plazo en el DS 005-2012-TR?",
        "¿Qué dice NFPA 11 sobre seguridad en incendios?",
    ]
    
    builder = FilterBuilder()
    
    print("="*70)
    print("FILTER BUILDER - TEST")
    print("="*70)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        parsed = parse_query(query)
        filters = builder.build_filters(parsed)
        
        if filters:
            print(f"   ✅ Filters created:")
            if hasattr(filters, 'should') and filters.should:
                print(f"      Should conditions: {len(filters.should)}")
            if hasattr(filters, 'must') and filters.must:
                print(f"      Must conditions: {len(filters.must)}")
        else:
            print(f"   ℹ️  No filters needed")