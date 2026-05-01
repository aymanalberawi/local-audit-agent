from langchain_ollama import ChatOllama

def get_audit_llm():
    """Connects to the local Qwen model in Docker."""
    return ChatOllama(
        model="qwen2.5-coder:7b",
        base_url="http://localhost:11434",
        temperature=0
    )