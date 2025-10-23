"""
Phase 5: Post-processing & Formatting
Final response assembly, quality checks, and source attribution
"""
from datetime import datetime
from typing import AsyncIterator, Dict, Any, List
from app.domain.models import (
    Phase5ResponsePackage, Phase4GeneratedResponse, Phase3Context,
    Phase1Analysis, ResponseMetadata, ResponseSource, QualityMetrics,
    CompleteMessage, ProgressMessage
)
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class Phase5PostProcessing:
    """
    Phase 5: Post-processing & Formatting Service
    
    Responsibilities:
    - Validate markdown structure
    - Extract and attribute sources
    - Calculate quality metrics
    - Assemble final response package
    """
    
    async def process(
        self,
        query: str,
        generated_response: Phase4GeneratedResponse,
        context: Phase3Context,
        analysis: Phase1Analysis,
        phase_timings: Dict[int, float]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Post-process generated response"""
        phase_start = datetime.now()
        
        yield ProgressMessage(
            phase=5,
            message="Post-processing and formatting...",
            progress=85
        ).model_dump()
        
        # Validate and enhance markdown
        processed_response = self._validate_markdown(generated_response.response)
        
        # Extract sources
        sources = self._extract_sources(context)
        
        # Calculate quality metrics
        quality = self._assess_quality(
            response=processed_response,
            context=context,
            sources=sources
        )
        
        # Build metadata
        processing_time = (datetime.now() - phase_start).total_seconds()
        phase_timings[5] = processing_time
        
        metadata = ResponseMetadata(
            model=generated_response.model_used,
            timestamp=datetime.now(),
            phase_timings=phase_timings,
            total_time=sum(phase_timings.values())
        )
        
        # Assemble final package
        response_package = Phase5ResponsePackage(
            response=processed_response,
            metadata=metadata,
            sources=sources,
            query=query,
            timestamp=datetime.now(),
            quality=quality
        )
        
        logger.info(
            f"Phase 5 completed in {processing_time:.2f}s, "
            f"quality score: {quality.score:.1f}"
        )
        
        # Yield complete message
        yield CompleteMessage(
            phase=5,
            data=response_package.model_dump(),
            progress=100
        ).model_dump()
    
    def _validate_markdown(self, response: str) -> str:
        """Validate and fix markdown structure"""
        lines = response.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Ensure proper spacing around headers
            if line.startswith('#'):
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append('')
                fixed_lines.append(line)
                fixed_lines.append('')
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _extract_sources(self, context: Phase3Context) -> List[ResponseSource]:
        """Extract source attributions"""
        sources = []
        for product in context.products:
            source = ResponseSource(
                product_id=product.modeltype,
                product_name=product.modelname,
                source_type="database",
                relevance_score=product.relevance_score
            )
            sources.append(source)
        return sources
    
    def _assess_quality(
        self,
        response: str,
        context: Phase3Context,
        sources: List[ResponseSource]
    ) -> QualityMetrics:
        """Assess response quality"""
        warnings = []
        metrics = {
            "response_length": len(response),
            "has_markdown_header": "##" in response or "#" in response,
            "has_markdown_bold": "**" in response,
            "has_markdown_table": "|" in response,
            "source_count": len(sources)
        }
        
        # Calculate quality score
        score = 100.0
        
        if metrics["response_length"] < 100:
            warnings.append("Response is very short")
            score -= 20
        
        if not metrics["has_markdown_header"]:
            warnings.append("No markdown headers found")
            score -= 10
        
        if metrics["source_count"] == 0:
            warnings.append("No sources attributed")
            score -= 15
        
        passed = score >= 60.0
        
        return QualityMetrics(
            score=score,
            warnings=warnings,
            metrics=metrics,
            passed=passed
        )
