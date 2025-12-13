from pydantic import BaseModel

class RegisterModel(BaseModel):
    username: str
    password: str
    full_name: str
    email: str

class TaskCreate(BaseModel):
    pass
