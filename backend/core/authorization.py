"""Authorization module for RBAC and multi-tenancy checks"""
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from models.user import User

# Define role hierarchy
ROLE_HIERARCHY = {
    "admin": ["admin", "auditor", "analyst"],
    "auditor": ["auditor", "analyst"],
    "analyst": ["analyst"]
}

def require_role(*allowed_roles):
    """Decorator to require specific roles"""
    async def role_checker(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
        # Get user from database to get current role
        user = db.query(User).filter(User.id == current_user.get("id")).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' does not have permission. Required roles: {allowed_roles}"
            )

        return user

    return role_checker


def check_company_access(user_id: int, target_company_id: int, db: Session):
    """Check if user has access to a company"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Only admins can access other companies' data
    if user.role == "admin":
        return user

    # Regular users can only access their own company
    if user.company_id != target_company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access data from this company"
        )

    return user


def get_current_user_full(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user with full details from database"""
    user = db.query(User).filter(User.email == current_user.get("email")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user
