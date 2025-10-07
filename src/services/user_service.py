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
        if self.repo.find_by_username(username):
            return False
        pwd_hash = hash_password(password)
        return self.repo.create(username, pwd_hash)

    def authenticate(self, username: str, password: str) -> bool:
        rec = self.repo.find_by_username(username)
        if not rec:
            return False
        _id, _username, pwd_hash, _created = rec
        return verify_password(password, pwd_hash)

__all__ = ["UserService"]
