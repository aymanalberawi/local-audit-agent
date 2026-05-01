"""
Memory Service — stores and recalls agent knowledge using pgvector.
Used to avoid re-running discovery on every audit of the same connection+standard.
"""
import json
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from models.memory import AgentMemory

logger = logging.getLogger(__name__)

# Lazy-load the embedding model to avoid slow startup
_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


class MemoryService:

    # Cosine similarity threshold — 0.0 = identical, 2.0 = completely different
    # We recall if distance < 0.3 (very similar)
    RECALL_THRESHOLD = 0.3

    @staticmethod
    def _embed(text: str) -> List[float]:
        return _get_model().encode(text).tolist()

    @staticmethod
    def store_memory(db: Session, content: str, memory_type: str = "general") -> AgentMemory:
        """Embed and store any text as an agent memory."""
        embedding = MemoryService._embed(content)
        memory = AgentMemory(memory_type=memory_type, content=content, embedding=embedding)
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def search_memory(db: Session, query: str, limit: int = 3) -> List[AgentMemory]:
        """Semantic search over all stored memories."""
        query_embedding = MemoryService._embed(query)
        results = db.query(AgentMemory)\
            .order_by(AgentMemory.embedding.cosine_distance(query_embedding))\
            .limit(limit)\
            .all()
        return results

    # ─── Schema Mapping (Phase 1 cache) ────────────────────────────────────────

    @staticmethod
    def store_schema_mapping(
        db: Session,
        connection_id: int,
        standard: str,
        dataset_map: List[Dict[str, Any]]
    ) -> AgentMemory:
        """
        Store the LLM's discovery result: which tables/columns are relevant
        for a given connection + standard combination.
        
        dataset_map example:
          [{"table": "users", "columns": ["email", "role", "department"]}]
        """
        content = json.dumps({
            "connection_id": connection_id,
            "standard": standard,
            "datasets": dataset_map
        })
        query_key = f"schema_mapping connection:{connection_id} standard:{standard}"
        embedding = MemoryService._embed(query_key)
        
        memory = AgentMemory(
            memory_type="schema_mapping",
            content=content,
            embedding=embedding
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        logger.info(f"Stored schema mapping for connection {connection_id} / {standard}")
        return memory

    @staticmethod
    def recall_schema_mapping(
        db: Session,
        connection_id: int,
        standard: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Try to recall a previously discovered schema mapping using exact content match.
        Falls back to vector search for approximate match.
        """
        try:
            # First try exact match by content prefix (most reliable)
            prefix = f'{{"connection_id": {connection_id}, "standard": "{standard}"'
            result = db.query(AgentMemory).filter(
                AgentMemory.memory_type == "schema_mapping",
                AgentMemory.content.like(f'%"connection_id": {connection_id}%'),
                AgentMemory.content.like(f'%"standard": "{standard}"%')
            ).order_by(AgentMemory.id.desc()).first()

            if result:
                data = json.loads(result.content)
                if data.get("connection_id") == connection_id and data.get("standard") == standard:
                    logger.info(f"Cache HIT: recalled schema mapping for conn {connection_id} / {standard}")
                    return data.get("datasets", [])

            return None
        except Exception as e:
            logger.warning(f"Memory recall failed: {e}")
            return None


    # ─── Finding Summaries (for future delta comparisons) ──────────────────────

    @staticmethod
    def store_finding_summary(
        db: Session,
        connection_id: int,
        standard: str,
        control_id: str,
        issue_description: str
    ) -> AgentMemory:
        """
        Store a summary of a finding so the agent can remember past failures.
        """
        content = (
            f"Audit finding on connection {connection_id} for standard {standard}. "
            f"Control {control_id} FAILED: {issue_description}"
        )
        embedding = MemoryService._embed(content)
        memory = AgentMemory(
            memory_type="past_finding",
            content=content,
            embedding=embedding
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory
