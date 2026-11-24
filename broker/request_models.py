from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    psw: str

class RegisterRequest(BaseModel):
    username: str
    psw: str

class DeleteRequest(BaseModel):
    filename: str