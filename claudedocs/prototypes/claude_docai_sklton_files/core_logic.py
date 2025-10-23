"""
Core Logic Service - Orchestrates all 5 OPMP phases
"""
from datetime import datetime
from typing import AsyncIterator, Dict, Any, Optional
from app.domain.models import ConversationState, ProcessingPhase, ErrorMessage
from app.services.phase1_query_understanding import Phase1QueryUnderstanding
from app.services.phase2_parallel_retrieval import Phase2ParallelRetrieval
from app.services.phase3_context_assembly import Phase3ContextAssembly
from app.services.phase4_response_generation import Phase4ResponseGeneration
from app.services.phase5_post_processing import Phase5PostProcessing
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


class CoreLogicService:
    """
    Core Logic Service - OPMP Pipeline Orchestrator
    
    Orchestrates the 5-phase pipeline:
    1. Query Understanding & Entity Extraction
    2. Parallel Multi-source Data Retrieval
    3. Context Assembly & Ranking
    4. Response Generation (Progressive Markdown)
    5. Post-processing & Formatting
    """
    
    def __init__(
        self,
        phase1: Phase1QueryUnderstanding,
        phase2: Phase2ParallelRetrieval,
        phase3: Phase3ContextAssembly,
        phase4: Phase4ResponseGeneration,
        phase5: Phase5PostProcessing
    ):
        """Initialize core logic service with all phase services"""
        self.phase1 = phase1
        self.phase2 = phase2
        self.phase3 = phase3
        self.phase4 = phase4
        self.phase5 = phase5
    
    async def chat_stream_progressive(
        self,
        query: str,
        session_id: str,
        available_modelnames: Optional[list] = None,
        available_modeltypes: Optional[list] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute full OPMP pipeline with progressive streaming
        
        Args:
            query: User query string
            session_id: Session identifier
            available_modelnames: Available product model names
            available_modeltypes: Available model types
            
        Yields:
            SSE messages for each phase progress and result
        """
        start_time = datetime.now()
        phase_timings: Dict[int, float] = {}
        
        # Initialize state
        state = ConversationState(
            session_id=session_id,
            query=query,
            current_phase=ProcessingPhase.PHASE_1_QUERY_UNDERSTANDING
        )
        
        try:
            # ========== PHASE 1: Query Understanding ==========
            phase1_start = datetime.now()
            analysis = None
            
            async for update in self.phase1.process(
                query=query,
                available_modelnames=available_modelnames,
                available_modeltypes=available_modeltypes
            ):
                yield update
                
                if update["type"] == "phase_result":
                    from app.domain.models import Phase1Analysis
                    analysis = Phase1Analysis(**update["data"])
                    state.phase1_result = analysis
            
            phase_timings[1] = (datetime.now() - phase1_start).total_seconds()
            
            if not analysis:
                raise Exception("Phase 1 failed to produce analysis")
            
            logger.info(f"Phase 1 completed in {phase_timings[1]:.2f}s")
            
            # ========== PHASE 2: Parallel Retrieval ==========
            state.current_phase = ProcessingPhase.PHASE_2_RETRIEVAL
            phase2_start = datetime.now()
            retrieval_results = None
            
            # Combine detected products
            detected_products = []
            if analysis.detected_products:
                detected_products.extend(analysis.detected_products)
            if analysis.detected_modeltypes:
                detected_products.extend(analysis.detected_modeltypes)
            
            async for update in self.phase2.retrieve(
                query=query,
                detected_products=detected_products if detected_products else None,
                top_k=30
            ):
                yield update
                
                if update["type"] == "phase_result":
                    from app.domain.models import Phase2RetrievalResults
                    retrieval_results = Phase2RetrievalResults(**update["data"])
                    state.phase2_result = retrieval_results
            
            phase_timings[2] = (datetime.now() - phase2_start).total_seconds()
            
            if not retrieval_results:
                raise Exception("Phase 2 failed: No results returned")
            
            if retrieval_results.total_semantic == 0 and retrieval_results.total_specs == 0:
                raise Exception("Phase 2 failed: No data retrieved from any source")
            
            logger.info(f"Phase 2 completed in {phase_timings[2]:.2f}s")
            
            # ========== PHASE 3: Context Assembly ==========
            state.current_phase = ProcessingPhase.PHASE_3_CONTEXT_ASSEMBLY
            phase3_start = datetime.now()
            context = None
            
            async for update in self.phase3.assemble(
                retrieval_results=retrieval_results,
                analysis=analysis
            ):
                yield update
                
                if update["type"] == "phase_result":
                    from app.domain.models import Phase3Context
                    context = Phase3Context(**update["data"])
                    state.phase3_result = context
            
            phase_timings[3] = (datetime.now() - phase3_start).total_seconds()
            
            if not context:
                raise Exception("Phase 3 failed: No context assembled")
            
            logger.info(f"Phase 3 completed in {phase_timings[3]:.2f}s")
            
            # ========== PHASE 4: Response Generation ==========
            state.current_phase = ProcessingPhase.PHASE_4_GENERATION
            phase4_start = datetime.now()
            generated_response = None
            
            async for update in self.phase4.generate(
                query=query,
                context=context,
                analysis=analysis
            ):
                yield update
                
                if update["type"] == "phase_result":
                    from app.domain.models import Phase4GeneratedResponse
                    generated_response = Phase4GeneratedResponse(**update["data"])
                    state.phase4_result = generated_response
            
            phase_timings[4] = (datetime.now() - phase4_start).total_seconds()
            
            if not generated_response:
                raise Exception("Phase 4 failed: No response generated")
            
            logger.info(f"Phase 4 completed in {phase_timings[4]:.2f}s")
            
            # ========== PHASE 5: Post-processing ==========
            state.current_phase = ProcessingPhase.PHASE_5_POSTPROCESSING
            phase5_start = datetime.now()
            
            async for update in self.phase5.process(
                query=query,
                generated_response=generated_response,
                context=context,
                analysis=analysis,
                phase_timings=phase_timings
            ):
                yield update
                
                if update["type"] == "complete":
                    from app.domain.models import Phase5ResponsePackage
                    state.phase5_result = Phase5ResponsePackage(**update["data"])
            
            phase_timings[5] = (datetime.now() - phase5_start).total_seconds()
            
            # Mark completion
            state.current_phase = ProcessingPhase.COMPLETED
            state.completed_at = datetime.now()
            
            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"[OPMP Pipeline] Complete in {total_time:.2f}s. "
                f"Phase times: {phase_timings}"
            )
            
        except Exception as e:
            logger.error(f"Error in OPMP pipeline: {e}", exc_info=True)
            state.current_phase = ProcessingPhase.ERROR
            state.error = str(e)
            
            # Send error message
            error_response = ErrorMessage(
                message=f"Processing error: {str(e)}",
                partial_results=True,
                phase_timings=phase_timings
            )
            yield error_response.model_dump()
