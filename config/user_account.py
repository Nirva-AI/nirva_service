from pydantic import BaseModel
from typing import List


# 04-19-01.txt
# 04-19-02.txt
# 04-19-03.txt
# 05-09-01.txt
# 05-09-02.txt


class UserAccount(BaseModel):
    username: str
    hashed_password: str
    display_name: str
    data: List[str]


FAKE_USER = UserAccount(
    username="weilyupku@gmail.com",
    hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 明文是 secret
    display_name="wei",
    data=[
        "04-19-01.txt",
        "04-19-02.txt",
        "04-19-03.txt",
        "05-09-01.txt",
        "05-09-02.txt",
    ],
)
