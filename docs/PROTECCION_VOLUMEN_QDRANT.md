# Protección de Volumen Qdrant - Prevención de Pérdida de Datos

## 🚨 Problema Identificado

**Fecha:** 2026-01-10

**Síntoma:** La colección Qdrant `normativa-asistente-kb` aparecía vacía (0 puntos) aunque se habían ingestado datos previamente.

**Causa Raíz:** El contenedor Docker de Qdrant estaba usando un volumen incorrecto:
- **Volumen incorrecto:** `/root/chainlit-datalayer/qdrant_storage`
- **Volumen correcto:** `/root/ai-genai-rag-asistente-normativa-sincro/qdrant_storage`

## 🔍 Análisis

### ¿Por qué pasó?

1. **Creación manual del contenedor:** El contenedor se creó manualmente o desde otro script usando el volumen incorrecto.
2. **Detección tardía:** El script `rag_system.sh` tiene lógica para detectar esto, pero:
   - Usaba rutas relativas (`$(pwd)`) que pueden cambiar según el directorio de ejecución
   - No normalizaba rutas para comparación (symlinks, rutas relativas)
   - No verificaba rutas absolutas

### Impacto

- **Datos perdidos temporalmente:**** Los datos estaban en el volumen correcto, pero el contenedor no podía accederlos
- **Confusión:** El sistema mostraba 0 puntos aunque los datos existían
- **Riesgo:** Si se hubiera recreado el contenedor sin verificar, se habrían perdido datos

## ✅ Solución Implementada

### 1. Mejoras en `rag_system.sh`

**Cambios realizados:**

```bash
# ANTES (problemático):
expected_volume="$(pwd)/qdrant_storage"

# DESPUÉS (mejorado):
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
expected_volume="${PROJECT_DIR}/qdrant_storage"

# Normalización de rutas para comparación
current_volume=$(readlink -f "$current_volume" 2>/dev/null || echo "$current_volume")
expected_volume=$(readlink -f "$expected_volume" 2>/dev/null || echo "$expected_volume")
```

**Mejoras:**
- ✅ Usa ruta absoluta basada en la ubicación del script
- ✅ Normaliza rutas (resuelve symlinks y rutas relativas)
- ✅ Crea el directorio si no existe
- ✅ Muestra advertencia clara si detecta volumen incorrecto

### 2. Verificación Automática

El script ahora:
1. **Verifica el volumen** cada vez que se inicia Qdrant
2. **Detecta discrepancias** y muestra advertencias claras
3. **Recrea el contenedor** automáticamente si el volumen es incorrecto
4. **Muestra la ruta del volumen** al crear el contenedor

## 🛡️ Protecciones Adicionales

### Verificación Manual

Para verificar que el volumen es correcto:

```bash
# Verificar volumen del contenedor
docker inspect qdrant-rag | grep -A 3 '"Mounts"' | grep '"Source"'

# Debe mostrar:
# "/root/ai-genai-rag-asistente-normativa-sincro/qdrant_storage"
```

### Verificación de Datos

```bash
# Verificar colecciones y puntos
curl -s "http://localhost:6333/collections" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); \
  cols = data.get('result', {}).get('collections', []); \
  [print(f\"{c['name']}: {c.get('points_count', 0)} puntos\") for c in cols]"
```

### Backup Recomendado

Para prevenir pérdida de datos, se recomienda:

1. **Backup periódico del volumen:**
   ```bash
   tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz qdrant_storage/
   ```

2. **Verificación antes de operaciones críticas:**
   ```bash
   # Verificar que hay datos antes de recrear
   curl -s "http://localhost:6333/collections/normativa-asistente-kb" | \
     python3 -c "import sys, json; \
     print(json.load(sys.stdin)['result']['points_count'])"
   ```

## 📋 Checklist de Prevención

Antes de realizar operaciones que puedan afectar Qdrant:

- [ ] Verificar que el volumen es correcto: `docker inspect qdrant-rag`
- [ ] Verificar que hay datos: `curl http://localhost:6333/collections`
- [ ] Hacer backup si hay datos importantes
- [ ] Usar siempre `./rag_system.sh` para gestionar Qdrant (no crear contenedores manualmente)
- [ ] Verificar logs si algo parece incorrecto: `docker logs qdrant-rag`

## 🔄 Recuperación de Datos

Si los datos están en el volumen correcto pero el contenedor no los ve:

1. **Detener Qdrant:**
   ```bash
   ./rag_system.sh stop qdrant
   ```

2. **Eliminar contenedor:**
   ```bash
   docker rm qdrant-rag
   ```

3. **Reiniciar con volumen correcto:**
   ```bash
   ./rag_system.sh start qdrant
   ```

4. **Verificar datos:**
   ```bash
   curl http://localhost:6333/collections
   ```

## 📝 Notas Importantes

1. **Nunca crear contenedores manualmente:** Siempre usar `./rag_system.sh start qdrant`
2. **Verificar rutas:** El volumen debe ser `/root/ai-genai-rag-asistente-normativa-sincro/qdrant_storage`
3. **Backup regular:** Los datos en Qdrant son críticos, hacer backups periódicos
4. **Monitoreo:** Verificar periódicamente que las colecciones tienen puntos

## 🎯 Conclusión

El problema se debió a una discrepancia en el volumen montado. Las mejoras implementadas:

- ✅ Previenen que vuelva a ocurrir
- ✅ Detectan el problema automáticamente
- ✅ Proporcionan advertencias claras
- ✅ Facilitan la recuperación

**Última actualización:** 2026-01-10

