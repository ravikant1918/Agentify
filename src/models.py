from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    message: str
    thread_id: Optional[str] = None