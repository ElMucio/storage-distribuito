from pydantic import BaseModel

class Register(BaseModel):
    username: str

class WriteRequest(BaseModel):
    username: str
    chunk_name: str
    chunk_data: str

class ReadRequest(BaseModel):
    username: str
    chunk_name: str

class DeleteRequest(BaseModel):
    username: str
    chunk_name: str