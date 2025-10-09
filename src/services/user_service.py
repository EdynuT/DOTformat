"""Service for user registration and authentication."""
from __future__ import annotations
from typing import Optional
from ..repositories.user_repository import UserRepository
from ..utils.security import hash_password, verify_password

class UserService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    def has_users(self) -> bool:
        return self.repo.count_users() > 0

    def register(self, username: str, password: str) -> bool:
        if not username or not password:
            return False
        # Enforce minimum password length
        if len(password) < 6:
            return False
        if self.repo.find_by_username(username):
            return False
        pwd_hash = hash_password(password)
        # First user automatically becomes admin
        role = 'admin' if self.repo.is_first_user() else 'user'
        return self.repo.create(username, pwd_hash, role=role)

    def authenticate(self, username: str, password: str) -> bool:
        rec = self.repo.find_by_username(username)
        if not rec:
            return False
        # rec = (id, username, password_hash, role, created_at)
        pwd_hash = rec[2]
        return verify_password(password, pwd_hash)

    def get_role(self, username: str) -> Optional[str]:
        return self.repo.get_role(username)

__all__ = ["UserService"]
