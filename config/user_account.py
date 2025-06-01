from pydantic import BaseModel


class UserAccount(BaseModel):
    username: str
    hashed_password: str
    display_name: str


fake_user_account = UserAccount(
    username="weilyupku@gmail.com",
    hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 明文是 secret
    display_name="wei",
)
