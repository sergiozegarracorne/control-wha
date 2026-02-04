from pydantic import BaseModel
from typing import List, Optional

class MessageSend(BaseModel):
    phone_number: str
    message: str
    image_path: Optional[str] = None

class MessageRead(BaseModel):
    meta: Optional[str] = None
    content: str
