"""
Retrieval Configuration - FASE C (VERSIÓN FINAL)

Configuración centralizada para el sistema de retrieval híbrido.
Ajustado según metadata REAL de Qdrant de todos los providers:
- NFPA, FMDS, RNE, Gestion, ISO, SST, Medio Ambiente, ASIS
"""

# ============================================================================
# HYBRID SEARCH CONFIGURATION
# ============================================================================

HYBRID_SEARCH_CONFIG = {
    # Dense search parameters
    "dense": {
        "enabled": True,
        "weight": 0.40,              # Peso en fusión final (40%)
        "initial_top_k": 20,         # Recuperar más chunks inicialmente
        "model": "nomic-embed-text"
    },
    
    # Sparse search parameters (BM25)
    "sparse": {
        "enabled": True,
        "weight": 0.30,              # Peso en fusión final (30%)
        "k1": 1.5,                   # BM25 parameter (term frequency saturation)
        "b": 0.75,                   # BM25 parameter (length normalization)
        "use_keywords_manual": True,
        "use_text": True,
        "boost_exact_match": 2.0     # Multiplicador para matches exactos
    },
    
    # Metadata bonuses
    "metadata_bonuses": {
        "enabled": True,
        "total_weight": 0.30,        # Peso total de bonuses (30%)
        "legal_weight_bonus": 0.10,  # Normalizado de jerarquia_normativa
        "primary_source_bonus": 0.10,
        "level_bonus": 0.05,         # Artículo principal (level=1)
        "code_match_bonus": 0.05     # Código/norma mencionada en query
    },
    
    # Fusion method
    "fusion_method": "weighted_sum"  # "weighted_sum" | "rrf" | "dbsf"
}

# ============================================================================
# QUERY PARSER CONFIGURATION
# ============================================================================

QUERY_PARSER_CONFIG = {
    # Entity extraction
    "extract_norms": True,
    "extract_articles": True,
    "extract_chapters": True,
    "extract_sections": True,
    
    # Norm patterns (Regex) - COMPLETO con datos reales ✨
    "norm_patterns": {
        # ==================== LEYES PERUANAS ====================
        "ley": r"(?:LEY|Ley)\s+N?[°º]?\s*(\d+)",
        
        # ==================== DECRETOS ====================
        "decreto_supremo": r"D\.?\s?S\.?\s+N?[°º]?\s*(\d+-\d+-[A-Z]+)",
        "decreto_legislativo": r"D\.?\s?L\.?\s+N?[°º]?\s*(\d+)",
        "decreto_urgencia": r"D\.?\s?U\.?\s+N?[°º]?\s*(\d+)",
        
        # ==================== RESOLUCIONES ====================
        "resolucion_ministerial": r"R\.?\s?M\.?\s+(?:N?[°º]?\s*)?(\d+-\d+-[A-Z]+|\d+)",
        "resolucion_directoral": r"R\.?\s?D\.?\s+(?:N?[°º]?\s*)?(\d+-\d+-[A-Z]+|\d+)",
        "resolucion_consejo": r"R\.?C\.?D\.?\s+(?:N?[°º]?\s*)?(\d+-\d+-[A-Z\-]+|\d+)",
        "resolucion_jefatural": r"R\.?\s?J\.?\s+(?:N?[°º]?\s*)?(\d+-\d+-[A-Z]+|\d+)",
        "resolucion_presidencial": r"R\.?\s?P\.?\s+(?:N?[°º]?\s*)?(\d+-\d+-[A-Z]+|\d+)",
        "resolucion_suprema": r"R\.?\s?S\.?\s+(?:N?[°º]?\s*)?(\d+-\d+-[A-Z]+|\d+)",
        
        # ==================== ORDENANZAS ====================
        "ordenanza_metropolitana": r"O\.?M\.?\s+(?:N?[°º]?\s*)?(\d+)",
        "ordenanza": r"Ordenanza\s+N?[°º]?\s*(\d+)",
        
        # ==================== COMUNICADOS ====================
        "comunicado": r"Comunicado\s+(\d+)",
        
        # ==================== CONVENIOS ====================
        "convenio": r"Convenio\s+(\d+)",
        
        # ==================== DIRECTIVAS ====================
        "directiva": r"Directiva\s+(\d+)",
        
        # ==================== NORMAS TÉCNICAS INTERNACIONALES ====================
        "nfpa": r"NFPA\s*(\d+)",
        "iso": r"ISO\s*(\d+(?:-\d+)?)",  # ISO 9001 o ISO 9001-2015
        "astm": r"ASTM\s*([A-Z]\d+)",
        "asis": r"ASIS[- ]?([A-Z\-]+)",
        "asis_code": r"PROT-SEC-PHY-(\d+)",  # PROT-SEC-PHY-001
        
        # ==================== NORMAS TÉCNICAS NACIONALES (PERÚ) ====================
        "fmds": r"FMDS\s*(\d+)",
        "ntp": r"NTP\s*(\d+(?:\.\d+)?)",  # NTP 350.026
        
        # ==================== RNE (Reglamento Nacional de Edificación) ====================
        # Normas A (Arquitectura)
        "rne_a": r"(?:NORMA\s+)?A\.(\d+)",      # A.130, A.010
        
        # Normas E (Estructuras)
        "rne_e": r"(?:NORMA\s+)?E\.(\d+)",      # E.060, E.090
        
        # Normas IS (Instalaciones Sanitarias)
        "rne_is": r"(?:NORMA\s+)?IS\.(\d+)",    # IS.010
        
        # Normas TH (Habilitaciones)
        "rne_th": r"(?:NORMA\s+)?TH\.(\d+)",    # TH.020
        
        # Normas G (Generales)
        "rne_g": r"(?:NORMA\s+)?G\.(\d+)",      # G.040, G.050
        
        # Normas GE (Generales de Edificación)
        "rne_ge": r"(?:NORMA\s+)?GE\.(\d+)",    # GE.040
        
        # Normas GH (Generales de Habilitación)
        "rne_gh": r"(?:NORMA\s+)?GH\.(\d+)",    # GH.010
        
        # Normas OS (Obras de Saneamiento)
        "rne_os": r"(?:NORMA\s+)?OS\.(\d+)",    # OS.060, OS.090
        
        # Normas CE (Carreteras y Caminos)
        "rne_ce": r"(?:NORMA\s+)?CE\.(\d+)",    # CE.020, CE.040
        
        # Normas EC (Electricidad y Comunicaciones)
        "rne_ec": r"(?:NORMA\s+)?EC\.(\d+)",    # EC.010, EC.020
        
        # Normas EM (Instalaciones Electromecánicas)
        "rne_em": r"(?:NORMA\s+)?EM\.(\d+)",    # EM.030, EM.090
    },
    
    # Structure patterns
    "article_pattern": r"art[íi]culo\s+(\d+)",
    "chapter_pattern": r"cap[íi]tulo\s+(\d+|[IVXLCDM]+)",
    "section_pattern": r"secci[oó]n\s+(\d+\.?\d*)",
    
    # Stopwords (Spanish) - ampliados
    "stopwords": [
        "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o",
        "que", "por", "para", "con", "se", "es", "al", "su", "sus", "me",
        "te", "le", "nos", "les", "mi", "tu", "este", "esta", "estos", "estas",
        "cuál", "cuáles", "dónde", "cómo", "qué", "dice", "establece", "según",
        "sobre", "entre", "sin", "bajo", "ante", "hasta", "desde", "cuando",
        "más", "pero", "si", "no", "hay", "he", "ha", "han", "ser", "estar"
    ]
}

# ============================================================================
# FILTER BUILDER CONFIGURATION
# ============================================================================

FILTER_BUILDER_CONFIG = {
    # Filter strategy
    "use_should_filters": True,      # OR logic (más flexible)
    "use_must_filters": False,       # AND logic (más restrictivo)
    
    # Code variations
    "generate_code_variations": True,
    
    # Variation patterns - COMPLETO con datos reales ✨
    "code_variation_patterns": {
        # ==================== LEYES ====================
        "ley": [
            "Ley {num}", 
            "L. {num}", 
            "Ley N° {num}", 
            "Ley Nº {num}",
            "LEY N° {num}",
            "LEY {num}",
            "Ley {num:05d}",   # Ley 00123
            "Ley-{num}",
            "Ley_{num}",       # Variación con underscore
            "{num}"             # Solo el número
        ],
        
        # ==================== DECRETOS SUPREMOS ====================
        "decreto_supremo": [
            "DS {num}", 
            "D.S. {num}", 
            "Decreto Supremo {num}",
            "DS N° {num}",
            "D.S. N° {num}",
            "Decreto Supremo n° {num}",
            "DS-{num}",
            "DS_{num}",        # Variación con underscore
            "{num}"             # Solo el número
        ],
        
        # ==================== DECRETOS LEGISLATIVOS ====================
        "decreto_legislativo": [
            "DL {num}",
            "D.L. {num}",
            "Decreto Legislativo {num}",
            "DL N° {num}",
            "Decreto Legislativo n° {num}"
        ],
        
        # ==================== DECRETOS DE URGENCIA ====================
        "decreto_urgencia": [
            "DU {num}",
            "D.U. {num}",
            "Decreto de Urgencia {num}",
            "DU N° {num}"
        ],
        
        # ==================== RESOLUCIONES MINISTERIALES ====================
        "resolucion_ministerial": [
            "RM {num}", 
            "R.M. {num}", 
            "Resolución Ministerial {num}",
            "RM N° {num}",
            "Resolución Ministerial n° {num}"
        ],
        
        # ==================== RESOLUCIONES DIRECTORALES ====================
        "resolucion_directoral": [
            "RD {num}",
            "R.D. {num}",
            "Resolución Directoral {num}",
            "RD N° {num}"
        ],
        
        # ==================== RESOLUCIONES DE CONSEJO ====================
        "resolucion_consejo": [
            "RCD {num}",
            "R.C.D. {num}",
            "RCD N° {num}",
            "Resolución de Consejo Directivo {num}"
        ],
        
        # ==================== RESOLUCIONES JEFATURALES ====================
        "resolucion_jefatural": [
            "RJ {num}",
            "R.J. {num}",
            "Resolución Jefatural {num}",
            "RJ N° {num}"
        ],
        
        # ==================== RESOLUCIONES SUPREMAS ====================
        "resolucion_suprema": [
            "RS {num}",
            "R.S. {num}",
            "Resolución Suprema {num}",
            "RS N° {num}"
        ],
        
        # ==================== ORDENANZAS ====================
        "ordenanza": [
            "OM {num}",
            "O.M. {num}",
            "Ordenanza {num}",
            "Ordenanza Metropolitana {num}"
        ],
        
        # ==================== NFPA ====================
        "nfpa": [
            "NFPA {num}",
            "NFPA-{num}",
            "NFPA{num}",
            "NFPA_{num}",      # Variación con underscore
            "{num}"             # Solo el número (ej: "13")
        ],
        
        # ==================== ISO ====================
        "iso": [
            "ISO {num}",
            "ISO-{num}",
            "ISO{num}",
            "ISO_{num}",        # Variación con underscore
            "ISO {num}-{year}", # ISO 9001-2015
            "{num}"             # Solo el número (ej: "9001")
        ],
        
        # ==================== FMDS ====================
        "fmds": [
            "FMDS {num}",
            "FMDS{num}",
            "FMDS-{num}",
            "FMDS_{num}",      # Variación con underscore
            "FMDS {num:04d}",  # FMDS 0100
            "{num}"             # Solo el número
        ],
        
        # ==================== NTP ====================
        "ntp": [
            "NTP {num}",
            "NTP-{num}",
            "NTP{num}",
            "NTP_{num}",       # Variación con underscore
            "NTP {num}.{subnum}",  # NTP 350.026
            "{num}"             # Solo el número
        ],
        
        # ==================== RNE ====================
        "rne": [
            "A.{num}",
            "A{num}",
            "NORMA A.{num}",
            "NORMA A-{num}",
            "E.{num}",
            "E{num}",
            "NORMA E.{num}",
            "IS.{num}",
            "NORMA IS.{num}",
            "TH.{num}",
            "NORMA TH.{num}",
            "G.{num}",
            "NORMA G.{num}",
            "GE.{num}",
            "GH.{num}",
            "OS.{num}",
            "CE.{num}",
            "EC.{num}",
            "EM.{num}"
        ],
        
        # ==================== COMUNICADOS ====================
        "comunicado": [
            "Comunicado {num}",
            "Comunicado N° {num}"
        ],
        
        # ==================== DIRECTIVAS ====================
        "directiva": [
            "Directiva {num}",
            "Directiva N° {num}"
        ],
        
        # ==================== ASIS ====================
        "asis": [
            "PROT-SEC-PHY-{num}",
            "ASIS PROT-SEC-PHY-{num}"
        ]
    },
    
    # Thematic area mapping - COMPLETO con datos reales ✨
    "thematic_mapping": {
        # ==================== SEGURIDAD Y SALUD EN EL TRABAJO ====================
        "seguridad": "seguridad_salud_trabajo",
        "sst": "seguridad_salud_trabajo",
        "salud": "seguridad_salud_trabajo",
        "ocupacional": "seguridad_salud_trabajo",
        "trabajo": "seguridad_salud_trabajo",
        "laboral": "seguridad_salud_trabajo",
        "empleador": "seguridad_salud_trabajo",
        "trabajador": "seguridad_salud_trabajo",
        
        # ==================== PROTECCIÓN CONTRA INCENDIOS ====================
        "incendio": "proteccion_contra_incendios",
        "fuego": "proteccion_contra_incendios",
        "extintor": "proteccion_contra_incendios",
        "espuma": "proteccion_contra_incendios",
        "rociador": "proteccion_contra_incendios",
        "sprinkler": "proteccion_contra_incendios",
        "deteccion": "proteccion_contra_incendios",
        "alarma": "proteccion_contra_incendios",
        
        # ==================== CONSTRUCCIÓN Y EDIFICACIONES ====================
        "construccion": "construccion_edificaciones",
        "edificacion": "construccion_edificaciones",
        "edificio": "construccion_edificaciones",
        "estructura": "construccion_edificaciones",
        "concreto": "construccion_edificaciones",
        "cimentacion": "construccion_edificaciones",
        "albañileria": "construccion_edificaciones",
        "evacuacion": "construccion_edificaciones",
        
        # ==================== GESTIÓN DE CALIDAD ====================
        "calidad": "gestion_calidad",
        "iso9001": "gestion_calidad",
        "proceso": "gestion_calidad",
        "mejora": "gestion_calidad",
        
        # ==================== MEDIO AMBIENTE ====================
        "ambiental": "medio_ambiente",
        "ambiente": "medio_ambiente",
        "residuos": "medio_ambiente",
        "agua": "medio_ambiente",
        "contaminacion": "medio_ambiente",
        "recurso": "medio_ambiente",
        "forestal": "medio_ambiente",
        "aire": "medio_ambiente",
        
        # ==================== MINERÍA Y ENERGÍA ====================
        "mineria": "mineria_energia",
        "mina": "mineria_energia",
        "relaves": "mineria_energia",
        "energia": "mineria_energia",
        "electrica": "mineria_energia",
        "hidrocarburos": "mineria_energia"
    }
}

# ============================================================================
# METADATA RE-RANKING CONFIGURATION
# ============================================================================

RERANKING_CONFIG = {
    # Relevance thresholds
    "min_score_threshold": 0.50,     # Filtrar chunks con score < 0.40 (ajustado - era muy restrictivo)
    "high_relevance_threshold": 0.80,
    
    # Score normalization
    "normalize_scores": False,        # ✨ CAMBIADO: NO normalizar internamente (preserva ranking)
    "normalize_for_display": True,    # ✨ NUEVO: Solo normalizar al mostrar en UI - min()
    "max_score": 1.0,                 # Score máximo permitido (para evitar > 100% en display)
    
    # NOTA: Los boost factors pueden generar final_score > 1.0 (máximo ~3.5x)
    # Estrategia: NO normalizar internamente para preservar diferencias relativas
    # Solo normalizar al convertir a porcentaje en la UI

    # Deduplication
    "deduplicate": True,
    "dedup_key": "chunk_index",      # Evitar chunks duplicados del mismo doc
    
    # Boost factors - AJUSTADO según legal_weight real ✨
    # NOTA: Los boost factors pueden hacer que final_score > 1.0
    # Por eso se normaliza a max_score después de aplicar boosts
    "boost_factors": {
        "legal_hierarchy": {
            1: 1.50,   # Constitución (legal_weight: 1000)
            2: 1.45,   # Ley Orgánica (legal_weight: 900)
            3: 1.40,   # Ley Ordinaria (legal_weight: 800)
            4: 1.35,   # Decreto Supremo (legal_weight: 700)
            5: 1.30,   # Resolución Ministerial (legal_weight: 600)
            6: 1.25,   # Resolución Directoral (legal_weight: 500)
            7: 1.20,   # Norma Técnica Internacional (legal_weight: 400)
            8: 1.20,   # Norma Técnica Nacional (legal_weight: 400) - mismo peso
            9: 1.15    # Ficha Técnica (legal_weight: 300)
        },
        "document_level": {
            1: 1.3,   # Artículo principal
            2: 1.2,   # Capítulo
            3: 1.1,   # Sección
            4: 1.05,  # Subsección
            5: 1.0    # General
        },
        "is_primary_source": 1.2,
        "code_exact_match": 1.5
    }
}

# ============================================================================
# CONTEXT COMPOSER CONFIGURATION
# ============================================================================

CONTEXT_COMPOSER_CONFIG = {
    # Formatting
    "max_chunks": 10,
    "max_context_length": 8000,      # Caracteres totales de contexto
    "include_metadata": True,
    "group_by_document": True,
    
    # Citation format
    "citation_style": "structured",  # "structured" | "simple"
    "include_relevance_score": True,
    "include_source_hierarchy": True,
    
    # Deduplication
    "deduplicate_content": True,
    "similarity_threshold": 0.95     # Cosine similarity para detectar duplicados
}

# ============================================================================
# QUESTION TYPE SPECIFIC SETTINGS
# ============================================================================

QUESTION_TYPE_CONFIG = {
    "factual": {
        "top_k": 3,
        "min_score": 0.70,
        "prefer_primary_sources": True,
        "boost_exact_matches": True
    },
    "interpretative": {
        "top_k": 5,
        "min_score": 0.65,
        "prefer_primary_sources": False,
        "boost_exact_matches": False
    },
    "comparative": {
        "top_k": 6,
        "min_score": 0.65,
        "prefer_primary_sources": False,
        "boost_exact_matches": False
    },
    "procedural": {
        "top_k": 5,
        "min_score": 0.65,
        "prefer_primary_sources": True,
        "boost_exact_matches": True
    }
}


def get_retrieval_config():
    """Get complete retrieval configuration."""
    return {
        "hybrid_search": HYBRID_SEARCH_CONFIG,
        "query_parser": QUERY_PARSER_CONFIG,
        "filter_builder": FILTER_BUILDER_CONFIG,
        "reranking": RERANKING_CONFIG,
        "context_composer": CONTEXT_COMPOSER_CONFIG,
        "question_type": QUESTION_TYPE_CONFIG
    }


def get_question_type_settings(question_type: str) -> dict:
    """Get settings for specific question type."""
    return QUESTION_TYPE_CONFIG.get(
        question_type, 
        QUESTION_TYPE_CONFIG["interpretative"]  # Default
    )