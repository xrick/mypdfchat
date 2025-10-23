"""
Phase 4: Response Generation (Progressive Markdown Streaming)
Generates LLM response with optimistic progressive markdown parsing
"""
from datetime import datetime
from typing import AsyncIterator, Dict, Any, List
from app.domain.models import (
    Phase4GeneratedResponse, Phase3Context, Phase1Analysis,
    MarkdownTokenMessage, PhaseResultMessage, ProgressMessage
)
from app.llm_providers.openai_compat import OpenAICompatClient
from app.infra.cache import CacheInterface, create_cache_key
from app.infra.logging import setup_logger

logger = setup_logger(__name__)


GENERATION_PROMPT = """You are a helpful product assistant. Based on the following context and user query, provide a comprehensive response in Markdown format.

User Query: {query}

Context:
{context}

User Intent: {intent}
User Focus: {user_focus}

Please provide a well-structured response using Markdown formatting:
- Use headers (##) for sections
- Use **bold** for emphasis
- Use bullet points for lists
- Use tables if comparing multiple products
- Include specific data from the context

Response:"""


class Phase4ResponseGeneration:
    """
    Phase 4: Response Generation with Progressive Markdown Streaming
    
    Implements OPMP (Optimistic Progressive Markdown Parsing) for smooth UX
    """
    
    def __init__(
        self,
        llm_client: OpenAICompatClient,
        cache: Optional[CacheInterface] = None
    ):
        self.llm_client = llm_client
        self.cache = cache
    
    async def generate(
        self,
        query: str,
        context: Phase3Context,
        analysis: Phase1Analysis
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate response with progressive streaming"""
        phase_start = datetime.now()
        
        yield ProgressMessage(
            phase=4,
            message="Generating response...",
            progress=65
        ).model_dump()
        
        # Check cache
        cache_key = create_cache_key("phase4", query, context.token_count)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info("Phase 4: Using cached response")
                # Stream cached response token by token for UX
                for token in self._split_into_tokens(cached["response"]):
                    yield MarkdownTokenMessage(
                        token=token,
                        phase=4,
                        from_cache=True
                    ).model_dump()
                
                yield PhaseResultMessage(
                    phase=4,
                    data=cached,
                    progress=80
                ).model_dump()
                return
        
        # Build prompt
        context_str = self._build_context_string(context)
        prompt = GENERATION_PROMPT.format(
            query=query,
            context=context_str,
            intent=analysis.intent.value,
            user_focus=analysis.user_focus
        )
        
        messages = [
            {"role": "system", "content": "You are a knowledgeable product expert."},
            {"role": "user", "content": prompt}
        ]
        
        # Progressive streaming generation
        full_response = ""
        token_count = 0
        
        try:
            async for token in self.llm_client.chat_completion_stream(messages):
                full_response += token
                token_count += 1
                
                # Yield each token for OPMP rendering
                yield MarkdownTokenMessage(
                    token=token,
                    phase=4
                ).model_dump()
        
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            # Fallback to non-streaming
            full_response = await self.llm_client.chat_completion(messages)
            for token in self._split_into_tokens(full_response):
                yield MarkdownTokenMessage(token=token, phase=4).model_dump()
        
        generation_time = (datetime.now() - phase_start).total_seconds()
        
        result = Phase4GeneratedResponse(
            response=full_response,
            tokens_generated=token_count,
            generation_time=generation_time,
            model_used=self.llm_client.config.model
        )
        
        logger.info(f"Phase 4 completed in {generation_time:.2f}s, {token_count} tokens")
        
        # Cache result
        if self.cache:
            await self.cache.set(cache_key, result.model_dump(), ttl=1800)
        
        yield PhaseResultMessage(
            phase=4,
            data=result.model_dump(),
            progress=80
        ).model_dump()
    
    def _build_context_string(self, context: Phase3Context) -> str:
        """Build context string from products"""
        lines = []
        for product in context.products:
            lines.append(f"\n### {product.modelname} ({product.modeltype})")
            for key, value in product.specs.items():
                lines.append(f"- {key}: {value}")
            if product.semantic_content:
                lines.append(f"Additional info: {product.semantic_content[:200]}")
        return "\n".join(lines)
    
    def _split_into_tokens(self, text: str, chunk_size: int = 3) -> List[str]:
        """Split text into small tokens for progressive rendering"""
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
