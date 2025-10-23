"""
Phase 3: Context Assembly & Ranking
Filters, ranks, and assembles context for LLM generation
"""
from datetime import datetime
from typing import AsyncIterator, Dict, Any, List
from app.domain.models import (
    Phase3Context, Phase2RetrievalResults, Phase1Analysis, 
    RankedProduct, ProgressMessage, PhaseResultMessage
)
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class Phase3ContextAssembly:
    """Phase 3: Context Assembly & Ranking Service"""
    
    def __init__(self, max_context_tokens: int = 8000):
        self.max_context_tokens = max_context_tokens
        self.avg_chars_per_token = 4  # Rough estimate
    
    async def assemble(
        self,
        retrieval_results: Phase2RetrievalResults,
        analysis: Phase1Analysis
    ) -> AsyncIterator[Dict[str, Any]]:
        """Assemble and rank context for generation"""
        phase_start = datetime.now()
        
        yield ProgressMessage(
            phase=3,
            message="Assembling and ranking context...",
            progress=45
        ).model_dump()
        
        # Rank products
        ranked_products = self._rank_products(
            retrieval_results.merged_products,
            analysis
        )
        
        # Filter by token limit
        filtered_products, truncated = self._filter_by_token_limit(ranked_products)
        
        processing_time = (datetime.now() - phase_start).total_seconds()
        
        context = Phase3Context(
            products=filtered_products,
            token_count=self._estimate_tokens(filtered_products),
            truncation_applied=truncated,
            original_count=len(ranked_products),
            kept_count=len(filtered_products),
            processing_time=processing_time
        )
        
        logger.info(f"Phase 3 completed: {len(filtered_products)}/{len(ranked_products)} products")
        
        yield PhaseResultMessage(
            phase=3,
            data=context.model_dump(),
            progress=60
        ).model_dump()
    
    def _rank_products(self, products: List, analysis: Phase1Analysis) -> List[RankedProduct]:
        """Rank products by relevance"""
        ranked = []
        for i, product in enumerate(products):
            score = product.semantic_score if product.semantic_score else 0.0
            
            # Boost score based on user focus
            if analysis.key_features:
                for feature in analysis.key_features:
                    if feature in product.specs:
                        score += 0.1
            
            ranked.append(RankedProduct(
                modelname=product.modelname,
                modeltype=product.modeltype,
                specs=product.specs,
                relevance_score=score,
                semantic_content=product.semantic_content,
                rank=i + 1
            ))
        
        ranked.sort(key=lambda x: x.relevance_score, reverse=True)
        return ranked
    
    def _filter_by_token_limit(self, products: List[RankedProduct]) -> tuple:
        """Filter products to fit token limit"""
        filtered = []
        current_tokens = 0
        
        for product in products:
            product_tokens = self._estimate_product_tokens(product)
            if current_tokens + product_tokens <= self.max_context_tokens:
                filtered.append(product)
                current_tokens += product_tokens
            else:
                break
        
        truncated = len(filtered) < len(products)
        return filtered, truncated
    
    def _estimate_tokens(self, products: List[RankedProduct]) -> int:
        """Estimate total tokens"""
        return sum(self._estimate_product_tokens(p) for p in products)
    
    def _estimate_product_tokens(self, product: RankedProduct) -> int:
        """Estimate tokens for a single product"""
        text = f"{product.modelname} {product.modeltype} "
        text += " ".join(f"{k}:{v}" for k, v in product.specs.items())
        return len(text) // self.avg_chars_per_token
