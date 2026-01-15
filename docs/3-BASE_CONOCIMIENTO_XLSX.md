# Documentación de `base-conocimiento.xlsx`

## 📋 Descripción General

`base-conocimiento.xlsx` es el **archivo fuente de verdad** que contiene toda la información de los documentos que se procesarán en el pipeline de ingesta. Este archivo Excel es procesado por `src/utils/excel_parser_base_conocimiento.py` para generar archivos JSON de metadata individuales.

**Ubicación:** `data/base-conocimiento.xlsx`

---

## 🎯 Propósito

Este archivo Excel centraliza:
- **Información de documentos**: Metadata completa de cada documento
- **Clasificación por pestañas**: Organización por categorías temáticas
- **Campos obligatorios y opcionales**: Estructura definida por el cliente
- **Fuente única de verdad**: Todos los scripts del pipeline leen desde aquí

---

## 📊 Estructura del Excel

### Estructura de Filas

El Excel tiene una estructura especial de 3 filas iniciales:

| Fila | Índice | Contenido | Descripción |
|------|--------|-----------|-------------|
| **Fila 1** | 0 | Categorías | `temp`, `obligatorio`, `opcional` |
| **Fila 2** | 1 | Nombres de columnas | Nombres reales de campos (document_id, source_file, etc.) |
| **Fila 3+** | 2+ | Datos | Datos reales de documentos |

### Categorías de Columnas

Las columnas están agrupadas en 3 categorías:

1. **`temp`**: Campos temporales (Nro., nombre archivo, Nro. páginas, peso (MB))
2. **`obligatorio`**: Campos obligatorios (document_id, source_file, book_title, code, etc.)
3. **`opcional`**: Campos opcionales (is_base_regulation, regulates, regulated_by, etc.)

---

## 📑 Pestañas Procesadas

El script procesa las siguientes pestañas (categorías temáticas):

| Pestaña | Descripción |
|---------|-------------|
| **NFPA** | Estándares de la National Fire Protection Association |
| **FMDS** | Normas FMDS (Fire and Mechanical Detection Systems) |
| **RNE** | Reglamento Nacional de Edificaciones |
| **Gestion** | Normas de gestión |
| **ISO** | Estándares ISO |
| **SST** | Seguridad y Salud en el Trabajo |
| **Medio Ambiente** | Normas ambientales |
| **ASIS** | Estándares ASIS |

### Pestañas Ignoradas

Las siguientes pestañas son **ignoradas** por el script:

- `catalogo`
- `resultados de ingesta`

---

## 📝 Campos Principales

### Campos Temporales (`temp`)

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `Nro.` | Número de registro | `1`, `2`, `3` |
| `nombre archivo` | Nombre del archivo original | `NFPA 22.pdf` |
| `Nro. páginas` | Número de páginas del documento | `222` |
| `peso (MB)` | Tamaño del archivo en MB | `14.4` |

### Campos Obligatorios (`obligatorio`)

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `document_id` | ID único del documento | `NFPA_22_2023_ED_2023` |
| `source_file` | Nombre del archivo fuente | `NFPA_22_2023_source.pdf` |
| `book_title` | Título del documento | `Standard for Water Tanks for Private Fire Protection` |
| `code` | Código normativo | `NFPA 22` |
| `full_name` | Nombre completo | `NFPA 22: Standard for Water Tanks for Private Fire Protection` |
| `edition` | Edición/año | `2023` |
| `provider` | Proveedor/emisor | `NFPA` |
| `provider_full_name` | Nombre completo del proveedor | `National Fire Protection Association` |
| `country` | País (código ISO) | `US` |
| `scope` | Alcance | `national`, `international` |
| `status` | Estado | `vigente`, `obsoleto` |
| `jerarquia_normativa` | Nivel jerárquico | `1`, `2`, `3`, `4`, `5` |
| `language` | Idioma | `es`, `en` |

### Campos Opcionales (`opcional`)

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `is_base_regulation` | Es regulación base | `true`, `false` |
| `regulates` | Normas que regula | `DS_005-2012-TR, RM_249-2017-TR` |
| `regulated_by` | Norma que lo regula | `Ley_29783_2011` |
| `thematic_area` | Área temática | `seguridad_salud_trabajo` |
| `tipo_principal` | Tipo principal | `ley_organica`, `decreto_supremo` |
| `tipo_secundario` | Tipo secundario | `ley_organica_sst` |
| `sector` | Sector | `seguridad_industrial` |
| `disciplina` | Disciplina (separado por comas) | `seguridad_ocupacional, prevencion_riesgos` |
| `aplicabilidad` | Aplicabilidad (separado por comas) | `construccion, mineria, industria` |
| `publication_date` | Fecha de publicación | `2011-08-20` |
| `effective_date` | Fecha de vigencia | `2011-08-21` |
| `expiration_date` | Fecha de expiración | `null` |
| `supersedes` | Reemplaza a | `Ley_28806` |
| `superseded_by` | Reemplazado por | `null` |
| `related_standards` | Estándares relacionados | `DS 005-2012-TR, RM 249-2017-TR` |
| `complementary_norms` | Normas complementarias | `ISO 45001, OHSAS 18001` |
| `conflicts_with` | Conflictos con | `null` |
| `derived_from` | Derivado de | `null` |

---

## 🔄 Procesamiento del Excel

### Script de Procesamiento

El archivo es procesado por:

```bash
python src/utils/excel_parser_base_conocimiento.py
```

### Proceso de Lectura

1. **Lee cada pestaña** de `DOCUMENT_SHEETS`
2. **Extrae mapeo de columnas** desde filas 0 y 1
3. **Procesa datos** desde fila 2 en adelante
4. **Normaliza campos** según categorías (temp, obligatorio, opcional)
5. **Genera JSON individual** para cada documento

### Salida

El script genera archivos JSON en:

```
output/metadata/source/{pestaña}/{document_id}_source.json
```

**Ejemplo:**
```
output/metadata/source/NFPA/NFPA_22_2023_ED_2023_source.json
```

---

## 🔍 Detección de Duplicados

El script detecta y maneja duplicados de dos formas:

### 1. Duplicados dentro de la misma pestaña

- ✅ **Usa la primera ocurrencia** encontrada en la pestaña
- ⚠️ **Muestra advertencia** para cada duplicado:
  ```
  ⚠️ Duplicado detectado en fila XX: DOC_ID (pestaña: NOMBRE)
     Se usará la primera ocurrencia definida en la fila YY, la fila XX será ignorada.
  ```

### 2. Duplicados entre diferentes pestañas

- ✅ **Usa la primera ocurrencia** de la primera pestaña en `DOCUMENT_SHEETS`
- ⚠️ **Muestra advertencia** para cada duplicado:
  ```
  ⚠️ Duplicado detectado: DOC_ID
     Ya existe en pestaña: PRIMERA_PESTAÑA (fila YY)
     Se ignorará la ocurrencia en pestaña: SEGUNDA_PESTAÑA (fila XX)
  ```

---

## 📄 Estructura del JSON Generado

Cada archivo `{document_id}_source.json` tiene la siguiente estructura:

```json
{
  "document_id": "NFPA_22_2023_ED_2023",
  "sheet": "NFPA",
  "temp": {
    "Nro.": "1",
    "nombre archivo": "NFPA 22.pdf",
    "Nro. páginas": "222",
    "peso (MB)": "14.4"
  },
  "sincro": {
    "document_id": "NFPA_22_2023_ED_2023",
    "source_file": "NFPA_22_2023_source.pdf",
    "book_title": "Standard for Water Tanks for Private Fire Protection",
    "code": "NFPA 22",
    "full_name": "NFPA 22: Standard for Water Tanks for Private Fire Protection",
    "edition": "2023",
    "provider": "NFPA",
    "provider_full_name": "National Fire Protection Association",
    "country": "US",
    "scope": "international",
    "status": "vigente",
    "jerarquia_normativa": 2,
    "language": "en",
    "is_base_regulation": true,
    "regulates": [],
    "regulated_by": null,
    "thematic_area": "fire_protection",
    "tipo_principal": "estandar_internacional",
    "tipo_secundario": "nfpa_standard",
    "sector": "proteccion_incendios",
    "disciplina": "sistemas_agua",
    "aplicabilidad": ["construccion", "industrial"],
    "publication_date": "2023-01-01",
    "effective_date": "2023-01-01",
    "expiration_date": null,
    "supersedes": null,
    "superseded_by": null,
    "related_standards": [],
    "complementary_norms": [],
    "conflicts_with": [],
    "derived_from": null
  }
}
```

---

## 🔧 Configuración del Parser

### Pestañas a Procesar

Definidas en `src/utils/excel_parser_base_conocimiento.py`:

```python
DOCUMENT_SHEETS = [
    'NFPA', 
    'FMDS', 
    'RNE', 
    'Gestion', 
    'ISO', 
    'SST', 
    'Medio Ambiente', 
    'ASIS'
]
```

### Pestañas a Ignorar

```python
IGNORED_SHEETS = [
    'catalogo', 
    'resultados de ingesta'
]
```

---

## 📋 Uso del Parser

### Ejecución Básica

```bash
# Procesar Excel con configuración por defecto
python src/utils/excel_parser_base_conocimiento.py
```

### Opciones Avanzadas

```bash
# Especificar ruta al Excel
python src/utils/excel_parser_base_conocimiento.py --excel data/base-conocimiento.xlsx

# Especificar directorio de salida
python src/utils/excel_parser_base_conocimiento.py --output output/metadata/source

# No limpiar directorio antes de exportar (preservar archivos existentes)
python src/utils/excel_parser_base_conocimiento.py --no-clean
```

### Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--excel` | Ruta al archivo Excel | `data/base-conocimiento.xlsx` |
| `--output` | Directorio de salida | `output/metadata/source` |
| `--no-clean` | No limpiar directorio antes de exportar | `False` (limpia por defecto) |

---

## ⚠️ Validaciones y Errores

### Validaciones Realizadas

1. ✅ **Existencia del archivo Excel**
2. ✅ **Estructura de filas** (debe tener al menos 3 filas)
3. ✅ **Mapeo de columnas** (debe tener filas de categorías y nombres)
4. ✅ **Document ID único** (dentro de la misma pestaña y entre pestañas)

### Errores Comunes

1. **Excel no encontrado**:
   ```
   FileNotFoundError: Excel no encontrado: data/base-conocimiento.xlsx
   ```
   **Solución**: Verificar que el archivo existe en la ruta especificada.

2. **Pestaña con menos de 3 filas**:
   ```
   ⚠️ Pestaña 'NOMBRE' tiene menos de 3 filas, omitiendo
   ```
   **Solución**: Verificar que la pestaña tenga al menos filas de categorías, nombres y datos.

3. **No se pudo obtener mapeo de columnas**:
   ```
   ⚠️ No se pudo obtener mapeo de columnas para 'NOMBRE'
   ```
   **Solución**: Verificar que las filas 0 y 1 tengan el formato correcto.

---

## 📊 Estadísticas de Procesamiento

Al finalizar el procesamiento, el script muestra:

```
📋 DOCUMENTOS POR PESTAÑA:
  NFPA: 45 documentos
  FMDS: 12 documentos
  RNE: 8 documentos
  ...

📁 EXPORTANDO A JSON...
✅ Archivos creados: 65
❌ Errores: 0
```

---

## 🔗 Integración con el Pipeline

El archivo `base-conocimiento.xlsx` es el **Paso 1** del pipeline de ingesta:

1. **Paso 1**: `excel_parser_base_conocimiento.py` → Genera `output/metadata/source/`
2. **Paso 2**: `docx_to_pdf.py` → Usa metadata de source para convertir archivos
3. **Paso 3**: `generate_markdown.py` → Usa metadata de source para extraer contenido
4. **Paso 4**: `translate_pipeline.py` → Usa metadata de source para traducción
5. **Paso 5**: `ingest_pipeline.py` → Usa metadata de source para ingesta

**Ver documentación completa**: `docs/PIPELINE_INGESTA.md`

---

## 📝 Notas Importantes

1. **El Excel es la fuente de verdad**: Todos los scripts leen desde este archivo.

2. **Los campos obligatorios deben estar completos**: El parser valida que los campos obligatorios tengan valores.

3. **Los duplicados se manejan automáticamente**: El script usa la primera ocurrencia y muestra advertencias.

4. **El directorio de salida se limpia por defecto**: Usa `--no-clean` para preservar archivos existentes.

5. **Los campos opcionales pueden ser `null`**: Si un campo opcional no tiene valor, se guarda como `null` en el JSON.

---

## 🔄 Actualización del Excel

### Cuándo Actualizar

Actualiza el Excel cuando:
- ✅ Agregas nuevos documentos
- ✅ Modificas información de documentos existentes
- ✅ Cambias clasificaciones o categorías
- ✅ Actualizas fechas o estados

### Cómo Actualizar

1. **Edita el Excel** `data/base-conocimiento.xlsx`
2. **Ejecuta el parser**:
   ```bash
   python src/utils/excel_parser_base_conocimiento.py
   ```
3. **Verifica los JSONs generados** en `output/metadata/source/`

---

## 📚 Referencias

- **Script de procesamiento**: `src/utils/excel_parser_base_conocimiento.py`
- **Documentación del Pipeline**: `docs/PIPELINE_INGESTA.md`
- **Template de metadata**: `data/metadata/metadata_template.json`

---

**Última Actualización:** 2025-01-05

