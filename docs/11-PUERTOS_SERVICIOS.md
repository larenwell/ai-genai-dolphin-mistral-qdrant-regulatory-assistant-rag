# Puertos y Servicios - Mapa Completo

## 📋 Descripción General

Este documento define todos los puertos utilizados por cada componente de la solución del Asistente de Normativa, incluyendo servicios de infraestructura, aplicaciones principales, y herramientas de gestión.

**Última Actualización:** 2025-01-05

---

## 🗺️ Mapa Completo de Puertos

| Servicio | Puerto | Protocolo | Descripción | Acceso |
|----------|--------|-----------|-------------|--------|
| **RAG Service (Chainlit)** | 8000 | HTTP | Interfaz principal del asistente | 🔒 Solo IPs autorizadas |
| **Datalayer Service (Prisma Studio)** | 5555 | HTTP | Interfaz de gestión de feedback | 🌐 Público |
| **Qdrant** | 6333 | HTTP | Base de datos vectorial (API REST) | 🔒 Localhost |
| **Qdrant** | 6334 | gRPC | Base de datos vectorial (gRPC) | 🔒 Localhost |
| **Ollama** | 11434 | HTTP | Servicio de embeddings locales | 🔒 Localhost |
| **PostgreSQL** | 5432 | TCP | Base de datos relacional | 🔒 Localhost |
| **LocalStack** | 4566 | HTTP | Servicios AWS simulados (S3, etc.) | 🔒 Localhost |

---

## 🎯 Servicios Principales

### 1. RAG Service (Chainlit)

**Puerto**: `8000`  
**Protocolo**: HTTP  
**Aplicación**: `src/ui/app.py`  
**Framework**: Chainlit  
**Sesión Screen**: `rag-service`

**URLs de Acceso**:
- **Local**: http://localhost:8000/
- **Externa**: http://161.132.45.154:8000/

**Seguridad**:
- 🔒 **Firewall configurado**: Solo IPs autorizadas pueden acceder
- **IPs Permitidas**: 209.45.68.70, 161.132.3.56, 161.132.3.57, 161.132.3.58, 161.132.3.59
- **Otras IPs**: Bloqueadas automáticamente

**Funcionalidad**:
- Interfaz web del asistente
- Chat interactivo con el usuario
- Sistema de feedback (thumbs up/down)
- Visualización de fuentes y relevancia

**Gestión**:
```bash
# Iniciar
./rag_system.sh start rag

# Ver logs
./rag_system.sh logs rag

# Estado
./rag_system.sh status
```

---

### 2. Datalayer Service (Prisma Studio)

**Puerto**: `5555`  
**Protocolo**: HTTP  
**Aplicación**: Prisma Studio  
**Sesión Screen**: `datalayer-service`

**URLs de Acceso**:
- **Local**: http://localhost:5555/
- **Externa**: http://161.132.45.154:5555/

**Funcionalidad**:
- Visualización de base de datos PostgreSQL
- Gestión de feedback de usuarios
- Visualización de threads, steps, users, elements
- Análisis de datos de conversaciones

**Gestión**:
```bash
# Iniciar
./rag_system.sh start datalayer

# Ver logs
./rag_system.sh logs datalayer

# Estado
./rag_system.sh status
```

---

## 🏗️ Servicios de Infraestructura

### 3. Qdrant (Base de Datos Vectorial)

**Puertos**: `6333` (HTTP), `6334` (gRPC)  
**Protocolo**: HTTP (REST API) y gRPC  
**Contenedor Docker**: `qdrant-rag`  
**Imagen**: `qdrant/qdrant:latest`

**URLs de Acceso**:
- **API REST**: http://localhost:6333/
- **Dashboard**: http://localhost:6333/dashboard
- **Colecciones**: http://localhost:6333/collections
- **gRPC**: localhost:6334

**Funcionalidad**:
- Almacenamiento de embeddings vectoriales
- Búsqueda semántica (dense search)
- Gestión de colecciones
- Metadata de chunks

**Gestión**:
```bash
# Iniciar
./rag_system.sh start qdrant

# Verificar
curl http://localhost:6333/collections

# Ver logs
docker logs qdrant-rag
```

**Volumen Persistente**: `$(pwd)/qdrant_storage:/qdrant/storage`

---

### 4. Ollama (Modelo de Embeddings)

**Puerto**: `11434`  
**Protocolo**: HTTP  
**Proceso**: `ollama serve` (background)

**URLs de Acceso**:
- **API**: http://localhost:11434/
- **Tags/Modelos**: http://localhost:11434/api/tags
- **Embed**: http://localhost:11434/api/embed

**Funcionalidad**:
- Generación de embeddings locales
- Modelo usado: `nomic-embed-text`
- Dimensiones: 768
- Sin dependencias externas

**Gestión**:
```bash
# Iniciar
./rag_system.sh start ollama

# Verificar
curl http://localhost:11434/api/tags

# Verificar modelo
curl http://localhost:11434/api/tags | grep nomic-embed-text
```

**Nota**: Ollama se ejecuta como proceso (no Docker) usando `nohup ollama serve`.

---

### 5. PostgreSQL (Base de Datos Relacional)

**Puerto**: `5432`  
**Protocolo**: TCP (PostgreSQL)  
**Contenedor Docker**: `chainlit-datalayer-postgres` (datalayer) o `postgres-rag` (standalone)  
**Imagen**: `postgres:16`

**Configuración**:
- **Usuario**: `root`
- **Contraseña**: `root`
- **Base de datos**: `postgres` (datalayer) o `chainlit` (standalone)

**Funcionalidad**:
- Almacenamiento de feedback de usuarios
- Gestión de threads (conversaciones)
- Gestión de steps (pasos en conversaciones)
- Gestión de users (usuarios)
- Gestión de elements (archivos adjuntos)

**Gestión**:
```bash
# Iniciar (como parte del datalayer)
./rag_system.sh start datalayer

# O standalone
./rag_system.sh start postgresql

# Verificar
pg_isready -h localhost -p 5432

# Conectar
psql -h localhost -U root -d postgres
```

**Volumen Persistente**: `./.data/postgres:/var/lib/postgresql/data` (en datalayer)

---

### 6. LocalStack (Servicios AWS Simulados)

**Puerto**: `4566`  
**Protocolo**: HTTP  
**Contenedor Docker**: `chainlit-datalayer-localstack` (datalayer) o `localstack-rag` (standalone)  
**Imagen**: `localstack/localstack:latest`

**URLs de Acceso**:
- **Health**: http://localhost:4566/health
- **S3**: http://localhost:4566/s3

**Servicios Disponibles**:
- **S3**: Almacenamiento de elementos (archivos adjuntos)
- **Lambda**: (opcional)
- **IAM**: (opcional)
- **STS**: (opcional)

**Funcionalidad**:
- Simulación de servicios AWS localmente
- Almacenamiento de archivos adjuntos en conversaciones
- Compatible con boto3 (Python AWS SDK)

**Gestión**:
```bash
# Iniciar (como parte del datalayer)
./rag_system.sh start datalayer

# O standalone
./rag_system.sh start localstack

# Verificar
curl http://localhost:4566/health
```

---

## 📊 Resumen por Categoría

### Servicios de Aplicación (Puertos Altos)

| Puerto | Servicio | Acceso |
|--------|----------|--------|
| **8000** | RAG Service (Chainlit) | 🔒 Solo IPs autorizadas |
| **5555** | Datalayer Service (Prisma Studio) | 🌐 Público |

### Servicios de Base de Datos

| Puerto | Servicio | Acceso |
|--------|----------|--------|
| **6333** | Qdrant (HTTP API) | 🔒 Localhost |
| **6334** | Qdrant (gRPC) | 🔒 Localhost |
| **5432** | PostgreSQL | 🔒 Localhost |

### Servicios de ML/AI

| Puerto | Servicio | Acceso |
|--------|----------|--------|
| **11434** | Ollama (Embeddings) | 🔒 Localhost |

### Servicios de Infraestructura

| Puerto | Servicio | Acceso |
|--------|----------|--------|
| **4566** | LocalStack (AWS Simulado) | 🔒 Localhost |

---

## 🔐 Seguridad y Acceso

### Puertos con Firewall

**Puerto 8000 (RAG Service)**:
- ✅ **IPs Autorizadas**: Acceso permitido
  - 209.45.68.70
  - 161.132.3.56
  - 161.132.3.57
  - 161.132.3.58
  - 161.132.3.59
- ❌ **Otras IPs**: Bloqueadas automáticamente
- **Configuración**: Automática al iniciar RAG Service
- **Persistencia**: Reglas se restauran al reiniciar

### Puertos Solo Localhost

Los siguientes puertos solo son accesibles desde localhost:
- **6333, 6334** (Qdrant)
- **11434** (Ollama)
- **5432** (PostgreSQL)
- **4566** (LocalStack)

### Puertos Públicos

- **5555** (Prisma Studio) - Accesible desde cualquier IP
  - **Nota**: En producción, considera restringir acceso

---

## 🔍 Verificación de Puertos

### Verificar Puertos en Uso

```bash
# Ver todos los puertos del sistema
netstat -tlnp | grep -E ":(8000|5555|6333|11434|5432|4566)"

# O usar el script
./rag_system.sh check
```

### Verificar Conectividad

```bash
# RAG Service
curl http://localhost:8000/

# Datalayer Service
curl http://localhost:5555/

# Qdrant
curl http://localhost:6333/collections

# Ollama
curl http://localhost:11434/api/tags

# PostgreSQL
pg_isready -h localhost -p 5432

# LocalStack
curl http://localhost:4566/health
```

---

## 🛠️ Solución de Problemas de Puertos

### Puerto Ocupado

Si un puerto está ocupado:

```bash
# Ver qué proceso usa el puerto
lsof -ti:8000
lsof -ti:5555
lsof -ti:6333

# Matar proceso (si es necesario)
kill -9 $(lsof -ti:8000)
```

### Cambiar Puerto

Para cambiar un puerto, edita las variables en `rag_system.sh`:

```bash
# Cambiar puerto del RAG Service
RAG_PORT="8001"  # En lugar de 8000

# Cambiar puerto del Datalayer
DATALAYER_PORT="5556"  # En lugar de 5555
```

**Nota**: Si cambias puertos, también actualiza:
- Variables de entorno (si aplica)
- URLs de acceso
- Configuración de firewall (para puerto 8000)

---

## 📋 Tabla de Referencia Rápida

| Servicio | Puerto | Comando Inicio | Comando Verificación |
|----------|--------|----------------|---------------------|
| **RAG Service** | 8000 | `./rag_system.sh start rag` | `curl http://localhost:8000/` |
| **Datalayer** | 5555 | `./rag_system.sh start datalayer` | `curl http://localhost:5555/` |
| **Qdrant** | 6333 | `./rag_system.sh start qdrant` | `curl http://localhost:6333/collections` |
| **Ollama** | 11434 | `./rag_system.sh start ollama` | `curl http://localhost:11434/api/tags` |
| **PostgreSQL** | 5432 | `./rag_system.sh start datalayer` | `pg_isready -h localhost -p 5432` |
| **LocalStack** | 4566 | `./rag_system.sh start datalayer` | `curl http://localhost:4566/health` |

---

## 🔄 Flujo de Comunicación

### Flujo de una Consulta

```
Usuario (Navegador)
    ↓ HTTP :8000
RAG Service (Chainlit)
    ↓ HTTP :11434
Ollama (Embeddings)
    ↓ HTTP :6333
Qdrant (Búsqueda)
    ↓ HTTP :8000
RAG Service (Respuesta)
    ↓ HTTP :8000
Usuario (Navegador)
```

### Flujo de Feedback

```
Usuario (Navegador)
    ↓ HTTP :8000
RAG Service (Chainlit)
    ↓ Automático
PostgreSQL :5432
    ↓ HTTP :5555
Prisma Studio (Visualización)
```

---

## 📝 Notas Importantes

1. **Puerto 8000 está protegido**: Solo IPs autorizadas pueden acceder. El firewall se configura automáticamente.

2. **Puertos de infraestructura son locales**: Qdrant, Ollama, PostgreSQL y LocalStack solo son accesibles desde localhost por seguridad.

3. **Prisma Studio es público**: El puerto 5555 es accesible desde cualquier IP. Considera restringir en producción.

4. **Los puertos son configurables**: Puedes cambiar los puertos editando `rag_system.sh`, pero asegúrate de actualizar todas las referencias.

5. **Verificación automática**: El script `rag_system.sh check` verifica todos los puertos automáticamente.

---

## 📚 Referencias

- **Documentación de rag_system.sh**: `docs/RAG_SYSTEM_SH.md`
- **Documentación de Feedback**: `docs/SISTEMA_FEEDBACK.md`
- **Documentación de Firewall**: `docs/FIREWALL_PERSISTENTE.md`
- **Script de Gestión**: `rag_system.sh`

---

**Última Actualización:** 2025-01-05

