from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.authorization import get_current_user_full
from models.user import User
from models.settings import ApplicationSettings
from typing import Dict, List
import subprocess

router = APIRouter(prefix="/settings", tags=["Settings"])


def get_available_models() -> List[str]:
    """Get list of available models from Ollama."""
    try:
        result = subprocess.run(
            ["docker", "exec", "ollama", "ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            models = []
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
            return sorted(models)
    except Exception as e:
        print(f"Error getting models: {e}")

    # Fallback to known models if docker exec fails
    return ["llama2:latest", "neural-chat:latest", "qwen2.5-coder:7b", "qwen2.5-coder:32b"]


def get_setting(db: Session, key: str, default: str = None) -> str:
    """Get a setting value from database."""
    setting = db.query(ApplicationSettings).filter(
        ApplicationSettings.setting_key == key
    ).first()
    return setting.setting_value if setting else default


def set_setting(db: Session, key: str, value: str, description: str = None) -> ApplicationSettings:
    """Set a setting value in database."""
    setting = db.query(ApplicationSettings).filter(
        ApplicationSettings.setting_key == key
    ).first()

    if setting:
        setting.setting_value = value
    else:
        setting = ApplicationSettings(
            setting_key=key,
            setting_value=value,
            description=description
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


@router.get("/llm-models")
async def get_llm_models(
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Get list of available LLM models."""
    available_models = get_available_models()
    current_model = get_setting(db, "llm_model", "mistral:latest")

    return {
        "available_models": available_models,
        "current_model": current_model,
        "model_info": {
            "llama2:latest": {"size": "7B", "speed": "⚡ Fast", "quality": "Good"},
            "neural-chat:latest": {"size": "7B", "speed": "⚡ Fast", "quality": "Good"},
            "qwen2.5-coder:7b": {"size": "7B", "speed": "🐌 Slow", "quality": "Best"},
            "qwen2.5-coder:32b": {"size": "32B", "speed": "🐢 Very Slow", "quality": "Excellent"},
        }
    }


@router.post("/llm-model")
async def set_llm_model(
    model: str,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Set the LLM model to use for audits."""
    if not current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Only admins can change settings")

    available_models = get_available_models()
    if model not in available_models:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not found. Available: {', '.join(available_models)}"
        )

    set_setting(db, "llm_model", model, "Selected LLM model for audits")

    return {
        "success": True,
        "message": f"LLM model changed to {model}",
        "model": model
    }


@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Get all application settings."""
    settings = db.query(ApplicationSettings).all()
    return {
        setting.setting_key: setting.setting_value
        for setting in settings
    }
