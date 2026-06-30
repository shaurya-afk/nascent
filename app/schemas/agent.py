from pydantic import BaseModel

class StartAgentRequest(BaseModel):
    repo_url: str
    user_query: str

class ResumeAgentRequest(BaseModel):
    thread_id: str
    action: str
    feedback: str