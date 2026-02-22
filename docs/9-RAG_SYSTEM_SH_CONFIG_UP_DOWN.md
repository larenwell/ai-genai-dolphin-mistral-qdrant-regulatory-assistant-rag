# Documentación de `rag_system.sh`

## 📋 Descripción General

`rag_system.sh` es el **script maestro unificado** para gestionar todos los servicios del Asistente de Normativa. Proporciona una interfaz única para iniciar, detener, monitorear y gestionar todos los componentes del sistema.

**Ubicación:** `/root/ai-genai-rag-asistente-normativa-sincro/rag_system.sh`

---

## 🎯 Propósito

Este script centraliza la gestión de:
- **Servicios de infraestructura**: Qdrant, Ollama, PostgreSQL, LocalStack
- **Servicios principales**: RAG Service (Chainlit), Datalayer Service (Prisma Studio)
- **Firewall**: Configuración automática y persistente de reglas iptables
- **Monitoreo**: Verificación de estado y salud de servicios
- **Logs**: Acceso a logs de servicios en ejecución

---

## 🏗️ Arquitectura de Servicios

### Servicios de Infraestructura

| Servicio | Puerto | Descripción | Contenedor/Proceso |
|----------|--------|-------------|-------------------|
| **Qdrant** | 6333 | Base de datos vectorial | Docker: `qdrant-rag` |
| **Ollama** | 11434 | Modelo de embeddings local | Proceso: `ollama serve` |
| **PostgreSQL** | 5432 | Base de datos relacional | Docker: `postgres-rag` o `chainlit-datalayer-postgres` |
| **LocalStack** | 4566 | Servicios AWS simulados | Docker: `localstack-rag` o `chainlit-datalayer-localstack` |

### Servicios Principales

| Servicio | Puerto | Descripción | Sesión Screen |
|----------|--------|-------------|---------------|
| **RAG Service** | 8000 | Asistente principal (Chainlit) | `rag-service` |
| **Datalayer Service** | 5555 | Prisma Studio (Feedback) | `datalayer-service` |

---

## 📝 Comandos Principales

### Gestión Completa del Sistema

```bash
# Iniciar TODO el sistema
./rag_system.sh start

# Detener TODO el sistema
./rag_system.sh stop

# Reiniciar TODO el sistema (⚠️ reinicia Ollama/Qdrant - puede afectar ingesta)
./rag_system.sh restart

# Reiniciar solo el servicio RAG (✅ NO afecta Ollama/Qdrant - seguro para ingesta)
./rag_system.sh restart rag

# Reiniciar solo el Datalayer Service
./rag_system.sh restart datalayer

# Ver estado de TODO el sistema
./rag_system.sh status

# Verificación completa del sistema
./rag_system.sh check

# Validar que todos los servicios críticos estén activos
./rag_system.sh validate

# Monitoreo continuo (opcional: intervalo en segundos, default: 30)
./rag_system.sh monitor
./rag_system.sh monitor 60

# Reinicio de emergencia (mata todos los procesos y reinicia)
./rag_system.sh emergency
```

### Servicios Individuales

```bash
# Iniciar servicios individuales
./rag_system.sh start qdrant      # Solo Qdrant
./rag_system.sh start ollama       # Solo Ollama
./rag_system.sh start postgresql   # Solo PostgreSQL
./rag_system.sh start localstack   # Solo LocalStack
./rag_system.sh start rag          # Solo RAG Service
./rag_system.sh start datalayer    # Solo Datalayer Service
```

### Gestión de Firewall

```bash
# Configurar reglas de firewall para puerto 8000
./rag_system.sh firewall configure

# Eliminar reglas de firewall
./rag_system.sh firewall remove

# Ver estado de reglas de firewall
./rag_system.sh firewall status
```

### Ver Logs

```bash
# Ver logs del RAG Service
./rag_system.sh logs rag

# Ver logs del Datalayer Service
./rag_system.sh logs datalayer
```

### Ayuda

```bash
# Mostrar ayuda completa
./rag_system.sh help
./rag_system.sh --help
./rag_system.sh -h
```

---

## 🔥 Sistema de Firewall

### Configuración Automática

El script configura automáticamente un firewall persistente que:

1. **Permite acceso solo desde IPs autorizadas** al puerto 8000
2. **Bloquea todas las demás conexiones** al puerto 8000
3. **Persiste las reglas** después de reiniciar el sistema

### IPs Autorizadas

Las IPs autorizadas están definidas en el script:

```bash
ALLOWED_IPS=(
    "209.45.68.70"
    "161.132.3.56"
    "161.132.3.57"
    "161.132.3.58"
    "161.132.3.59"
)
```

### Persistencia

El firewall se configura de forma persistente usando:

1. **`netfilter-persistent`** (método preferido)
2. **`iptables-save`** a `/etc/iptables/rules.v4` (método alternativo)
3. **Servicio systemd** `rag-firewall-restore.service` (restauración automática al arrancar)

### Funciones de Firewall

- **`configure_firewall()`**: Configura reglas de firewall
- **`restore_firewall_rules()`**: Restaura reglas guardadas
- **`remove_firewall_rules()`**: Elimina reglas de firewall
- **`show_firewall_status()`**: Muestra estado del firewall

---

## 🔍 Funciones de Verificación

### Verificación de Servicios

El script incluye funciones para verificar el estado de cada servicio:

```bash
check_qdrant()        # Verifica Qdrant en puerto 6333
check_ollama()        # Verifica Ollama en puerto 11434
check_postgresql()    # Verifica PostgreSQL en puerto 5432
check_localstack()    # Verifica LocalStack en puerto 4566
check_rag_service()   # Verifica RAG Service (sesión screen)
check_datalayer_service()  # Verifica Datalayer Service (sesión screen)
check_firewall_rules()     # Verifica reglas de firewall
```

### Validación Completa

La función `validate_all_services()` verifica:

1. ✅ Que Qdrant esté disponible y respondiendo
2. ✅ Que Ollama esté disponible y respondiendo
3. ✅ Que PostgreSQL esté disponible y respondiendo
4. ✅ Que los servicios respondan correctamente
5. ✅ Que el modelo `nomic-embed-text` esté disponible en Ollama

---

## 🚀 Proceso de Inicio Completo

Cuando ejecutas `./rag_system.sh start`, el script realiza:

### FASE 1: Servicios de Infraestructura Base
1. **Inicia Qdrant**:
   - Verifica si existe contenedor `qdrant-rag`
   - Crea contenedor si no existe (con volumen persistente)
   - Espera hasta que responda en puerto 6333

2. **Inicia Ollama**:
   - Verifica si está ejecutándose
   - Inicia proceso `ollama serve` si no está corriendo
   - Espera hasta que responda en puerto 11434

### FASE 2: Servicios del Datalayer
1. **Inicia Docker Compose del Datalayer**:
   - Cambia a directorio `/root/chainlit-datalayer`
   - Ejecuta `docker-compose up -d`
   - Inicia PostgreSQL y LocalStack

2. **Ejecuta Migraciones de Prisma**:
   - Configura `DATABASE_URL`
   - Ejecuta `npx prisma migrate deploy`

### FASE 2.5: Validación de Servicios Críticos
1. **Valida que todos los servicios estén activos**
2. **Verifica conectividad** de cada servicio

### FASE 2.6: Configuración de Firewall
1. **Restaura reglas de firewall** si existen
2. **Configura nuevas reglas** si no existen
3. **Guarda reglas de forma persistente**

### FASE 3: Servicios Principales
1. **Inicia RAG Service**:
   - Valida dependencias críticas
   - Crea sesión screen `rag-service`
   - Ejecuta `chainlit run src/ui/app.py --host 0.0.0.0 --port 8000`

2. **Inicia Datalayer Service**:
   - Crea sesión screen `datalayer-service`
   - Ejecuta `npx prisma studio --port 5555 --hostname 0.0.0.0`

---

## 🛑 Proceso de Detención

Cuando ejecutas `./rag_system.sh stop`, el script:

1. **Detiene servicios principales**:
   - Cierra sesión screen `rag-service`
   - Cierra sesión screen `datalayer-service`

2. **Detiene contenedores Docker**:
   - Detiene `qdrant-rag`
   - Detiene `postgres-rag`
   - Detiene `localstack-rag`
   - Ejecuta `docker-compose down` en datalayer

3. **Detiene procesos**:
   - Mata proceso `ollama serve`

⚠️ **ADVERTENCIA**: Este comando **SÍ afecta** el proceso de ingesta si está corriendo, ya que detiene Ollama.

---

## 🔄 Comandos de Reinicio

### Reinicio Completo del Sistema

El comando `./rag_system.sh restart` (o `./rag_system.sh restart all`) reinicia **TODO** el sistema:

1. **Detiene todos los servicios**:
   - Servicio RAG
   - Datalayer Service
   - Contenedores Docker (Qdrant, PostgreSQL, LocalStack)
   - **Ollama** (`pkill -f "ollama serve"`)

2. **Reinicia todos los servicios**

⚠️ **ADVERTENCIA**: Este comando **SÍ afecta** el proceso de ingesta si está corriendo, ya que reinicia Ollama.

### Reinicio Solo del Servicio RAG

El comando `./rag_system.sh restart rag` reinicia **SOLO** el servicio RAG:

1. **Detiene solo el servicio RAG**
2. **Reinicia solo el servicio RAG**
3. **NO afecta** Ollama, Qdrant, PostgreSQL, LocalStack
4. **NO interrumpe** el proceso de ingesta

✅ **RECOMENDADO** cuando hay un proceso de ingesta activo.

**Cuándo usar:**
- Cuando se modifican archivos de `src/ui/app.py`
- Cuando se cambian configuraciones de retrieval
- Cuando se necesita aplicar cambios en el servicio RAG sin afectar la ingesta

### Reinicio Solo del Datalayer

El comando `./rag_system.sh restart datalayer` reinicia **SOLO** el Datalayer Service:

1. **Detiene solo el Datalayer Service**
2. **Reinicia solo el Datalayer Service**
3. **NO afecta** otros servicios

### Reinicio de Emergencia

El comando `./rag_system.sh emergency` realiza un reinicio completo con limpieza:

1. **Detiene todos los servicios**
2. **Espera 5 segundos**
3. **Limpia procesos huérfanos**:
   - Mata procesos `ollama serve`
   - Mata procesos `chainlit`
   - Mata procesos `prisma`
4. **Limpia contenedores Docker**:
   - Detiene todos los contenedores
   - Elimina todos los contenedores
5. **Espera 3 segundos más**
6. **Inicia todos los servicios**

⚠️ **ADVERTENCIA**: Este comando **SÍ afecta** el proceso de ingesta.

---

## 📊 Monitoreo Continuo

El comando `./rag_system.sh monitor [intervalo]` muestra:

- Estado de Qdrant (Activo/Inactivo)
- Estado de Ollama (Activo/Inactivo)
- Estado de PostgreSQL (Activo/Inactivo)
- Estado de LocalStack (Activo/Inactivo)
- Estado de RAG Service (Activo/Inactivo) con URL
- Estado de Datalayer Service (Activo/Inactivo) con URL
- Próxima verificación en X segundos

**Presiona Ctrl+C para salir del monitor.**

---

## 🔍 Verificación Completa del Sistema

El comando `./rag_system.sh check` muestra:

1. **Directorio actual**
2. **Puertos en uso** (8000, 5555, 6333, 11434, 5432, 4566)
3. **Procesos activos** (chainlit, prisma, ollama, qdrant)
4. **Contenedores Docker** activos
5. **Sesiones screen** activas
6. **Conectividad de servicios** (cada servicio responde o no)
7. **URLs de acceso**
8. **Comandos de acción recomendados**

---

## 📋 Configuración

### Variables Principales

```bash
PROJECT_DIR="/root/ai-genai-rag-asistente-normativa-sincro"
DATALAYER_DIR="/root/chainlit-datalayer"
RAG_SERVICE_NAME="rag-service"
DATALAYER_SERVICE_NAME="datalayer-service"
HOST="0.0.0.0"
RAG_PORT="8000"
DATALAYER_PORT="5555"
```

### IPs Permitidas

```bash
ALLOWED_IPS=(
    "209.45.68.70"
    "161.132.3.56"
    "161.132.3.57"
    "161.132.3.58"
    "161.132.3.59"
)
```

**Para modificar las IPs permitidas**, edita el array `ALLOWED_IPS` en el script.

---

## 🐳 Gestión de Contenedores Docker

### Qdrant

- **Nombre del contenedor**: `qdrant-rag`
- **Puertos**: 6333 (HTTP), 6334 (gRPC)
- **Volumen**: `$(pwd)/qdrant_storage:/qdrant/storage`
- **Imagen**: `qdrant/qdrant:latest`

### PostgreSQL

- **Nombre del contenedor**: `postgres-rag` (standalone) o `chainlit-datalayer-postgres` (datalayer)
- **Puerto**: 5432
- **Base de datos**: `chainlit` (standalone) o `postgres` (datalayer)
- **Imagen**: `postgres:16`

### LocalStack

- **Nombre del contenedor**: `localstack-rag` (standalone) o `chainlit-datalayer-localstack` (datalayer)
- **Puerto**: 4566
- **Servicios**: s3, lambda, iam, sts
- **Imagen**: `localstack/localstack:latest`

---

## 📺 Gestión de Sesiones Screen

El script usa `screen` para ejecutar servicios de forma persistente:

- **RAG Service**: Sesión `rag-service`
- **Datalayer Service**: Sesión `datalayer-service`

### Comandos Útiles de Screen

```bash
# Ver todas las sesiones screen
screen -list

# Conectarse a una sesión
screen -r rag-service
screen -r datalayer-service

# Desconectarse de una sesión (sin cerrarla)
# Presiona: Ctrl+A, luego D

# Cerrar una sesión
screen -S rag-service -X quit
```

---

## 🔐 Permisos Requeridos

### Para Firewall

El script requiere permisos de **root** o **sudo** para configurar iptables:

- Si ejecutas como root: Funciona directamente
- Si ejecutas como usuario normal: Usa `sudo` automáticamente

### Para Docker

El usuario debe estar en el grupo `docker` o tener permisos para ejecutar Docker.

### Para Screen

No requiere permisos especiales.

---

## ⚠️ Solución de Problemas

### Error: "Qdrant no se pudo iniciar"

```bash
# Verificar logs del contenedor
docker logs qdrant-rag

# Verificar si el puerto está ocupado
lsof -ti:6333

# Reiniciar Qdrant
./rag_system.sh start qdrant
```

### Error: "Ollama no está instalado"

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Iniciar Ollama
./rag_system.sh start ollama
```

### Error: "No se pudo configurar firewall"

```bash
# Verificar permisos
sudo iptables -L

# Configurar manualmente
sudo ./rag_system.sh firewall configure

# Ver estado
./rag_system.sh firewall status
```

### Error: "Servicio RAG no responde"

```bash
# Ver logs
./rag_system.sh logs rag

# Verificar que las dependencias estén activas
./rag_system.sh validate

# Reiniciar servicio
./rag_system.sh start rag
```

### Error: "Puerto 8000 ya está en uso"

```bash
# Ver qué proceso usa el puerto
lsof -ti:8000

# Matar proceso
kill -9 $(lsof -ti:8000)

# Reiniciar servicio
./rag_system.sh start rag
```

---

## ⚠️ Impacto en el Proceso de Ingesta

### Comandos que NO Afectan la Ingesta

✅ **Seguros para usar cuando hay ingesta activa:**

```bash
./rag_system.sh restart rag      # Solo reinicia RAG Service
./rag_system.sh restart datalayer  # Solo reinicia Datalayer
./rag_system.sh start rag        # Solo inicia RAG Service
./rag_system.sh start datalayer  # Solo inicia Datalayer
```

### Comandos que SÍ Afectan la Ingesta

⚠️ **NO usar cuando hay ingesta activa:**

```bash
./rag_system.sh restart          # Reinicia TODO (incluye Ollama)
./rag_system.sh restart all      # Reinicia TODO (incluye Ollama)
./rag_system.sh stop            # Detiene TODO (incluye Ollama)
./rag_system.sh emergency        # Reinicio completo con limpieza
```

### ¿Por qué afecta la ingesta?

El proceso de ingesta (`ingest_pipeline.py`) usa **Ollama** para generar embeddings. Si Ollama se reinicia:
- ❌ El proceso de ingesta pierde la conexión temporalmente
- ❌ Algunos embeddings pueden fallar durante la desconexión
- ✅ El proceso se recupera automáticamente cuando Ollama vuelve a estar disponible
- ⚠️ Los embeddings que fallaron durante la desconexión se pierden

### Recomendación

**Antes de reiniciar, verificar si hay ingesta activa:**

```bash
# Verificar proceso de ingesta
ps aux | grep ingest_pipeline

# Si hay ingesta activa, usar:
./rag_system.sh restart rag  # ✅ Seguro

# Si NO hay ingesta activa, puedes usar:
./rag_system.sh restart      # ⚠️ Reinicia todo
```

**Ver documentación completa:** `docs/ADVERTENCIA_REINICIO_INGESTA.md`

---

## 📝 Notas Importantes

1. **El script NO elimina datos de Qdrant**: El volumen `qdrant_storage/` es persistente y no se elimina al detener servicios.

2. **El firewall se configura automáticamente**: Al iniciar el RAG Service, el firewall se configura/restaura automáticamente.

3. **Los servicios se validan antes de iniciar**: El script valida que las dependencias estén activas antes de iniciar servicios principales.

4. **Las reglas de firewall son persistentes**: Se restauran automáticamente al reiniciar el sistema.

5. **Los servicios se ejecutan en background**: Usando `screen` para persistencia y `nohup` para Ollama.

6. **Reinicio selectivo disponible**: Usa `restart rag` o `restart datalayer` para reiniciar solo servicios específicos sin afectar otros.

---

## 🌐 URLs de Acceso

Después de iniciar el sistema, los servicios están disponibles en:

- **Asistente RAG**: http://161.132.45.154:8000/
- **Feedback Datalayer**: http://161.132.45.154:5555/
- **Qdrant Dashboard**: http://161.132.45.154:6333/dashboard

**Nota**: Solo las IPs autorizadas pueden acceder al puerto 8000.

---

## 📚 Referencias

- **Documentación de Firewall**: `docs/FIREWALL_PERSISTENTE.md`
- **Documentación de Servicios**: `SERVICIOS.md`
- **Documentación del Pipeline**: `docs/PIPELINE_INGESTA.md`

---

**Última Actualización:** 2026-01-10

---

## 📚 Referencias Adicionales

- **Advertencia sobre Reinicio e Ingesta**: `docs/ADVERTENCIA_REINICIO_INGESTA.md`
- **Impacto de Cambios en Ingesta**: `docs/IMPACTO_CAMBIOS_INGESTA.md`

