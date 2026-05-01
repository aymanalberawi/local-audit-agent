from sqlalchemy import Column, Integer, String, Text, ForeignKey
from models.base import Base

class AgentMemory(Base):
    """
    Stores vector embeddings of database schemas, API definitions, and past findings
    to provide the LLM agent with long-term semantic memory.
    """
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, index=True)

    # Company ID for multi-tenancy
    company_id = Column(Integer, ForeignKey("companies.id"))

    # Categorizes the memory: 'schema_table', 'api_endpoint', 'past_finding', etc.
    memory_type = Column(String, index=True)

    # The raw text content that the LLM will read
    content = Column(Text)

    # Mathematical representation of the content (stored as JSON array for now).
    # 384 dimensions matches the local 'all-MiniLM-L6-v2' model.
    # TODO: Replace with pgvector.sqlalchemy.Vector(384) when pgvector is properly configured
    embedding = Column(Text)  # Store as JSON string of embeddings array
