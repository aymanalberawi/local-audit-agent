from sqlalchemy import Column, Integer, String, Text
from models.base import Base


class ApplicationSettings(Base):
    """Application-wide settings like LLM model selection."""
    __tablename__ = "application_settings"

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(255), unique=True, nullable=False)  # e.g., "llm_model"
    setting_value = Column(Text, nullable=False)  # e.g., "mistral:latest"
    description = Column(Text, nullable=True)  # e.g., "Selected LLM model for audits"

    def __repr__(self):
        return f"<ApplicationSettings {self.setting_key}={self.setting_value}>"
