import os
import uuid
import ollama
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
import time

load_dotenv()

QDRANT_URL = "http://localhost:6333"  # Default Qdrant URL
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "norms-mistral")

class EmbeddingControllerQdrant:
    def __init__(self, model_name: str = "nomic-embed-text", qdrant_url: str = QDRANT_URL, qdrant_collection: str = QDRANT_COLLECTION_NAME):
        self.model_name = model_name
        self.qdrant_url = qdrant_url
        self.qdrant_collection = qdrant_collection

        if not self.qdrant_url:
            raise ValueError("Qdrant URL is required")
        if not self.qdrant_collection:
            raise ValueError("Qdrant collection name is required")

        # Initialize Qdrant client with connection timeout
        try:
            print(f"🔗 Conectando a Qdrant en {qdrant_url}...")
            self.qdrant_client = QdrantClient(url=qdrant_url, timeout=10)
            
            # Test connection by getting collections
            print(f"🔍 Verificando colección '{self.qdrant_collection}'...")
            collections = self.qdrant_client.get_collections().collections
            
            # Check if collection exists, if not create it
            if not any(col.name == self.qdrant_collection for col in collections):
                print(f"📦 Creando nueva colección: {self.qdrant_collection}")
                self.qdrant_client.create_collection(
                    collection_name=self.qdrant_collection,
                    vectors_config=models.VectorParams(
                        size=768,  # Dimension for nomic-embed-text
                        distance=models.Distance.COSINE
                    )
                )
                print(f"✅ Colección '{self.qdrant_collection}' creada exitosamente")
            else:
                print(f"✅ Colección '{self.qdrant_collection}' ya existe")
                
        except Exception as e:
            error_msg = f"❌ Error conectando a Qdrant en {qdrant_url}: {str(e)}"
            print(error_msg)
            print(f"💡 Asegúrate de que Qdrant esté ejecutándose:")
            print(f"   - Verifica: curl http://localhost:6333/collections")
            print(f"   - O ejecuta: ./rag_system.sh start qdrant")
            raise ConnectionError(error_msg) from e

    def generate_embeddings(self, text: str) -> list:
        """Genera embeddings usando Ollama con manejo robusto de errores"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = ollama.embed(model=self.model_name, input=text)
                if response and "embeddings" in response and len(response["embeddings"]) > 0:
                    return response["embeddings"][0]
                else:
                    raise ValueError("Ollama response is empty or invalid")
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Error generando embedding (intento {attempt + 1}/{max_retries}): {e}")
                    print(f"   Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    error_msg = f"❌ Error crítico generando embedding después de {max_retries} intentos: {e}"
                    print(error_msg)
                    print(f"💡 Asegúrate de que Ollama esté ejecutándose:")
                    print(f"   - Verifica: curl http://localhost:11434/api/tags")
                    print(f"   - O ejecuta: ./rag_system.sh start ollama")
                    raise ConnectionError(error_msg) from e
        
        return []
    
    def delete_collection(self):
        """Elimina la colección actual"""
        try:
            self.qdrant_client.delete_collection(collection_name=self.qdrant_collection)
            print(f"✅ Colección '{self.qdrant_collection}' eliminada")
            return True
        except Exception as e:
            print(f"❌ Error eliminando colección: {e}")
            return False
    
    def recreate_collection(self):
        """Recrea la colección (borra y crea de nuevo)"""
        try:
            # Verificar si existe
            collections = self.qdrant_client.get_collections().collections
            if any(col.name == self.qdrant_collection for col in collections):
                print(f"🗑️ Eliminando colección existente '{self.qdrant_collection}'...")
                self.qdrant_client.delete_collection(collection_name=self.qdrant_collection)
            
            # Crear nueva
            print(f"🆕 Creando nueva colección '{self.qdrant_collection}'...")
            self.qdrant_client.create_collection(
                collection_name=self.qdrant_collection,
                vectors_config=models.VectorParams(
                    size=768,  # Dimension for nomic-embed-text
                    distance=models.Distance.COSINE
                )
            )
            print(f"✅ Colección recreada exitosamente")
            return True
        except Exception as e:
            print(f"❌ Error recreando colección: {e}")
            return False
    
    def check_document_exists(self, document_id: str) -> bool:
        """
        Verifica si un documento ya existe en la colección
        Busca por el campo 'document_id' en los metadatos
        
        Args:
            document_id: ID del documento a buscar
            
        Returns:
            True si el documento existe, False en caso contrario
        """
        try:
            # Scroll para obtener todos los puntos con ese document_id
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.qdrant_collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1  # Solo necesitamos saber si existe al menos uno
            )
            
            points = scroll_result[0]  # scroll devuelve (points, next_page_offset)
            exists = len(points) > 0
            
            if exists:
                print(f"   ⚠️ Documento '{document_id}' ya existe en la colección")
            
            return exists
            
        except Exception as e:
            print(f"   ⚠️ Error verificando duplicados: {e}")
            return False  # En caso de error, asumir que no existe y continuar
    
    def delete_document(self, document_id: str) -> bool:
        """
        Elimina todos los chunks de un documento específico
        
        Args:
            document_id: ID del documento a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            # Primero verificar cuántos puntos hay
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.qdrant_collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=10000  # Límite alto para obtener todos
            )
            
            points = scroll_result[0]
            
            if len(points) == 0:
                print(f"   ℹ️ No se encontraron puntos para '{document_id}'")
                return True
            
            # Eliminar por filtro
            self.qdrant_client.delete(
                collection_name=self.qdrant_collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            )
            
            print(f"   🗑️ Eliminados {len(points)} chunks del documento '{document_id}'")
            return True
            
        except Exception as e:
            print(f"   ❌ Error eliminando documento: {e}")
            return False
    
    def get_collection_stats(self) -> dict:
        """
        Obtiene estadísticas de la colección
        
        Returns:
            Dict con total_chunks, unique_documents y document_names
        """
        try:
            count = self.qdrant_client.count(self.qdrant_collection).count
            
            # Obtener muestra de documentos únicos
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.qdrant_collection,
                limit=1000,
                with_payload=True
            )
            
            points = scroll_result[0]
            
            # Contar documentos únicos
            unique_docs = set()
            for point in points:
                if 'document_name' in point.payload:
                    unique_docs.add(point.payload['document_name'])
            
            return {
                'total_chunks': count,
                'unique_documents': len(unique_docs),
                'document_names': list(unique_docs)
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return {
                'total_chunks': 0,
                'unique_documents': 0,
                'document_names': []
            }
        
    def store_embeddings(self, embeddings: list, chunks: list, chunk_metadata: list = []):
        """
        Almacena embeddings en Qdrant con manejo robusto de errores y reintentos
        
        Args:
            embeddings: Lista de vectores de embeddings
            chunks: Lista de chunks (texto o dict con content)
            chunk_metadata: Lista de metadatos adicionales (opcional)
            
        Returns:
            True si todos se guardaron exitosamente, False si hubo fallos
        """
        try:
            points_to_upsert = []
            successful_insertions = 0
            failed_insertions = 0
            
            # Preparar puntos
            for i, (embedding, chunk) in enumerate(zip(embeddings, chunks)):
                try:
                    # Extract text content from chunk
                    if isinstance(chunk, dict):
                        text_content = chunk.get('content', str(chunk))
                        # Extract metadata from chunk, excluding the content field
                        chunk_meta = {k: v for k, v in chunk.get('metadata', {}).items() 
                                    if k != 'content' and isinstance(v, (str, int, float, bool, list))}
                    else:
                        text_content = str(chunk)
                        chunk_meta = {}
                    
                    # Combine metadata
                    metadata = {
                        'text': text_content,
                        **chunk_meta,
                        **({} if not chunk_metadata or i >= len(chunk_metadata) else chunk_metadata[i])
                    }
                    
                    point = models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=metadata
                    )
                    points_to_upsert.append(point)
                    
                except Exception as e:
                    print(f"⚠️ Error preparando punto {i}: {e}")
                    failed_insertions += 1
                    continue
            
            print(f"📊 Puntos preparados: {len(points_to_upsert)}")
            
            # Upsert en lotes con reintentos
            batch_size = 50  # Reducido para mayor estabilidad
            max_retries = 3
            
            for i in range(0, len(points_to_upsert), batch_size):
                batch = points_to_upsert[i:i + batch_size]
                batch_num = i//batch_size + 1
                total_batches = (len(points_to_upsert)-1)//batch_size + 1
                
                # Reintentos para cada lote
                for retry in range(max_retries):
                    try:
                        result = self.qdrant_client.upsert(
                            collection_name=self.qdrant_collection,
                            points=batch
                        )
                        
                        if result.status == "completed":
                            successful_insertions += len(batch)
                            print(f"✅ Lote {batch_num}/{total_batches}: {len(batch)} puntos insertados")
                            break
                        else:
                            raise Exception(f"Upsert falló con status: {result.status}")
                            
                    except Exception as e:
                        if retry < max_retries - 1:
                            print(f"⚠️ Lote {batch_num} falló (intento {retry + 1}/{max_retries}): {e}")
                            print(f"   Reintentando en 2 segundos...")
                            time.sleep(2)
                        else:
                            print(f"❌ Lote {batch_num} falló definitivamente: {e}")
                            failed_insertions += len(batch)
                
                # Pequeña pausa entre lotes para evitar sobrecarga
                time.sleep(0.1)
            
            # Verificar inserción final
            final_count = self.qdrant_client.count(self.qdrant_collection).count
            print(f"📊 Resumen de inserción:")
            print(f"   ✅ Exitosos: {successful_insertions}")
            print(f"   ❌ Fallidos: {failed_insertions}")
            print(f"   📈 Total en colección: {final_count}")
            
            if failed_insertions > 0:
                print(f"⚠️ ADVERTENCIA: {failed_insertions} chunks no se insertaron correctamente")
                return False
            else:
                print(f"🎉 Todos los chunks insertados exitosamente")
                return True
                
        except Exception as e:
            print(f"❌ Error crítico almacenando embeddings: {str(e)}")
            raise

    def load_and_query_qdrant(self, query_embedding: list, top_k: int = 4):
        """
        Realiza una búsqueda de similitud en Qdrant
        
        Args:
            query_embedding: Vector de embedding de la consulta
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de resultados ordenados por similitud
        """
        results = self.qdrant_client.search(
            collection_name=self.qdrant_collection,
            query_vector=query_embedding,
            limit=top_k
        )
        
        return results