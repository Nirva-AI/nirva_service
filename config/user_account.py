from pydantic import BaseModel


class UserAccount(BaseModel):
    username: str
    hashed_password: str


fake_user_account = UserAccount(
    username="wei",
    hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 明文是 secret
)
