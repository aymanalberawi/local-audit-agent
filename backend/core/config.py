from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GCC Audit SaaS"
    # Use Docker service names instead of localhost for container-to-container communication
    DATABASE_URL: str = "postgresql://admin:password@db:5432/audit_saas"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "super_secret_temporary_key_for_development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    OLLAMA_URL: str = "http://ollama:11434"  # Use containerized URL, not host.docker.internal
    OLLAMA_MODEL: str = "llama2:latest"  # Default to commonly available model

    class Config:
        env_file = ".env"

settings = Settings()

