"""Service for user registration, authentication, and admin management.

All business rules for account management (role changes, deletions, password
changes) live here so the UI layer only renders dialogs and calls this API.
"""
from __future__ import annotations
from typing import List, Optional, Tuple

from ..repositories.user_repository import UserRepository
from ..utils.security import hash_password, verify_password
from ..utils.envelope_key import create_and_store_wrapper


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

    def verify_password(self, username: str, password: str) -> bool:
        rec = self.repo.find_by_username(username)
        if not rec:
            return False
        return verify_password(password, rec[2])

    # --- Admin management -------------------------------------------------

    def list_users(self) -> List[Tuple]:
        return self.repo.list_all()

    def count_admins(self) -> int:
        return self.repo.count_admins()

    def first_admin_id(self) -> Optional[int]:
        return self.repo.first_user_id()

    def create_user_by_admin(self, username: str, password: str, confirm: str, k_app: Optional[bytes] = None) -> int:
        """Create a new user from the admin 'Create User' dialog.

        Returns the new user id. Raises ValueError on validation failure.
        """
        username = (username or "").strip()
        if not username or not password:
            raise ValueError("Fill all fields")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        if password != confirm:
            raise ValueError("Passwords do not match")
        if self.repo.find_by_username(username):
            raise ValueError("Username exists")
        if not self.register(username, password):
            raise ValueError("Failed to create user")
        rec = self.repo.find_by_username(username)
        user_id = rec[0]
        if k_app is not None:
            create_and_store_wrapper(user_id, password, k_app=k_app)
        return user_id

    def change_role(self, actor_username: str, target_user_id: int, admin_password: str) -> str:
        """Toggle a user's role between 'user' and 'admin'. Returns the new role.

        Raises ValueError/PermissionError describing why the change was rejected.
        """
        target = self.repo.find_by_id(target_user_id)
        if not target:
            raise ValueError("User not found")
        target_username, target_role = target[1], target[3]
        first_admin = self.repo.first_user_id()
        if target_user_id == first_admin:
            raise PermissionError("Cannot change the base admin.")
        if target_username == actor_username:
            raise PermissionError("You cannot change your own role.")
        if not self.verify_password(actor_username, admin_password):
            raise PermissionError("Password incorrect")
        new_role = 'admin' if target_role == 'user' else 'user'
        self.repo.update_role(target_user_id, new_role)
        return new_role

    def delete_user(self, actor_username: str, target_user_id: int, admin_password: str) -> None:
        target = self.repo.find_by_id(target_user_id)
        if not target:
            raise ValueError("User not found")
        target_username, target_role = target[1], target[3]
        first_admin = self.repo.first_user_id()
        if target_user_id == first_admin:
            raise PermissionError("Cannot delete the base admin.")
        if target_username == actor_username:
            raise PermissionError("Cannot delete the logged in user.")
        if target_role == 'admin' and self.repo.count_admins() == 1:
            raise PermissionError("Cannot delete the last admin.")
        if not self.verify_password(actor_username, admin_password):
            raise PermissionError("Password incorrect")
        self.repo.delete(target_user_id)

    def change_own_password(self, username: str, current_password: str, new_password: str, confirm: str,
                             k_app: Optional[bytes] = None) -> None:
        if not current_password or not new_password:
            raise ValueError("Fill fields")
        if len(new_password) < 6:
            raise ValueError("Password must be at least 6 characters")
        if new_password != confirm:
            raise ValueError("Passwords do not match")
        rec = self.repo.find_by_username(username)
        if not rec:
            raise ValueError("User not found")
        user_id, stored_hash = rec[0], rec[2]
        if not verify_password(current_password, stored_hash):
            raise ValueError("Current password incorrect")
        self.repo.update_password_hash(user_id, hash_password(new_password))
        if k_app is not None:
            create_and_store_wrapper(user_id, new_password, k_app=k_app)


__all__ = ["UserService"]
