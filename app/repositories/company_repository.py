from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.enums import Role, Status


class CompanyRepository:
    """
    Repositorio para operaciones CRUD sobre usuarios con rol COMPANY.
    Capa de acceso a datos.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, company_id: int) -> Optional[User]:
        """Obtener empresa por ID (solo usuarios con role = COMPANY)"""
        return (
            self.db.query(User)
            .filter(User.id == company_id, User.role == Role.COMPANY.value)
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Obtener todas las empresas"""
        return (
            self.db.query(User)
            .filter(User.role == Role.COMPANY.value)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(self, status: Status, skip: int = 0, limit: int = 100) -> List[User]:
        """Obtener empresas filtradas por status"""
        return (
            self.db.query(User)
            .filter(User.role == Role.COMPANY.value, User.status == status.value)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def approve(self, company: User) -> User:
        """Cambiar el status de una empresa a APPROVED"""
        company.status = Status.APPROVED.value
        self.db.commit()
        self.db.refresh(company)
        return company

    def reject(self, company: User) -> User:
        """Cambiar el status de una empresa a REJECTED"""
        company.status = Status.REJECTED.value
        self.db.commit()
        self.db.refresh(company)
        return company

    def get_by_id_any_status(self, company_id: int) -> Optional[User]:
        """Obtener empresa por ID sin importar su status (para verify-provider)"""
        return (
            self.db.query(User)
            .filter(User.id == company_id, User.role == Role.COMPANY.value)
            .first()
        )
