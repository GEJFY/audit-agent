"""認証スキーマ"""

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    is_active: bool
