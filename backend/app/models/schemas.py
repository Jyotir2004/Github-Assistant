from typing import List, Optional, Dict, Any
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    login: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int = 0
    total_private_repos: Optional[int] = 0

class RepositoryItem(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool = False
    html_url: str
    default_branch: str = "main"
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    updated_at: Optional[str] = None

class FileItem(BaseModel):
    path: str
    mode: Optional[str] = None
    type: str  # "blob" (file) or "tree" (dir)
    sha: Optional[str] = None
    size: Optional[int] = None
    url: Optional[str] = None

class FileTreeResponse(BaseModel):
    owner: str
    repo: str
    branch: str
    tree: List[FileItem]
    truncated: bool = False

class FileContentResponse(BaseModel):
    path: str
    name: str
    content: str
    size: int
    language: str
    encoding: str = "utf-8"

class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant' | 'system'
    content: str

class ChatRequest(BaseModel):
    owner: str
    repo: str
    message: str
    branch: Optional[str] = "main"
    history: Optional[List[ChatMessage]] = Field(default_factory=list)
    current_file_path: Optional[str] = None
    current_file_content: Optional[str] = None
    use_rag: bool = True
    model: Optional[str] = None

class RetrievedContext(BaseModel):
    file_path: str
    chunk_index: int
    score: float
    snippet: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[RetrievedContext] = Field(default_factory=list)
    model_used: str

class IndexRepoRequest(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None
    max_files: Optional[int] = 60

class IndexStatusResponse(BaseModel):
    owner: str
    repo: str
    indexed: bool
    total_files: int = 0
    total_chunks: int = 0
    last_indexed_at: Optional[str] = None
    status: str = "idle"  # idle | indexing | ready | error
    error_message: Optional[str] = None

class CodeActionRequest(BaseModel):
    owner: str
    repo: str
    file_path: str
    code: str
    action: str = Field(..., description="'explain' | 'find_bugs' | 'generate_tests' | 'optimize' | 'docstring'")
    custom_instructions: Optional[str] = None

class CodeActionResponse(BaseModel):
    action: str
    file_path: str
    analysis: str
    suggestions: Optional[List[str]] = Field(default_factory=list)
    improved_code: Optional[str] = None

class DocGenRequest(BaseModel):
    owner: str
    repo: str
    doc_type: str = Field("readme", description="'readme' | 'architecture' | 'contributing' | 'api_docs'")
    include_badges: bool = True

class DocGenResponse(BaseModel):
    doc_type: str
    markdown_content: str

class IssuePrItem(BaseModel):
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    html_url: str
    user: Dict[str, Any]
    labels: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str
    is_pr: bool = False

class AnalyzeIssueRequest(BaseModel):
    owner: str
    repo: str
    number: int
    is_pr: bool = False

class AppConfigUpdate(BaseModel):
    github_token: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None

class CommitFileRequest(BaseModel):
    owner: str
    repo: str
    path: str
    content: str
    message: str
    branch: Optional[str] = "main"

class CreateBranchRequest(BaseModel):
    owner: str
    repo: str
    new_branch: str
    from_branch: Optional[str] = "main"

class CreatePrRequest(BaseModel):
    owner: str
    repo: str
    title: str
    body: str
    head: str
    base: Optional[str] = "main"

class PostCommentRequest(BaseModel):
    owner: str
    repo: str
    issue_number: int
    comment: str

class CreateIssueRequest(BaseModel):
    owner: str
    repo: str
    title: str
    body: str
    labels: Optional[List[str]] = Field(default_factory=list)

class CreateRepoRequest(BaseModel):
    name: str = Field(..., description="Repository name")
    description: Optional[str] = Field(None, description="Repository description")
    private: bool = Field(False, description="Whether the repository is private")
    auto_init: bool = Field(True, description="Whether to initialize with a README")
    auto_index: bool = Field(True, description="Automatically index in ChromaDB after creation")

class SyncStatusResponse(BaseModel):
    total_repos: int = 0
    new_repos_detected: List[str] = Field(default_factory=list)
    auto_indexed: List[str] = Field(default_factory=list)
    last_sync_time: Optional[str] = None
    has_new: bool = False
    is_watcher_running: bool = False
    error: Optional[str] = None

