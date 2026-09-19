import React, { useState, useEffect } from 'react';
import { api } from './services/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [fileTree, setFileTree] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [indexStatus, setIndexStatus] = useState({ indexed: false, total_chunks: 0, status: 'idle' });
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Welcome to your GitHub AI Assistant! Select a repository to begin RAG code exploration, bug finding, and multi-agent reasoning.' }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [useRag, setUseRag] = useState(true);
  const [loadingAction, setLoadingAction] = useState(false);
  const [modalData, setModalData] = useState(null);
  const [showNewRepoModal, setShowNewRepoModal] = useState(false);
  const [newRepoForm, setNewRepoForm] = useState({ name: '', description: '', private: false, auto_init: true, auto_index: true });
  const [creatingRepo, setCreatingRepo] = useState(false);

  useEffect(() => {
    async function init() {
      try {
        const userData = await api.getUser();
        setUser(userData);
        const repos = await api.getRepositories();
        setRepositories(repos);
        if (repos.length > 0) {
          handleSelectRepo(repos[0]);
        }
      } catch (err) {
        console.error('Init error:', err);
      }
    }
    init();

    // Auto-sync polling every 20 seconds to detect newly created repositories
    const syncInterval = setInterval(async () => {
      try {
        const syncData = await api.getSyncStatus(true);
        if (syncData.has_new && syncData.new_repos_detected?.length > 0) {
          console.log('[React AutoSync] New repositories detected:', syncData.new_repos_detected);
          const updatedRepos = await api.getRepositories();
          setRepositories(updatedRepos);
          const found = updatedRepos.find(r => r.full_name === syncData.new_repos_detected[0]);
          if (found) {
            handleSelectRepo(found);
          }
        }
      } catch (e) {
        // silent catch
      }
    }, 20000);

    return () => clearInterval(syncInterval);
  }, []);

  const handleSelectRepo = async (repo) => {
    setSelectedRepo(repo);
    setActiveFile(null);
    const parts = repo.full_name.split('/');
    try {
      const [treeData, statusData] = await Promise.all([
        api.getFileTree(parts[0], parts[1], repo.default_branch),
        api.getIndexStatus(parts[0], parts[1])
      ]);
      setFileTree(treeData.tree || []);
      setIndexStatus(statusData);
    } catch (err) {
      console.error('Error fetching repo data:', err);
    }
  };

  const handleOpenFile = async (path) => {
    if (!selectedRepo) return;
    const parts = selectedRepo.full_name.split('/');
    try {
      const fileData = await api.getFileContent(parts[0], parts[1], path, selectedRepo.default_branch);
      setActiveFile(fileData);
    } catch (err) {
      console.error('Failed to open file:', err);
    }
  };

  const handleIndexRepo = async () => {
    if (!selectedRepo) return;
    const parts = selectedRepo.full_name.split('/');
    setIndexStatus(prev => ({ ...prev, status: 'indexing' }));
    try {
      const res = await api.indexRepository(parts[0], parts[1], selectedRepo.default_branch);
      setIndexStatus(res);
    } catch (err) {
      console.error('Indexing failed:', err);
      setIndexStatus(prev => ({ ...prev, status: 'idle' }));
    }
  };

  const handleSendMessage = async () => {
    if (!inputQuery.trim()) return;
    const query = inputQuery;
    setInputQuery('');
    const newHistory = [...chatMessages, { role: 'user', content: query }];
    setChatMessages(newHistory);

    const parts = selectedRepo ? selectedRepo.full_name.split('/') : [null, null];
    try {
      const res = await api.chat({
        owner: parts[0],
        repo: parts[1],
        message: query,
        history: newHistory.slice(-8),
        current_file_path: activeFile ? activeFile.path : null,
        current_file_content: activeFile ? activeFile.content : null,
        use_rag: useRag
      });

      // Automatic repository switching from AI context memory
      if (res.repo_switched && res.switched_repo) {
        const switched = res.switched_repo;
        let targetRepo = repositories.find(r => r.full_name.toLowerCase() === switched.full_name.toLowerCase());
        if (!targetRepo) {
          targetRepo = switched;
          setRepositories(prev => [switched, ...prev.filter(r => r.full_name !== switched.full_name)]);
        }
        await handleSelectRepo(targetRepo);
      }

      setChatMessages(prev => [
        ...prev,
        { 
          role: 'assistant', 
          content: res.answer, 
          sources: res.sources,
          switchedRepo: res.repo_switched && res.switched_repo ? res.switched_repo.full_name : null
        }
      ]);
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}` }
      ]);
    }
  };

  const handleCodeAction = async (action) => {
    if (!activeFile || !selectedRepo) return;
    const parts = selectedRepo.full_name.split('/');
    setLoadingAction(true);
    setModalData({ title: `AI Action: ${action}`, content: 'Analyzing with Groq...' });
    try {
      const res = await api.codeAction(parts[0], parts[1], activeFile.path, activeFile.content, action);
      setModalData({ title: `AI Analysis: ${action}`, content: res.analysis });
    } catch (err) {
      setModalData({ title: 'Error', content: err.message });
    } finally {
      setLoadingAction(false);
    }
  };

  const handleCreateRepoSubmit = async (e) => {
    e.preventDefault();
    if (!newRepoForm.name.trim()) return;
    setCreatingRepo(true);
    try {
      const res = await api.createRepository(newRepoForm);
      if (res.repository) {
        const updatedRepos = await api.getRepositories();
        setRepositories(updatedRepos);
        const created = updatedRepos.find(r => r.full_name === res.repository.full_name) || res.repository;
        handleSelectRepo(created);
        setShowNewRepoModal(false);
        setNewRepoForm({ name: '', description: '', private: false, auto_init: true, auto_index: true });
      }
    } catch (err) {
      alert('Failed to create repository: ' + err.message);
    } finally {
      setCreatingRepo(false);
    }
  };

  return (
    <div className="dark-theme" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="app-header">
        <div className="brand-logo">
          <div className="logo-icon">⚡</div>
          <div className="brand-text">
            <span className="brand-title">GitHub <span className="gradient-text">AI Assistant</span></span>
          </div>
        </div>

        <div className="header-center" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <select 
            className="repo-dropdown" 
            value={selectedRepo ? selectedRepo.full_name : ''}
            onChange={(e) => {
              const r = repositories.find(repo => repo.full_name === e.target.value);
              if (r) handleSelectRepo(r);
            }}
          >
            {repositories.map(r => (
              <option key={r.full_name} value={r.full_name}>{r.name}</option>
            ))}
          </select>
          <button 
            className="btn btn-secondary" 
            onClick={() => setShowNewRepoModal(true)}
            style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', border: 'none' }}
          >
            + New Repo
          </button>
          <button className="btn btn-secondary" onClick={handleIndexRepo}>
            🧠 {indexStatus.indexed ? `Indexed (${indexStatus.total_chunks})` : 'Index ChromaDB'}
          </button>
        </div>

        <div className="header-right">
          <div className="model-badge">
            <span className="model-dot"></span> Groq 120B
          </div>
          {user && (
            <div className="user-badge">
              <img src={user.avatar_url} alt={user.login} className="user-avatar" />
              <span className="user-login">{user.login}</span>
            </div>
          )}
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="main-workspace">
        <div className="workspace-left">
          <div className="file-browser-container">
            <div className="file-tree-sidebar">
              <div className="file-tree-list">
                {fileTree.filter(item => item.type === 'blob').slice(0, 100).map(item => (
                  <div
                    key={item.path}
                    className={`tree-item file ${activeFile && activeFile.path === item.path ? 'active' : ''}`}
                    onClick={() => handleOpenFile(item.path)}
                  >
                    <span>📄</span>
                    <span className="file-name">{item.path}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="code-viewer-panel">
              <div className="code-header">
                <span className="code-breadcrumb">📄 {activeFile ? activeFile.path : 'Select a file'}</span>
                {activeFile && (
                  <button className="btn-text-sm" onClick={() => navigator.clipboard.writeText(activeFile.content)}>
                    📋 Copy
                  </button>
                )}
              </div>

              {activeFile && (
                <div className="code-ai-toolbar">
                  <span className="toolbar-label">AI Actions:</span>
                  <button className="action-chip" onClick={() => handleCodeAction('explain')}>🔍 Explain</button>
                  <button className="action-chip highlight-chip" onClick={() => handleCodeAction('find_bugs')}>🐛 Find Bugs</button>
                  <button className="action-chip" onClick={() => handleCodeAction('generate_tests')}>🧪 Tests</button>
                  <button className="action-chip" onClick={() => handleCodeAction('optimize')}>⚡ Optimize</button>
                </div>
              )}

              <div className="code-editor-container">
                <pre><code>{activeFile ? activeFile.content : '// Select a file to inspect code and run AI diagnostics...'}</code></pre>
              </div>
            </div>
          </div>
        </div>

        {/* Right Workspace: Chat */}
        <aside className="workspace-right">
          <div className="chat-header">
            <h3 className="chat-heading">Repository AI Copilot</h3>
            <label className="rag-toggle">
              <input type="checkbox" checked={useRag} onChange={(e) => setUseRag(e.target.checked)} />
              <span className="toggle-slider"></span>
              <span className="toggle-text">RAG</span>
            </label>
          </div>

          <div className="chat-feed">
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`chat-msg ${msg.role}`}>
                <div className="msg-avatar">{msg.role === 'user' ? '👤' : '🤖'}</div>
                <div className="msg-bubble">
                  {msg.switchedRepo && (
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      background: 'rgba(56, 189, 248, 0.15)',
                      border: '1px solid rgba(56, 189, 248, 0.4)',
                      borderRadius: '6px',
                      padding: '4px 10px',
                      fontSize: '12px',
                      color: '#38bdf8',
                      marginBottom: '8px'
                    }}>
                      <span>🔄</span>
                      <span>Auto-selected repository: <strong>{msg.switchedRepo}</strong></span>
                    </div>
                  )}
                  <p style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', margin: '4px 0' }}>{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="source-citations">
                      <div className="citation-header">📚 Sources ({msg.sources.length}):</div>
                      {msg.sources.map((s, i) => (
                        <span key={i} className="citation-chip">📄 {s.file_path}:{s.chunk_index || 1}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Ultra-Modern AI Prompt / Type Bar */}
          <div className="chat-input-area">
            {/* Quick Suggestion Chips */}
            <div className="quick-suggestion-chips">
              <button 
                className="suggestion-chip" 
                onClick={() => { setInputQuery("what i have used for my_portfolio frontend"); }}
              >
                📦 Frontend in my_portfolio
              </button>
              <button 
                className="suggestion-chip" 
                onClick={() => { setInputQuery("Explain the overall architecture and data flow of this repository"); }}
              >
                🏛️ Architecture & Flow
              </button>
              <button 
                className="suggestion-chip" 
                onClick={() => { setInputQuery("Check this repository for potential bugs or security vulnerabilities"); }}
              >
                🛡️ Bug & Security Audit
              </button>
              <button 
                className="suggestion-chip" 
                onClick={() => { setInputQuery("Where is the main entry point and how does the application start?"); }}
              >
                🚀 Main Entrypoint
              </button>
            </div>

            {/* Floating Glassmorphic Type Bar */}
            <div className="modern-type-bar">
              {/* Context Row */}
              <div className="typebar-context-row">
                <span className="context-pill repo">
                  📁 {selectedRepo ? selectedRepo.name : 'All Repos Context'}
                </span>
                {activeFile && (
                  <span className="context-pill file">
                    📄 {activeFile.path.split('/').pop()}
                    <button 
                      className="pill-close" 
                      onClick={() => setActiveFile(null)} 
                      title="Detach file from prompt"
                    >
                      ×
                    </button>
                  </span>
                )}
                <span className={`context-pill ${useRag ? 'rag' : ''}`}>
                  🧠 RAG {useRag ? 'Active' : 'Off'}
                </span>
              </div>

              {/* Textarea Field */}
              <textarea
                className="typebar-input-field"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => { 
                  if (e.key === 'Enter' && !e.shiftKey) { 
                    e.preventDefault(); 
                    handleSendMessage(); 
                  } 
                }}
                placeholder="Ask about any repository, frontend stack, bugs, or code..."
                rows={1}
              />

              {/* Bottom Actions & Controls Row */}
              <div className="typebar-bottom-row">
                <div className="typebar-actions-left">
                  <button 
                    type="button" 
                    className="typebar-chip"
                    onClick={() => setInputQuery(prev => prev ? `Explain: ${prev}` : "Explain this repository")}
                  >
                    ✨ Explain
                  </button>
                  <button 
                    type="button" 
                    className="typebar-chip"
                    onClick={() => setInputQuery(prev => prev ? `Audit bugs in: ${prev}` : "Find bugs in this code")}
                  >
                    🐛 Bugs
                  </button>
                  <button 
                    type="button" 
                    className="typebar-chip"
                    onClick={() => setInputQuery(prev => prev ? `Tech stack for: ${prev}` : "What tech stack is used here?")}
                  >
                    📦 Stack
                  </button>
                </div>

                <div className="typebar-controls-right">
                  <span className="typebar-hint">
                    <kbd>Enter ↵</kbd> send
                  </span>
                  <button 
                    className="modern-send-btn" 
                    onClick={handleSendMessage}
                    disabled={!inputQuery.trim()}
                    title="Send message (Enter)"
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="22" y1="2" x2="11" y2="13"></line>
                      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

        </aside>
      </div>

      {/* Modal */}
      {modalData && (
        <div className="modal-overlay">
          <div className="modal-box modal-lg">
            <div className="modal-header">
              <h3>{modalData.title}</h3>
              <button className="modal-close" onClick={() => setModalData(null)}>×</button>
            </div>
            <div className="modal-body">
              <pre style={{ whiteSpace: 'pre-wrap' }}>{modalData.content}</pre>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => setModalData(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* New Repo Modal */}
      {showNewRepoModal && (
        <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="modal-box" style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '24px', width: '450px', maxWidth: '90vw' }}>
            <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc' }}>🚀 Create New Repository</h3>
              <button className="modal-close" onClick={() => setShowNewRepoModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '20px', cursor: 'pointer' }}>×</button>
            </div>
            <form onSubmit={handleCreateRepoSubmit}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', color: '#94a3b8', fontSize: '13px', marginBottom: '6px' }}>Repository Name *</label>
                <input
                  type="text"
                  value={newRepoForm.name}
                  onChange={(e) => setNewRepoForm({ ...newRepoForm, name: e.target.value })}
                  placeholder="e.g. nextgen-api"
                  required
                  style={{ width: '100%', padding: '8px 12px', background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#fff' }}
                />
              </div>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', color: '#94a3b8', fontSize: '13px', marginBottom: '6px' }}>Description</label>
                <input
                  type="text"
                  value={newRepoForm.description}
                  onChange={(e) => setNewRepoForm({ ...newRepoForm, description: e.target.value })}
                  placeholder="Short description..."
                  style={{ width: '100%', padding: '8px 12px', background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#fff' }}
                />
              </div>
              <div style={{ marginBottom: '14px', display: 'flex', gap: '16px', color: '#e2e8f0', fontSize: '14px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="reactRepoVis"
                    checked={!newRepoForm.private}
                    onChange={() => setNewRepoForm({ ...newRepoForm, private: false })}
                  />
                  Public
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="reactRepoVis"
                    checked={newRepoForm.private}
                    onChange={() => setNewRepoForm({ ...newRepoForm, private: true })}
                  />
                  Private 🔒
                </label>
              </div>
              <div style={{ marginBottom: '18px', display: 'flex', flexDirection: 'column', gap: '8px', color: '#94a3b8', fontSize: '13px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={newRepoForm.auto_init}
                    onChange={(e) => setNewRepoForm({ ...newRepoForm, auto_init: e.target.checked })}
                  />
                  Initialize with README.md
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: '#38bdf8' }}>
                  <input
                    type="checkbox"
                    checked={newRepoForm.auto_index}
                    onChange={(e) => setNewRepoForm({ ...newRepoForm, auto_index: e.target.checked })}
                  />
                  Auto-index in ChromaDB for instant RAG
                </label>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowNewRepoModal(false)}
                  style={{ padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={creatingRepo}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', border: 'none', cursor: 'pointer' }}
                >
                  {creatingRepo ? 'Creating...' : 'Create & Index'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
