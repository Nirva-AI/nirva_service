from pydantic import BaseModel


class UserAccount(BaseModel):
    username: str
    password: str


simu_test_user_account = UserAccount(
    username="wei",
    password="12345678",
)
