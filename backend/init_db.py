"""Database initialization script"""
from core.database import engine, SessionLocal
from models.base import Base
from models.user import User
from models.hierarchy import Company
from models.audit_scheme import AuditScheme
from models.settings import ApplicationSettings
from core.security import get_password_hash
from services.standards_service import StandardsService
from sqlalchemy import text
import models.hierarchy
import models.audit
import models.schedule
import models.audit_scheme
import models.settings

def init_database():
    """Initialize database tables and seed data"""
    print("Enabling pgvector extension...")
    db = SessionLocal()
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.commit()
        print("pgvector extension enabled")
    except Exception as e:
        print(f"Note: pgvector extension might not be available: {e}")
        db.rollback()
    finally:
        db.close()

    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")

    print("Creating default company and admin user...")
    db = SessionLocal()
    try:
        # Create default company if it doesn't exist
        company = db.query(Company).filter(Company.id == 1).first()
        if not company:
            company = Company(id=1, name="Default Company")
            db.add(company)
            db.commit()
            print("Default company created")

        # Check if admin exists
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            admin_user = User(
                email="admin@example.com",
                hashed_password=get_password_hash("password"),
                company_id=1,
                is_active=True,
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            print("Admin user created: admin@example.com / password")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating company/admin user: {e}")
        db.rollback()
    finally:
        db.close()

    print("Initializing application settings...")
    db = SessionLocal()
    try:
        # Check if default LLM model setting exists
        llm_model_setting = db.query(ApplicationSettings).filter(
            ApplicationSettings.setting_key == "llm_model"
        ).first()

        if not llm_model_setting:
            default_model = ApplicationSettings(
                setting_key="llm_model",
                setting_value="llama2:latest",
                description="Selected LLM model for audits"
            )
            db.add(default_model)
            db.commit()
            print("Default LLM model setting created: llama2:latest")
        else:
            print(f"LLM model setting already exists: {llm_model_setting.setting_value}")
    except Exception as e:
        print(f"Error initializing application settings: {e}")
        db.rollback()
    finally:
        db.close()

    print("Initializing audit standards from JSON files...")
    db = SessionLocal()
    try:
        stats = StandardsService.initialize_from_json(db)
        print(f"Standards initialization complete:")
        print(f"  ✓ Imported: {stats['imported']}")
        print(f"  ⊘ Errors: {len(stats['errors'])}")
        if stats['errors']:
            for error in stats['errors']:
                print(f"    - {error}")
    except Exception as e:
        print(f"Error initializing standards: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
