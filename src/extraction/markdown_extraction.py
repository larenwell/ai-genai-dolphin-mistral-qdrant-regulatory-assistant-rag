"""
Mistral Markdown Extraction Controller
Extrae contenido de PDFs y DOCX, convirtiéndolos a Markdown con metadata normalizada

NO hace ingesta a base de datos - solo genera archivos markdown
"""

import os
import re
import base64
import json
import time
from mistralai import Mistral
from typing import Dict, List, Optional, Any
from pathlib import Path
import PyPDF2


def print_stage_title(title: str, stage_number: int = None):
    """Print a beautiful stage title with visual separators"""
    if stage_number:
        print(f"\n{'='*80}")
        print(f"🚀 ETAPA {stage_number}: {title}")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"🎯 {title}")
        print(f"{'='*80}")


def print_sub_stage(title: str):
    """Print a sub-stage title"""
    print(f"\n📋 {title}")
    print(f"{'-'*60}")


def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            if hasattr(e, 'status_code') and e.status_code >= 500:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️  Error temporal (intento {attempt + 1}/{max_retries}): {str(e)}")
                print(f"⏳ Reintentando en {delay} segundos...")
                time.sleep(delay)
                continue
            else:
                raise e
    
    return None


class MistralExtractionController:
    """
    Controlador para extracción de contenido usando Mistral AI
    
    Funcionalidades:
    - Extracción de PDFs con Mistral OCR (con chunking para archivos grandes)
    - Conversión de DOCX a Markdown con Mistral Chat
    - Generación de summaries jerárquicos (mini-summaries + summary final)
    - Metadata normalizada para todos los documentos
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.mistral_client = Mistral(api_key=api_key)
    
    def extract_document_title(self, pdf_path: str) -> str:
        """Extrae el título real del documento PDF"""
        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                
                # ESTRATEGIA 1: Metadata del PDF
                if pdf.metadata and pdf.metadata.get('/Title'):
                    title = pdf.metadata['/Title']
                    if title and len(title.strip()) > 0:
                        print(f"   ✅ Título extraído de metadata: {title}")
                        return title.strip()
                
                # ESTRATEGIA 2: Primera página
                first_page = pdf.pages[0].extract_text()
                lines = [line.strip() for line in first_page.split('\n') if line.strip()]
                
                for line in lines[:15]:
                    if (10 < len(line) < 150 and
                        not line.startswith(('Page', 'Página', 'Date', 'Fecha')) and
                        not re.match(r'^\d+$', line) and
                        line[0].isupper()):
                        print(f"   ✅ Título extraído de primera página: {line}")
                        return line
                
                # ESTRATEGIA 3: Fallback
                fallback = Path(pdf_path).stem
                print(f"   ⚠️  Usando nombre de archivo como título: {fallback}")
                return fallback
                
        except Exception as e:
            print(f"   ⚠️  Error extrayendo título: {str(e)}")
            return Path(pdf_path).stem
    
    def detect_language(self, text: str) -> str:
        """Detecta el idioma del texto (español o inglés)"""
        sample = text[:1000].lower()
        
        spanish_keywords = ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'los', 'las', 'del', 
                           'artículo', 'ley', 'decreto', 'considerando']
        english_keywords = ['the', 'of', 'and', 'to', 'a', 'in', 'is', 'that', 'for', 
                           'section', 'standard', 'requirements', 'shall']
        
        spanish_score = sum(1 for word in spanish_keywords if f' {word} ' in sample)
        english_score = sum(1 for word in english_keywords if f' {word} ' in sample)
        
        if spanish_score > english_score:
            return "es"
        elif english_score > spanish_score:
            return "en"
        else:
            return "unknown"
    
    def generate_document_id(self, source_file: str) -> str:
        """Genera un document_id único y consistente"""
        doc_id = Path(source_file).stem
        doc_id = re.sub(r'[^\w\-]', '_', doc_id)
        return doc_id.upper()
        
    def encode_pdf(self, pdf_path: str) -> str:
        """Encode the pdf to base64"""
        try:
            with open(pdf_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    def split_pdf_into_chunks(self, pdf_path: str, pages_per_chunk: int = 20) -> List[Dict]:
        """Divide un PDF grande en chunks para evitar límite de API"""
        try:
            from PyPDF2 import PdfReader, PdfWriter
            import tempfile
            
            print(f"   📄 Leyendo PDF original...")
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            
            print(f"   📊 Total páginas: {total_pages}")
            print(f"   ✂️  Dividiendo en chunks de {pages_per_chunk} páginas...")
            
            temp_pdf_paths = []
            num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
            
            for chunk_idx in range(num_chunks):
                start_page = chunk_idx * pages_per_chunk
                end_page = min(start_page + pages_per_chunk, total_pages)
                
                print(f"   📦 Chunk {chunk_idx + 1}/{num_chunks} (páginas {start_page + 1}-{end_page})")
                
                writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_chunk_{chunk_idx}.pdf')
                temp_path = temp_file.name
                temp_file.close()
                
                with open(temp_path, 'wb') as output_file:
                    writer.write(output_file)
                
                temp_pdf_paths.append({
                    'path': temp_path,
                    'start_page': start_page + 1,
                    'end_page': end_page,
                    'chunk_index': chunk_idx
                })
            
            return temp_pdf_paths
            
        except Exception as e:
            print(f"   ❌ Error dividiendo PDF: {str(e)}")
            return None
    
    def _generate_mini_summary(self, content: str, chunk_num: int, total_chunks: int, 
                               start_page: int = None, end_page: int = None, section: str = None) -> str:
        """Genera un mini-summary de un chunk específico"""
        try:
            location = f"páginas {start_page}-{end_page}" if start_page else section or f"sección {chunk_num}"
            
            summary_response = self.mistral_client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Generate a brief summary (max 200 words) of this content section.
                        
                        This is part {chunk_num} of {total_chunks} ({location}).
                        
                        Focus on:
                        - Main topics covered
                        - Key technical points
                        - Important definitions or concepts
                        - Critical requirements or specifications
                        
                        Be concise but capture essential information."""
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this section:\n\n{content[:6000]}"
                    }
                ]
            )
            
            return summary_response.choices[0].message.content
            
        except Exception as e:
            return f"[Error generating summary for {location}]"
    
    def _combine_mini_summaries(self, mini_summaries: List[Dict], document_title: str) -> str:
        """Combina mini-summaries en un summary ejecutivo final"""
        try:
            combined_text = f"Document: {document_title}\n\n"
            combined_text += "Section Summaries:\n\n"
            
            for ms in mini_summaries:
                location = ms.get('pages') or ms.get('section', f"Part {ms['chunk_index']}")
                combined_text += f"[{location}]\n{ms['summary']}\n\n"
            
            final_summary_response = self.mistral_client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {
                        "role": "system",
                        "content": """Create an executive summary from these section summaries.
                        
                        Synthesize into a coherent overview (max 500 words) that includes:
                        1. Overall document purpose and scope
                        2. Main topics and structure
                        3. Key technical concepts
                        4. Critical requirements or specifications
                        5. Application context
                        
                        Avoid redundancy while preserving important details."""
                    },
                    {
                        "role": "user",
                        "content": f"Create executive summary from:\n\n{combined_text}"
                    }
                ]
            )
            
            return final_summary_response.choices[0].message.content
            
        except Exception as e:
            # Fallback: concatenar mini-summaries
            return "\n\n".join([f"**{ms.get('pages', ms.get('section'))}:** {ms['summary']}" 
                               for ms in mini_summaries])
    
    def extract_content_mistral_ocr(self, pdf_path: str, max_size_mb: int = 100) -> Optional[Dict[str, Any]]:
        """
        Extrae contenido de PDF con Mistral OCR
        Si el PDF es muy grande, lo divide en chunks automáticamente
        Genera mini-summaries durante el procesamiento y los combina al final
        """
        try:
            if not os.path.exists(pdf_path):
                print(f"Error: El archivo {pdf_path} no existe")
                return None
                
            print(f"📄 Archivo: {pdf_path}")
            
            # PASO 1: Extraer metadata del documento
            print_sub_stage("EXTRACCIÓN DE METADATA DEL DOCUMENTO")
            document_title = self.extract_document_title(pdf_path)
            source_file = os.path.basename(pdf_path)
            document_id = self.generate_document_id(source_file)
            
            print(f"   📋 Document ID: {document_id}")
            print(f"   📄 Source File: {source_file}")
            print(f"   📖 Title: {document_title}")
            
            # PASO 2: Verificar tamaño del archivo
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            print(f"   📊 Tamaño archivo: {file_size_mb:.2f} MB")
            
            # PASO 3: Decidir estrategia de procesamiento
            process_in_chunks = file_size_mb > max_size_mb
            
            if process_in_chunks:
                print(f"   ⚠️  Archivo grande ({file_size_mb:.2f} MB > {max_size_mb} MB)")
                print(f"   🔄 Procesando por chunks...")
                
                # Dividir PDF
                print_sub_stage("DIVISIÓN DE PDF EN CHUNKS")
                pdf_chunks = self.split_pdf_into_chunks(pdf_path, pages_per_chunk=20)
                
                if not pdf_chunks:
                    return None
                
                # Procesar cada chunk
                print_sub_stage("PROCESAMIENTO DE CHUNKS CON MISTRAL OCR")
                all_markdown_content = ""
                total_pages = 0
                mini_summaries = []
                
                for chunk_info in pdf_chunks:
                    chunk_path = chunk_info['path']
                    chunk_idx = chunk_info['chunk_index']
                    start_page = chunk_info['start_page']
                    end_page = chunk_info['end_page']
                    
                    print(f"\n   📦 Chunk {chunk_idx + 1}/{len(pdf_chunks)} (páginas {start_page}-{end_page})")
                    
                    chunk_markdown = ""
                    
                    try:
                        print(f"      🔄 Codificando...")
                        base64_chunk = self.encode_pdf(chunk_path)
                        if not base64_chunk:
                            continue
                        
                        print(f"      🔄 Llamando a Mistral OCR...")
                        
                        def call_mistral_ocr():
                            return self.mistral_client.ocr.process(
                                model="mistral-ocr-latest",
                                document={
                                    "type": "document_url",
                                    "document_url": f"data:application/pdf;base64,{base64_chunk}"
                                }
                            )
                        
                        chunk_response = retry_with_backoff(call_mistral_ocr, max_retries=3, base_delay=2)
                        if chunk_response is None:
                            continue
                        
                        print(f"      ✅ OCR completado")
                        
                        response_dict = json.loads(chunk_response.model_dump_json())
                        pages = response_dict.get("pages", [])
                        
                        # Acumular contenido
                        for i, page in enumerate(pages):
                            actual_page_num = start_page + i
                            page_content = page.get("markdown", "")
                            all_markdown_content += f"\n\n--- Page {actual_page_num} ---\n\n{page_content}"
                            chunk_markdown += page_content + "\n"
                            print(f"      ✅ Página {actual_page_num}: {len(page_content)} chars")
                        
                        total_pages += len(pages)
                        
                        # Generar mini-summary del chunk
                        if chunk_markdown.strip():
                            print(f"      📝 Generando mini-summary...")
                            try:
                                mini_summary = self._generate_mini_summary(
                                    chunk_markdown, 
                                    chunk_idx + 1, 
                                    len(pdf_chunks),
                                    start_page,
                                    end_page
                                )
                                mini_summaries.append({
                                    "chunk_index": chunk_idx + 1,
                                    "pages": f"{start_page}-{end_page}",
                                    "summary": mini_summary
                                })
                                print(f"      ✅ Mini-summary: {len(mini_summary)} chars")
                            except Exception as e:
                                print(f"      ⚠️  Error en mini-summary: {str(e)}")
                        
                    except Exception as chunk_error:
                        print(f"      ❌ Error: {str(chunk_error)}")
                        continue
                    
                    finally:
                        # Limpiar archivo temporal
                        try:
                            os.unlink(chunk_path)
                        except:
                            pass
                
                print(f"\n   ✅ Total: {len(all_markdown_content):,} chars, {total_pages} páginas")
                print(f"   📋 Mini-summaries: {len(mini_summaries)}")
                markdown_content = all_markdown_content
                
            else:
                # PROCESAMIENTO NORMAL
                print(f"   ✅ Tamaño aceptable, procesando completo...")
                
                print_sub_stage("CODIFICACIÓN PDF A BASE64")
                base64_pdf = self.encode_pdf(pdf_path)
                if not base64_pdf:
                    return None
                
                print_sub_stage("PROCESAMIENTO CON MISTRAL OCR")
                
                def call_mistral_ocr():
                    return self.mistral_client.ocr.process(
                        model="mistral-ocr-latest",
                        document={
                            "type": "document_url",
                            "document_url": f"data:application/pdf;base64,{base64_pdf}"
                        }
                    )
                
                try:
                    pdf_response = retry_with_backoff(call_mistral_ocr, max_retries=3, base_delay=2)
                    if pdf_response is None:
                        raise Exception("Failed after all retry attempts")
                    print("✅ Mistral OCR response received")
                except Exception as api_error:
                    print(f"❌ Error: {str(api_error)}")
                    raise
                
                response_dict = json.loads(pdf_response.model_dump_json())
                pages = response_dict.get("pages", [])
                
                if pages:
                    markdown_content = ""
                    for i, page in enumerate(pages):
                        page_content = page.get("markdown", "")
                        markdown_content += f"\n\n--- Page {i+1} ---\n\n{page_content}"
                    total_pages = len(pages)
                else:
                    markdown_content = response_dict.get("content", "")
                    total_pages = 0
                
                mini_summaries = []
            
            if not markdown_content:
                print("❌ No se pudo extraer contenido")
                return None
            
            # Detectar idioma
            print_sub_stage("DETECCIÓN DE IDIOMA")
            detected_language = self.detect_language(markdown_content)
            print(f"   🌐 Idioma: {detected_language}")
            
            # Generar summary final
            print_sub_stage("GENERACIÓN DE SUMMARY")
            if process_in_chunks and mini_summaries:
                print(f"   🔄 Combinando {len(mini_summaries)} mini-summaries...")
                final_summary = self._combine_mini_summaries(mini_summaries, document_title)
                print(f"   ✅ Summary final: {len(final_summary)} chars")
            else:
                print(f"   🔄 Generando summary directo...")
                final_summary = self.generate_document_summary(markdown_content)
                print(f"   ✅ Summary: {len(final_summary)} chars")
            
            print(f"✅ Extracción completada: {len(markdown_content):,} caracteres")
            
            return {
                "markdown_content": markdown_content,
                "document_summary": final_summary,
                "metadata": {
                    "document_id": document_id,
                    "source_file": source_file,
                    "book_title": document_title,
                    "language": detected_language,
                    "total_pages": total_pages,
                    "extraction_method": "mistral_ocr_chunked" if process_in_chunks else "mistral_ocr",
                    "file_size_mb": round(file_size_mb, 2),
                    "processed_in_chunks": process_in_chunks,
                    "num_mini_summaries": len(mini_summaries)
                }
            }
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def convert_text_to_markdown(self, text_content: str, source_file: str = None) -> Dict[str, Any]:
        """
        Convierte texto plano (DOCX) a markdown SIN mini-summaries
        Procesa por chunks para evitar timeouts de API
        """
        try:
            print_sub_stage("CONVERSIÓN DE TEXTO A MARKDOWN")
            
            if source_file:
                document_id = self.generate_document_id(source_file)
                print(f"   📋 Document ID: {document_id}")
                print(f"   📄 Source File: {source_file}")
            else:
                document_id = "UNKNOWN"
                source_file = "unknown.docx"
            
            detected_language = self.detect_language(text_content)
            print(f"   🌐 Idioma: {detected_language}")
            
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            document_title = lines[0] if lines else document_id
            
            if len(document_title) > 150:
                document_title = document_title[:147] + "..."
            
            print(f"   📖 Título: {document_title}")
            print(f"   🔄 Convirtiendo a markdown...")
            
            # LÍMITE OPTIMIZADO: 60,000 chars por chunk
            max_chunk_size = 10000
            
            # Documentos grandes: dividir en chunks
            if len(text_content) > max_chunk_size:
                print(f"   ⚠️  Texto grande ({len(text_content):,} chars), procesando por chunks...")
                
                chunks = []
                current_chunk = ""
                
                for line in text_content.split('\n'):
                    if len(current_chunk + line + '\n') > max_chunk_size and current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = line + '\n'
                    else:
                        current_chunk += line + '\n'
                
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                print(f"   📊 Dividido en {len(chunks)} chunks")
                
                markdown_parts = []
                for i, chunk in enumerate(chunks):
                    print(f"   🔄 Chunk {i+1}/{len(chunks)} ({len(chunk):,} chars)...")
                    
                    # Convertir chunk a markdown
                    conversion_response = self.mistral_client.chat.complete(
                        model="mistral-small-latest",
                        messages=[
                            {
                                "role": "system",
                                "content": f"""Convert plain text to markdown. Chunk {i+1} of {len(chunks)}.
                                
                                1. Create headers (# ## ###)
                                2. Preserve all content
                                3. Add markdown formatting
                                4. Keep technical terms exact
                                {"5. Don't add main title" if i > 0 else ""}
                                
                                Return ONLY markdown."""
                            },
                            {
                                "role": "user",
                                "content": f"Convert:\n\n{chunk}"
                            }
                        ]
                    )
                    
                    chunk_markdown = conversion_response.choices[0].message.content
                    markdown_parts.append(chunk_markdown)
                    print(f"      ✅ Markdown: {len(chunk_markdown)} chars")
                
                markdown_content = "\n\n".join(markdown_parts)
                print(f"   ✅ Markdown completo: {len(markdown_content)} chars")
                
                # Summary vacío por ahora (se implementará después)
                final_summary = ""
                print(f"   ⚠️  Summary omitido temporalmente (se implementará después)")
                
            else:
                # Documento pequeño - procesar directo
                conversion_response = self.mistral_client.chat.complete(
                    model="mistral-small-latest",
                    messages=[
                        {
                            "role": "system",
                            "content": """Convert plain text to markdown.
                            
                            1. Create headers (# ## ###)
                            2. Preserve all content
                            3. Add markdown formatting
                            4. Keep technical terms exact
                            
                            Return ONLY markdown."""
                        },
                        {
                            "role": "user",
                            "content": f"Convert:\n\n{text_content}"
                        }
                    ]
                )
                
                markdown_content = conversion_response.choices[0].message.content
                print(f"   ✅ Markdown: {len(markdown_content)} chars")
                
                # Summary vacío por ahora
                final_summary = ""
                print(f"   ⚠️  Summary omitido temporalmente (se implementará después)")
            
            return {
                "markdown_content": markdown_content,
                "document_summary": final_summary,
                "metadata": {
                    "document_id": document_id,
                    "source_file": source_file,
                    "book_title": document_title,
                    "language": detected_language,
                    "total_pages": None,
                    "extraction_method": "docx_conversion",
                    "num_mini_summaries": 0  # Sin mini-summaries por ahora
                }
            }
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None
    
    def generate_document_summary(self, markdown_content: str) -> str:
        """Genera resumen del documento para metadata (documentos pequeños)"""
        try:
            content_preview = markdown_content[:8000] if len(markdown_content) > 8000 else markdown_content
            
            summary_response = self.mistral_client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {
                        "role": "system",
                        "content": """Generate a concise summary capturing:
                        1. Main topic and objectives
                        2. Key concepts
                        3. Content structure
                        4. Technical elements
                        5. Application context
                        
                        Keep it under 500 words."""
                    },
                    {
                        "role": "user", 
                        "content": f"Summarize:\n\n{content_preview}"
                    }
                ]
            )
            
            return summary_response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return "Could not generate summary."