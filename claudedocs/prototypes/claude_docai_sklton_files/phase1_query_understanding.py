"""
Phase 1: Query Understanding & Entity Extraction
Analyzes user queries, extracts intent, product models, and key features
"""
import re
import json
from datetime import datetime
from typing import AsyncIterator, Dict, Any, List, Optional
from app.domain.models import (
    Phase1Analysis, QueryIntent, ConfidenceLevel, Complexity,
    ProgressMessage, PhaseResultMessage
)
from app.llm_providers.openai_compat import OpenAICompatClient
from app.infra.cache import CacheInterface, create_cache_key
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


# Prompts for query understanding
QUERY_UNDERSTANDING_PROMPT = """Analyze the following user query and extract structured information.

User Query: {query}

Available Product Models: {available_models}
Available Model Types: {available_types}

Please provide a JSON response with the following structure:
{{
    "intent": "compare|recommend|spec_query|general_inquiry",
    "detected_products": ["list", "of", "product", "models"],
    "detected_modeltypes": ["list", "of", "model", "types"],
    "key_features": ["list", "of", "key", "features"],
    "user_focus": "main user concern (performance|price|portability|battery)",
    "complexity": "simple|medium|complex"
}}

Respond with ONLY the JSON object, no additional text."""


class Phase1QueryUnderstanding:
    """
    Phase 1: Query Understanding & Entity Extraction Service
    
    Responsibilities:
    - Analyze user intent
    - Extract product models and types
    - Identify key features
    - Determine query complexity
    - Provide confidence scoring
    """
    
    def __init__(
        self,
        llm_client: OpenAICompatClient,
        cache: Optional[CacheInterface] = None
    ):
        """
        Initialize Phase 1 service
        
        Args:
            llm_client: LLM client for deep analysis
            cache: Optional cache interface
        """
        self.llm_client = llm_client
        self.cache = cache
        
        # Regex patterns for fast extraction
        self.product_pattern = re.compile(r'\b(APX|AHP|AG|ARB|AMD|AB|AKK)\s*(\d{3,4})\b', re.IGNORECASE)
        self.modeltype_pattern = re.compile(r'\b(819|839|928|958|960|AC01)\b')
    
    async def process(
        self,
        query: str,
        available_modelnames: Optional[List[str]] = None,
        available_modeltypes: Optional[List[str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Process query through Phase 1 analysis pipeline
        
        Args:
            query: User query string
            available_modelnames: List of available product model names
            available_modeltypes: List of available model types
            
        Yields:
            Progress and result messages
        """
        phase_start = datetime.now()
        
        # Yield initial progress
        yield ProgressMessage(
            phase=1,
            message="Analyzing query intent and extracting entities...",
            progress=5
        ).model_dump()
        
        # Step 1: Check cache
        cache_key = create_cache_key("phase1", query)
        if self.cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info("Phase 1: Using cached analysis")
                cached_result["from_cache"] = True
                
                yield PhaseResultMessage(
                    phase=1,
                    data=cached_result,
                    progress=20
                ).model_dump()
                return
        
        yield ProgressMessage(
            phase=1,
            message="Running fast path extraction...",
            progress=10
        ).model_dump()
        
        # Step 2: Fast path extraction
        analysis = self._fast_path_extraction(query)
        
        if analysis.confidence == ConfidenceLevel.HIGH:
            logger.info("Phase 1: Fast path successful")
            
            # Cache result
            if self.cache:
                await self.cache.set(cache_key, analysis.model_dump(), ttl=300)
            
            yield PhaseResultMessage(
                phase=1,
                data=analysis.model_dump(),
                progress=20
            ).model_dump()
            return
        
        # Step 3: LLM-based deep analysis
        yield ProgressMessage(
            phase=1,
            message="Performing deep LLM analysis...",
            progress=15
        ).model_dump()
        
        analysis = await self._llm_extraction(
            query,
            available_modelnames or [],
            available_modeltypes or []
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - phase_start).total_seconds()
        analysis.processing_time = processing_time
        
        logger.info(f"Phase 1 completed in {processing_time:.2f}s")
        
        # Cache result
        if self.cache:
            await self.cache.set(cache_key, analysis.model_dump(), ttl=300)
        
        # Yield final result
        yield PhaseResultMessage(
            phase=1,
            data=analysis.model_dump(),
            progress=20
        ).model_dump()
    
    def _fast_path_extraction(self, query: str) -> Phase1Analysis:
        """
        Fast regex-based extraction for simple queries
        
        Args:
            query: User query string
            
        Returns:
            Phase1Analysis with extracted information
        """
        # Extract products
        product_matches = self.product_pattern.findall(query)
        detected_products = [f"{prefix}{num}" for prefix, num in product_matches]
        
        # Extract model types
        modeltype_matches = self.modeltype_pattern.findall(query)
        detected_modeltypes = list(set(modeltype_matches))
        
        # Determine intent based on keywords
        intent = self._infer_intent(query)
        
        # Extract key features
        key_features = self._extract_key_features(query)
        
        # Determine confidence
        confidence = ConfidenceLevel.HIGH if (detected_products or detected_modeltypes) else ConfidenceLevel.LOW
        
        # Determine complexity
        complexity = self._assess_complexity(query)
        
        return Phase1Analysis(
            intent=intent,
            detected_products=detected_products,
            detected_modeltypes=detected_modeltypes,
            key_features=key_features,
            user_focus=self._infer_user_focus(query),
            complexity=complexity,
            confidence=confidence,
            from_cache=False
        )
    
    async def _llm_extraction(
        self,
        query: str,
        available_models: List[str],
        available_types: List[str]
    ) -> Phase1Analysis:
        """
        LLM-based deep extraction for complex queries
        
        Args:
            query: User query string
            available_models: Available product model names
            available_types: Available model types
            
        Returns:
            Phase1Analysis with LLM-extracted information
        """
        try:
            prompt = QUERY_UNDERSTANDING_PROMPT.format(
                query=query,
                available_models=", ".join(available_models[:50]),  # Limit for token efficiency
                available_types=", ".join(available_types)
            )
            
            messages = [
                {"role": "system", "content": "You are an expert at analyzing product queries."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.llm_client.chat_completion(messages, temperature=0.3)
            
            # Parse JSON response
            parsed = json.loads(response.strip())
            
            return Phase1Analysis(
                intent=QueryIntent(parsed.get("intent", "general_inquiry")),
                detected_products=parsed.get("detected_products", []),
                detected_modeltypes=parsed.get("detected_modeltypes", []),
                key_features=parsed.get("key_features", []),
                user_focus=parsed.get("user_focus", "general"),
                complexity=Complexity(parsed.get("complexity", "medium")),
                confidence=ConfidenceLevel.HIGH,
                from_cache=False
            )
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Fallback to fast path
            return self._fast_path_extraction(query)
    
    def _infer_intent(self, query: str) -> QueryIntent:
        """Infer query intent from keywords"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["compare", "comparison", "vs", "versus", "差異", "比較"]):
            return QueryIntent.COMPARE
        elif any(word in query_lower for word in ["recommend", "suggest", "best", "推薦", "建議"]):
            return QueryIntent.RECOMMEND
        elif any(word in query_lower for word in ["spec", "specification", "feature", "規格", "特性"]):
            return QueryIntent.SPEC_QUERY
        else:
            return QueryIntent.GENERAL_INQUIRY
    
    def _extract_key_features(self, query: str) -> List[str]:
        """Extract key features mentioned in query"""
        feature_keywords = {
            "cpu": ["cpu", "processor", "處理器"],
            "gpu": ["gpu", "graphics", "顯卡"],
            "memory": ["memory", "ram", "記憶體"],
            "storage": ["storage", "ssd", "儲存"],
            "battery": ["battery", "續航", "電池"],
            "display": ["display", "screen", "螢幕"],
            "weight": ["weight", "portable", "重量", "攜帶"],
            "price": ["price", "cost", "價格", "價錢"]
        }
        
        query_lower = query.lower()
        features = []
        
        for feature, keywords in feature_keywords.items():
            if any(kw in query_lower for kw in keywords):
                features.append(feature)
        
        return features
    
    def _infer_user_focus(self, query: str) -> str:
        """Infer user's main focus"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["performance", "fast", "speed", "效能", "速度"]):
            return "performance"
        elif any(word in query_lower for word in ["price", "cost", "budget", "價格", "預算"]):
            return "price"
        elif any(word in query_lower for word in ["portable", "light", "weight", "攜帶", "輕"]):
            return "portability"
        elif any(word in query_lower for word in ["battery", "續航", "電池"]):
            return "battery"
        else:
            return "general"
    
    def _assess_complexity(self, query: str) -> Complexity:
        """Assess query complexity based on structure"""
        # Simple heuristics
        word_count = len(query.split())
        has_multiple_products = len(self.product_pattern.findall(query)) > 1
        has_multiple_features = len(self._extract_key_features(query)) > 2
        
        if word_count < 10 and not has_multiple_products:
            return Complexity.SIMPLE
        elif word_count < 30 and (has_multiple_products or has_multiple_features):
            return Complexity.MEDIUM
        else:
            return Complexity.COMPLEX
