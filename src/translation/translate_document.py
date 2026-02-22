"""
Document Translation Module - For KB Preparation (RNE Optimized)

Translates full markdown documents ES→EN for ingestion into English KB.
Optimized for RNE (Reglamento Nacional de Edificaciones) documents that combine:
- Legal articles and regulatory provisions
- Technical specifications and standards
- Material specifications (ASTM, ISO, etc.)
- Technical glossaries

Usage:
    from translation.translate_document import DocumentTranslator
    
    translator = DocumentTranslator()
    translated_text = translator.translate_file("input.md", "output.md")
"""

import os
import re
import time
import signal
from typing import List, Tuple
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()


class DocumentTranslator:
    """
    Translator optimized for RNE documents (hybrid legal/technical/normative).
    
    Features:
    - Intelligent splitting by markdown sections
    - Progress tracking with timeout protection
    - Automatic retries with exponential backoff
    - Cost estimation
    - Preserves markdown formatting
    - Specialized prompt for RNE documents
    """
    
    def __init__(
        self, 
        mistral_api_key: str = None,
        max_chunk_chars: int = 6000,  # Conservative limit for safety
        max_retries: int = 3,
        timeout_seconds: int = 60  # Timeout for API calls
    ):
        """
        Initialize document translator.
        
        Args:
            mistral_api_key: Mistral API key (uses env var if not provided)
            max_chunk_chars: Maximum characters per API call (default: 6000)
            max_retries: Maximum retry attempts per chunk (default: 3)
            timeout_seconds: Timeout for API calls in seconds (default: 60)
        """
        self.mistral_api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
        self.timeout_seconds = timeout_seconds
        
        if not self.mistral_api_key:
            raise ValueError("Mistral API key required. Set MISTRAL_API_KEY in .env or pass as argument.")
        
        self.mistral_client = Mistral(api_key=self.mistral_api_key)
        self.max_chunk_chars = max_chunk_chars
        self.max_retries = max_retries
        
        # Statistics
        self.total_chars_translated = 0
        self.api_calls_made = 0
        self.failed_chunks = []
        
        print(f"📄 Document Translator initialized (RNE-optimized)")
        print(f"   Max chunk size: {self.max_chunk_chars} chars")
        print(f"   Max retries: {self.max_retries}")
        print(f"   Timeout: {self.timeout_seconds} seconds")
    
    def _timeout_handler(self, signum, frame):
        """Handle timeout for API calls."""
        raise TimeoutError("API call timed out")
    
    def _make_api_call_with_timeout(self, prompt: str) -> str:
        """Make API call with timeout protection."""
        # Set up timeout signal
        old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.timeout_seconds)
        
        try:
            response = self.mistral_client.chat.complete(
                model="mistral-small-latest",
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            return str(response.choices[0].message.content).strip()
        finally:
            # Cancel timeout and restore old handler
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    def get_rne_specialized_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Generate specialized prompt for RNE (Reglamento Nacional de Edificaciones) documents.
        
        Covers all hybrid document types:
        - Legal-Normative (articles, decrees)
        - Technical-Referential (ASTM, ISO standards)
        - Technical-Normative (specifications + requirements)
        - Technical Glossaries (specialized definitions)
        - Legal-Urban Planning (zoning, land development)
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
        
        Returns:
            Specialized prompt string
        """
        lang_names = {"es": "Spanish", "en": "English"}
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        prompt = f"""You are a specialized translator for the Peruvian National Building Code (RNE - Reglamento Nacional de Edificaciones).

TASK: Translate the following {source_name} RNE document to {target_name}.

DOCUMENT TYPE: Building code combining legal articles, technical specifications, material standards, and technical glossaries.

═══════════════════════════════════════════════════════════════════════════════
CRITICAL TRANSLATION RULES FOR RNE DOCUMENTS:
═══════════════════════════════════════════════════════════════════════════════

1. PRESERVE MARKDOWN FORMATTING:
   ✓ Keep ALL headers (# ## ###) exactly as they are
   ✓ Preserve tables, bullet points, and numbered lists
   ✓ Maintain line breaks and page markers (--- Page X ---)
   ✓ Keep mathematical expressions and formulas unchanged ($...$)
   ✓ Preserve special characters and symbols

2. LEGAL/REGULATORY TERMINOLOGY:
   
   Spanish → English (Legal):
   - Artículo N° → Article No.
   - Decreto Supremo → Supreme Decree
   - Norma Técnica → Technical Standard / Technical Code
   - Reglamento Nacional de Edificaciones (RNE) → National Building Code (RNE)
   - Habilitación Urbana → Urban Development / Land Subdivision
   - Zonificación → Zoning
   - Aporte → Contribution / Dedication (for land/facilities)
   - De conformidad con → In accordance with
   - Se prohíbe → It is prohibited / Shall not
   - Deberá cumplir → Shall comply / Must comply
   - Podrá → May / Shall be permitted to
   - Está obligado → Is required / Shall
   - CONSIDERANDO: → WHEREAS: / CONSIDERING:
   - SE RESUELVE: → IT IS RESOLVED: / IT IS HEREBY RESOLVED:

3. TECHNICAL STANDARDS & REFERENCES:
   
   PRESERVE EXACTLY (do NOT translate):
   - ASTM (American Society for Testing and Materials)
   - ISO (International Organization for Standardization)
   - UNE (Una Norma Española)
   - DIN (Deutsches Institut für Normung)
   - NFPA (National Fire Protection Association)
   - MPa, psi, kg/cm², N/mm² (units)
   
   Standard format preservation:
   - ASTM A325 → ASTM A325 (unchanged)
   - Norma UNE 102-801-93 → UNE 102-801-93 Standard
   - ISO 9001:2015 → ISO 9001:2015 (unchanged)
   - NFPA 72 → NFPA 72 (unchanged)

4. CONSTRUCTION/ENGINEERING TERMINOLOGY:
   
   MATERIALS & STRUCTURAL:
   - Concreto armado → Reinforced concrete
   - Acero estructural → Structural steel
   - Acero de alta resistencia → High-strength steel
   - Fundiciones de acero → Steel castings
   - Piezas forjadas → Forged pieces / Forgings
   - Pernos → Bolts
   - Tuercas → Nuts
   - Arandelas → Washers
   - Pernos de cortante → Shear bolts
   - Resistencia a la tracción → Tensile strength
   - Resistencia mínima → Minimum strength
   
   WOOD/TIMBER (Carpentry):
   - Madera → Timber / Wood / Lumber (context-dependent)
   - Escuadría → Cross-section dimensions / Scantling
   - Madera aserrada → Sawn timber / Lumber
   - Madera rolliza → Round timber / Log
   - Madera labrada → Hewn timber / Dressed timber
   - Madera tratada → Treated timber
   - Madera preservada → Preservative-treated timber
   - Grano → Grain (wood grain pattern)
   - Contenido de humedad → Moisture content
   - Habilitar → Dress to size / Mill to dimensions
   - Labrar → Dress / Mill / Hew
   - Espiga → Tenon
   - Ranura → Groove / Mortise
   - Machihembrar → Tongue-and-groove joint
   
   STRUCTURAL ELEMENTS:
   - Entrepiso → Floor assembly / Inter-floor structure
   - Viga → Beam
   - Columna → Column
   - Cimentación → Foundation
   - Losa → Slab
   - Muro portante → Load-bearing wall
   - Lima (techo) → Hip rafter (saliente) / Valley rafter (entrante)
   - Lima tesa → Hip rafter
   - Lima hoya → Valley rafter
   
   MECHANICAL/INSTALLATIONS:
   - Conducto → Duct / Conduit
   - Conducto colectivo → Collective duct / Common duct
   - Tiro natural → Natural draft
   - Sobresucción → Over-suction / Excessive suction
   - Calentador instantáneo → Tankless water heater / Instantaneous heater
   - Calentador de acumulación → Storage water heater
   - Extractor de aire → Air extractor / Exhaust fan
   - Evacuación de gases → Gas exhaust / Flue gas evacuation
   - Producto de la combustión → Combustion products / Products of combustion
   - Celosía → Grille / Louver

5. MEASUREMENTS & SPECIFICATIONS:
   
   Keep EXACTLY as written:
   - Dimensions: 20 × 10 cm → 20 × 10 cm (unchanged)
   - Percentages: 1% → 1% (unchanged)
   - Pressures: 414 MPa → 414 MPa (unchanged)
   - Temperatures: 20°C → 20°C (unchanged)
   - Formulas: $20 \\times 10$ → $20 \\times 10$ (unchanged LaTeX)
   
   Context translation:
   - "de resistencia a la tracción 414 MPa" → "with tensile strength of 414 MPa"
   - "resistencia mínima a la tracción 830/725 MPa" → "minimum tensile strength 830/725 MPa"
   - "perforación de 20 × 10 cm como mínimo" → "opening of minimum 20 × 10 cm"

6. LEGAL REQUIREMENTS PHRASING (CRITICAL FOR CODE COMPLIANCE):
   
   Modal verbs for regulatory language:
   - "deberá" / "deberán" → "shall" (mandatory requirement)
   - "podrá" / "podrán" → "may" / "shall be permitted to" (optional/allowed)
   - "se prohíbe" / "se prohíben" → "it is prohibited" / "shall not" (forbidden)
   - "es obligatorio" → "it is mandatory" / "shall" (required)
   - "se permite" → "it is permitted" / "may" (allowed)
   - "está permitido" → "is permitted" / "is allowed"
   
   Examples:
   - "Los conductos colectivos deberán tener..." 
     → "Collective ducts shall have..."
   - "Se prohíbe instalar calentadores..."
     → "It is prohibited to install water heaters..." / "Installation of water heaters is prohibited..."
   - "Podrá llevarse a cabo..."
     → "May be carried out..." / "Shall be permitted to be carried out..."

7. TECHNICAL DEFINITIONS FORMAT (For Glossaries):
   
   Preserve definition structure:
   - "Es el conjunto de..." → "The assembly of..." / "The set of..."
   - "Es la operación que consiste en..." → "The operation consisting of..." / "The process of..."
   - "Es aquella..." → "That which..." / "Timber/Material that..."
   - "Acción y efecto de..." → "Action and effect of..." / "The act and result of..."
   
   Examples:
   - "Es el aumento de las dimensiones de una pieza..."
     → "The increase in dimensions of a timber piece..."
   - "Es la operación realizada en la madera para reducirla..."
     → "The operation performed on timber to reduce it..."

8. ARTICLE & SECTION STRUCTURE:
   
   Preserve legal/technical numbering exactly:
   - "Artículo 1.-" → "Article 1.-"
   - "Artículo 31.-" → "Article 31.-"
   - "1.3.1.1." → "1.3.1.1." (unchanged)
   - "4.3.3.1." → "4.3.3.1." (unchanged)
   - "a), b), c)" → "a), b), c)" (unchanged)
   - "(1), (2), (3)" → "(1), (2), (3)" (unchanged)

9. CAPITALIZATION:
   
   Maintain appropriate capitalization:
   - "CAPÍTULO I" → "CHAPTER I"
   - "GENERALIDADES" → "GENERAL PROVISIONS" / "GENERAL"
   - "REQUISITOS GENERALES" → "GENERAL REQUIREMENTS"
   - "NORMAS LEGALES" → "LEGAL STANDARDS" / "REGULATORY PROVISIONS"

10. CONTEXTUAL ACCURACY:
    
    Use appropriate technical terms based on context:
    - Building/Construction context: Use "structure", "building", "construction"
    - Materials context: Use specific material terms
    - Installation context: Use "installation", "system", "equipment"
    - Regulatory context: Use formal legal language

═══════════════════════════════════════════════════════════════════════════════

Text to translate:
{text}

Technical translation (RNE Building Code):"""

        return prompt
    
    def translate_chunk(
        self, 
        text: str, 
        source_lang: str = "es", 
        target_lang: str = "en",
        retry_count: int = 0
    ) -> str:
        """
        Translate a single chunk of text using RNE-specialized prompt.
        
        Args:
            text: Text chunk to translate
            source_lang: Source language code
            target_lang: Target language code
            retry_count: Current retry attempt
        
        Returns:
            Translated text
        """
        # Generate RNE-specialized prompt
        prompt = self.get_rne_specialized_prompt(text, source_lang, target_lang)

        try:
            translated = self._make_api_call_with_timeout(prompt)
            self.api_calls_made += 1
            self.total_chars_translated += len(text)
            
            return translated
            
        except TimeoutError as e:
            print(f"⏰ Translation timed out (attempt {retry_count + 1}/{self.max_retries})")
            
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                print(f"🔄 Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self.translate_chunk(text, source_lang, target_lang, retry_count + 1)
            else:
                print(f"⚠️ Max retries reached due to timeouts, keeping original text")
                self.failed_chunks.append(text[:100])
                return text
                
        except Exception as e:
            print(f"❌ Translation failed (attempt {retry_count + 1}/{self.max_retries}): {e}")
            
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"🔄 Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self.translate_chunk(text, source_lang, target_lang, retry_count + 1)
            else:
                print(f"⚠️ Max retries reached, keeping original text")
                self.failed_chunks.append(text[:100])
                return text
    
    def split_document_intelligently(self, text: str) -> List[str]:
        """
        Split document into chunks respecting markdown structure and page markers.
        
        Strategy:
        1. Split by top-level headers (# or ##) and page markers
        2. If section > max_chunk_chars, split by sub-headers (###)
        3. If still too large, split by paragraphs
        4. Preserve section headers with their content
        
        Args:
            text: Full document text
        
        Returns:
            List of text chunks
        """
        chunks = []
        
        # Split by major headers (# or ##) and page markers
        # Preserve both headers and page markers
        sections = re.split(r'(^#{1,2}\s+.+$|^---\s+Page\s+\d+\s+---$)', text, flags=re.MULTILINE)
        
        current_chunk = ""
        current_header = ""
        
        for i, section in enumerate(sections):
            # Check if this is a header or page marker
            if re.match(r'^#{1,2}\s+.+$', section) or re.match(r'^---\s+Page\s+\d+\s+---$', section):
                current_header = section
                continue
            
            # This is content under a header
            if section.strip():
                # Combine header with content
                section_with_header = f"{current_header}\n\n{section}" if current_header else section
                
                # If section is small enough, add to current chunk
                if len(current_chunk) + len(section_with_header) < self.max_chunk_chars:
                    current_chunk += "\n\n" + section_with_header if current_chunk else section_with_header
                else:
                    # Save current chunk if not empty
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    # Start new chunk with this section
                    # If section itself is too large, split it further
                    if len(section_with_header) > self.max_chunk_chars:
                        sub_chunks = self._split_large_section(section_with_header)
                        chunks.extend(sub_chunks)
                        current_chunk = ""
                    else:
                        current_chunk = section_with_header
                
                current_header = ""  # Reset header after using it
        
        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_large_section(self, text: str) -> List[str]:
        """
        Split a large section by paragraphs.
        
        Args:
            text: Large section text
        
        Returns:
            List of smaller chunks
        """
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < self.max_chunk_chars:
                current_chunk += "\n\n" + para if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def translate_document(
        self, 
        text: str, 
        source_lang: str = "es", 
        target_lang: str = "en",
        show_progress: bool = True
    ) -> str:
        """
        Translate a full document with progress tracking.
        
        Args:
            text: Full document text
            source_lang: Source language code
            target_lang: Target language code
            show_progress: Show progress bar and statistics
        
        Returns:
            Fully translated document
        """
        # Reset statistics
        self.total_chars_translated = 0
        self.api_calls_made = 0
        self.failed_chunks = []
        
        print(f"\n{'='*60}")
        print(f"📄 DOCUMENT TRANSLATION START")
        print(f"{'='*60}")
        print(f"Document size: {len(text):,} characters")
        print(f"Language: {source_lang} → {target_lang}")
        print(f"Document type: RNE (National Building Code)")
        
        # Skip if same language
        if source_lang == target_lang:
            print(f"⚠️ Same language, skipping translation")
            return text
        
        # Split document
        print(f"\n🔪 Splitting document intelligently...")
        chunks = self.split_document_intelligently(text)
        
        print(f"✅ Split into {len(chunks)} chunks")
        print(f"📊 Chunk sizes:")
        for i, chunk in enumerate(chunks[:5], 1):  # Show first 5
            print(f"   Chunk {i}: {len(chunk):,} chars")
        if len(chunks) > 5:
            print(f"   ... and {len(chunks) - 5} more")
        
        # Estimate cost
        estimated_tokens = sum(len(chunk) // 4 for chunk in chunks)  # Rough estimate
        estimated_cost = (estimated_tokens / 1_000_000) * 0.25  # Mistral pricing
        print(f"\n💰 Estimated cost: ${estimated_cost:.4f} USD")
        
        # Translate each chunk
        print(f"\n🔄 Starting translation...")
        print(f"{'─'*60}")
        
        translated_chunks = []
        
        for i, chunk in enumerate(chunks, 1):
            if show_progress:
                progress_pct = (i / len(chunks)) * 100
                print(f"[{i}/{len(chunks)}] ({progress_pct:.1f}%) Translating chunk ({len(chunk):,} chars)...", end=" ")
            
            translated = self.translate_chunk(chunk, source_lang, target_lang)
            translated_chunks.append(translated)
            
            if show_progress:
                print(f"✅")
        
        # Reassemble
        print(f"{'─'*60}")
        print(f"🔧 Reassembling document...")
        
        translated_document = "\n\n".join(translated_chunks)
        
        # Statistics
        print(f"\n{'='*60}")
        print(f"✅ TRANSLATION COMPLETE")
        print(f"{'='*60}")
        print(f"📊 Statistics:")
        print(f"   Chunks translated: {len(chunks)}")
        print(f"   API calls made: {self.api_calls_made}")
        print(f"   Total chars translated: {self.total_chars_translated:,}")
        print(f"   Output size: {len(translated_document):,} chars")
        
        if self.failed_chunks:
            print(f"\n⚠️ Warning: {len(self.failed_chunks)} chunk(s) failed translation")
            print(f"   (Original text kept for failed chunks)")
        
        print(f"{'='*60}\n")
        
        return translated_document
    
    def translate_file(
        self, 
        input_path: str, 
        output_path: str,
        source_lang: str = "es",
        target_lang: str = "en"
    ) -> bool:
        """
        Translate a markdown file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output file
            source_lang: Source language code
            target_lang: Target language code
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\n📂 Reading: {input_path}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                original_text = f.read()
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return False
        
        # Translate
        translated_text = self.translate_document(original_text, source_lang, target_lang)
        
        # Write output
        print(f"💾 Writing: {output_path}")
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translated_text)
            
            print(f"✅ File saved successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error writing file: {e}")
            return False