"""
Context Composer - FASE C

Formats retrieved chunks into structured context for LLM.
"""

import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.retrieval_config import CONTEXT_COMPOSER_CONFIG


class ContextComposer:
    """
    Composes context from ranked chunks with intelligent formatting.
    
    Features:
    - Structured citations with metadata
    - Grouping by document
    - Deduplication of similar content
    - Length control
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize context composer.
        
        Args:
            config: Composer configuration
        """
        self.config = config or CONTEXT_COMPOSER_CONFIG
        
        self.max_chunks = self.config.get("max_chunks", 10)
        self.max_context_length = self.config.get("max_context_length", 8000)
        self.include_metadata = self.config.get("include_metadata", True)
        self.group_by_document = self.config.get("group_by_document", True)
        self.citation_style = self.config.get("citation_style", "structured")
        self.include_relevance_score = self.config.get("include_relevance_score", True)
        self.deduplicate_content = self.config.get("deduplicate_content", True)
    
    def compose(self, chunks: List[Dict]) -> str:
        """
        Compose formatted context from chunks.
        
        Args:
            chunks: List of ranked chunks (must have 'payload' and 'final_score')
        
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        # Limit chunks
        chunks = chunks[:self.max_chunks]
        
        # Deduplicate if enabled
        if self.deduplicate_content:
            chunks = self._deduplicate_chunks(chunks)
        
        # Group by document if enabled
        if self.group_by_document:
            context = self._compose_grouped(chunks)
        else:
            context = self._compose_flat(chunks)
        
        # Truncate if too long
        if len(context) > self.max_context_length:
            context = context[:self.max_context_length] + "\n\n[Context truncated due to length...]"
        
        return context
    
    def _compose_grouped(self, chunks: List[Dict]) -> str:
        """Compose context grouped by document."""
        # Group chunks by document_id
        grouped = {}
        
        for chunk in chunks:
            metadata = self._get_metadata(chunk)
            doc_id = metadata.get('document_id', 'Unknown')
            
            if doc_id not in grouped:
                grouped[doc_id] = {
                    'metadata': metadata,
                    'chunks': []
                }
            
            grouped[doc_id]['chunks'].append(chunk)
        
        # Format each document group
        formatted_sections = []
        
        for doc_id, group in grouped.items():
            doc_metadata = group['metadata']
            doc_chunks = group['chunks']
            
            # Document header
            doc_header = self._format_document_header(doc_metadata)
            
            # Format chunks
            chunk_texts = []
            for i, chunk in enumerate(doc_chunks, 1):
                chunk_text = self._format_chunk(chunk, index=i)
                chunk_texts.append(chunk_text)
            
            # Combine
            section = f"{doc_header}\n\n" + "\n\n".join(chunk_texts)
            formatted_sections.append(section)
        
        # Join all sections
        context = "\n\n" + "="*70 + "\n\n"
        context = context.join(formatted_sections)
        
        return context
    
    def _compose_flat(self, chunks: List[Dict]) -> str:
        """Compose context without grouping."""
        formatted_chunks = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_text = self._format_chunk(chunk, index=i)
            formatted_chunks.append(chunk_text)
        
        return "\n\n---\n\n".join(formatted_chunks)
    
    def _format_document_header(self, metadata: Dict) -> str:
        """Format document header with metadata."""
        # Extract key fields
        code = metadata.get('code', 'Unknown')
        full_name = metadata.get('full_name', 'Unknown Document')
        edition = metadata.get('edition', '')
        
        # Build header
        header = f"📄 **{code}"
        if edition:
            header += f":{edition}"
        header += f"** - {full_name}"
        
        # Add legal weight indicator
        if self.include_metadata:
            jerarquia = metadata.get('jerarquia_normativa', None)
            if jerarquia:
                hierarchy_labels = {
                    1: "Constitución",
                    2: "Ley Orgánica",
                    3: "Ley Ordinaria",
                    4: "Decreto Supremo",
                    5: "Resolución",
                    6: "Directiva",
                    7: "Norma Técnica Internacional",
                    8: "Norma Técnica Nacional",
                    9: "Otros"
                }
                label = hierarchy_labels.get(jerarquia, f"Nivel {jerarquia}")
                header += f" _{label}_"
        
        return header
    
    def _format_chunk(self, chunk: Dict, index: int = 1) -> str:
        """Format individual chunk."""
        metadata = self._get_metadata(chunk)
        text = metadata.get('text', '[No content]')
        
        if self.citation_style == "structured":
            return self._format_chunk_structured(chunk, metadata, text, index)
        else:
            return self._format_chunk_simple(chunk, metadata, text, index)
    
    def _format_chunk_structured(
        self, 
        chunk: Dict, 
        metadata: Dict, 
        text: str, 
        index: int
    ) -> str:
        """Format chunk with structured citation."""
        # Build citation
        citation = self._build_citation(metadata)
        
        # Build relevance indicator
        relevance = ""
        if self.include_relevance_score:
            final_score = chunk.get('final_score', 0.0)
            relevance = f", Relevance: {final_score:.2f}"
        
        # Format
        formatted = f"[Source {index}: {citation}{relevance}]\n{text}"
        
        return formatted
    
    def _format_chunk_simple(
        self, 
        chunk: Dict, 
        metadata: Dict, 
        text: str, 
        index: int
    ) -> str:
        """Format chunk with simple citation."""
        code = metadata.get('code', 'Unknown')
        formatted = f"**[{code}]**\n{text}"
        return formatted
    
    def _build_citation(self, metadata: Dict) -> str:
        """
        Build citation string from metadata.
        
        Priority:
        1. citation_format (if exists)
        2. full_reference (if exists)
        3. Constructed from code + article
        """
        # Try citation_format first
        citation_format = metadata.get('citation_format', '')
        if citation_format:
            return citation_format
        
        # Try full_reference
        full_reference = metadata.get('full_reference', '')
        if full_reference:
            return full_reference
        
        # Construct from pieces
        code = metadata.get('code', 'Unknown')
        edition = metadata.get('edition', '')
        article = metadata.get('article', '')
        section = metadata.get('section', '')
        chapter = metadata.get('chapter', '')
        
        citation = code
        if edition:
            citation += f":{edition}"
        
        # Add structure
        parts = []
        if chapter:
            parts.append(f"Ch. {chapter}")
        if section:
            parts.append(f"Sec. {section}")
        if article:
            parts.append(f"Art. {article}")
        
        if parts:
            citation += ", " + ", ".join(parts)
        
        return citation
    
    def _deduplicate_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Remove chunks with very similar content.
        
        Uses simple heuristic: if text similarity > threshold, keep highest scored.
        """
        if len(chunks) <= 1:
            return chunks
        
        unique_chunks = []
        seen_texts = []
        
        for chunk in chunks:
            metadata = self._get_metadata(chunk)
            text = metadata.get('text', '')
            
            # Check similarity with seen texts
            is_duplicate = False
            for seen_text in seen_texts:
                if self._text_similarity(text, seen_text) > 0.90:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
                seen_texts.append(text)
        
        return unique_chunks
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity (Jaccard on words).
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score (0.0 - 1.0)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _get_metadata(self, chunk: Dict) -> Dict:
        """Extract metadata from chunk (handles both dict and Qdrant result)."""
        if hasattr(chunk, 'payload'):
            return chunk.payload
        elif 'payload' in chunk:
            return chunk['payload']
        else:
            return chunk


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_composer_instance = None

def get_context_composer() -> ContextComposer:
    """Get or create global context composer instance."""
    global _composer_instance
    if _composer_instance is None:
        _composer_instance = ContextComposer()
    return _composer_instance


def compose_context(chunks: List[Dict]) -> str:
    """
    Convenience function to compose context.
    
    Args:
        chunks: List of ranked chunks
    
    Returns:
        Formatted context string
    """
    composer = get_context_composer()
    return composer.compose(chunks)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Mock chunks for testing
    mock_chunks = [
        {
            'payload': {
                'document_id': 'LEY_29783_2011',
                'code': 'Ley 29783',
                'full_name': 'Ley de Seguridad y Salud en el Trabajo',
                'edition': '2011',
                'article': '39',
                'text': 'Artículo 39.- El empleador debe garantizar capacitación...',
                'citation_format': 'Ley 29783:2011, Art. 39',
                'jerarquia_normativa': 2
            },
            'final_score': 0.95
        },
        {
            'payload': {
                'document_id': 'DS_005-2012-TR',
                'code': 'DS 005-2012-TR',
                'full_name': 'Reglamento de la Ley 29783',
                'edition': '2012',
                'article': '15',
                'text': 'Artículo 15.- Reglamentando el artículo 39...',
                'citation_format': 'DS 005-2012-TR, Art. 15',
                'jerarquia_normativa': 4
            },
            'final_score': 0.78
        }
    ]
    
    composer = ContextComposer()
    context = composer.compose(mock_chunks)
    
    print("="*70)
    print("CONTEXT COMPOSER - TEST")
    print("="*70)
    print(context)