/**
 * GitHub AI Assistant — Client Application Logic
 */

// Global State
const state = {
  user: null,
  repositories: [],
  selectedRepo: null,      // { owner, name, full_name, default_branch, ... }
  fileTree: [],            // List of file objects
  activeFile: null,        // { path, content, language }
  chatHistory: [],         // [ { role, content } ]
  config: {},
  isStreaming: false
};

// DOM Elements
const repoSelect = document.getElementById('repoSelect');
const refreshReposBtn = document.getElementById('refreshReposBtn');
const indexRepoBtn = document.getElementById('indexRepoBtn');
const indexStatusPill = document.getElementById('indexStatusPill');
const indexBtnText = document.getElementById('indexBtnText');

const repoFullName = document.getElementById('repoFullName');
const repoDescription = document.getElementById('repoDescription');
const repoStatsPills = document.getElementById('repoStatsPills');
const statStars = document.getElementById('statStars');
const statForks = document.getElementById('statForks');
const statBranch = document.getElementById('statBranch');
const statLanguage = document.getElementById('statLanguage');
const statChunks = document.getElementById('statChunks');

const fileTreeList = document.getElementById('fileTreeList');
const fileSearchInput = document.getElementById('fileSearchInput');
const activeFilePath = document.getElementById('activeFilePath');
const codeBlock = document.getElementById('codeBlock');
const copyCodeBtn = document.getElementById('copyCodeBtn');

const chatFeed = document.getElementById('chatFeed');
const chatInput = document.getElementById('chatInput');
const sendChatBtn = document.getElementById('sendChatBtn');
const clearChatBtn = document.getElementById('clearChatBtn');
const ragToggle = document.getElementById('ragToggle');
const activeFileIndicator = document.getElementById('activeFileIndicator');
const attachedFileName = document.getElementById('attachedFileName');
const detachFileBtn = document.getElementById('detachFileBtn');

// Modals
const actionModal = document.getElementById('actionModal');
const modalTitle = document.getElementById('modalTitle');
const modalIcon = document.getElementById('modalIcon');
const modalBody = document.getElementById('modalBody');
const closeActionModal = document.getElementById('closeActionModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const copyModalContentBtn = document.getElementById('copyModalContentBtn');

const settingsModal = document.getElementById('settingsModal');
const settingsBtn = document.getElementById('settingsBtn');
const closeSettingsModal = document.getElementById('closeSettingsModal');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const settingGithubToken = document.getElementById('settingGithubToken');
const settingGroqKey = document.getElementById('settingGroqKey');
const settingModel = document.getElementById('settingModel');
const activeModelName = document.getElementById('activeModelName');

const newRepoBtn = document.getElementById('newRepoBtn');
const syncBadge = document.getElementById('syncBadge');
const syncStatusText = document.getElementById('syncStatusText');
const newRepoModal = document.getElementById('newRepoModal');
const closeNewRepoModal = document.getElementById('closeNewRepoModal');
const cancelNewRepoBtn = document.getElementById('cancelNewRepoBtn');
const submitNewRepoBtn = document.getElementById('submitNewRepoBtn');
const submitNewRepoText = document.getElementById('submitNewRepoText');
const newRepoName = document.getElementById('newRepoName');
const newRepoDesc = document.getElementById('newRepoDesc');
const newRepoAutoInit = document.getElementById('newRepoAutoInit');
const newRepoAutoIndex = document.getElementById('newRepoAutoIndex');

const toast = document.getElementById('toast');

// --- Helper Functions ---
function showToast(message, duration = 3000) {
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}

function getOwnerAndRepo() {
  if (!state.selectedRepo) return null;
  const parts = state.selectedRepo.full_name.split('/');
  return { owner: parts[0], repo: parts[1] };
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  setupGitHubWriteHandlers();
  await loadUserAndConfig();
  await loadRepositories();
  startAutoSync();
});

function setupEventListeners() {
  // Tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const targetId = tab.dataset.target;
      document.getElementById(targetId).classList.add('active');
    });
  });

  // Repo select
  repoSelect.addEventListener('change', async (e) => {
    const fullName = e.target.value;
    if (!fullName) return;
    const repo = state.repositories.find(r => r.full_name === fullName);
    if (repo) {
      await selectRepository(repo);
    }
  });

  refreshReposBtn.addEventListener('click', () => loadRepositories(null, false));

  // Create New Repository Modal Handlers
  if (newRepoBtn) {
    newRepoBtn.addEventListener('click', () => {
      newRepoName.value = '';
      newRepoDesc.value = '';
      newRepoModal.style.display = 'flex';
      setTimeout(() => newRepoName.focus(), 100);
    });
  }
  if (closeNewRepoModal) {
    closeNewRepoModal.addEventListener('click', () => {
      newRepoModal.style.display = 'none';
    });
  }
  if (cancelNewRepoBtn) {
    cancelNewRepoBtn.addEventListener('click', () => {
      newRepoModal.style.display = 'none';
    });
  }
  if (submitNewRepoBtn) {
    submitNewRepoBtn.addEventListener('click', handleCreateNewRepo);
  }
  if (newRepoName) {
    newRepoName.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleCreateNewRepo();
      }
    });
  }

  // Index Repo
  indexRepoBtn.addEventListener('click', handleIndexRepo);

  // File search filter
  fileSearchInput.addEventListener('input', (e) => {
    renderFileTree(e.target.value.trim().toLowerCase());
  });

  // Copy Code
  copyCodeBtn.addEventListener('click', () => {
    if (state.activeFile && state.activeFile.content) {
      navigator.clipboard.writeText(state.activeFile.content);
      showToast('Source code copied to clipboard!');
    }
  });

  // Quick AI Action buttons
  document.getElementById('actExplain').addEventListener('click', () => triggerCodeAction('explain'));
  document.getElementById('actBugs').addEventListener('click', () => triggerCodeAction('find_bugs'));
  document.getElementById('actTests').addEventListener('click', () => triggerCodeAction('generate_tests'));
  document.getElementById('actOptimize').addEventListener('click', () => triggerCodeAction('optimize'));
  document.getElementById('actReadme').addEventListener('click', () => triggerDocAction('readme'));
  document.getElementById('actArch').addEventListener('click', () => triggerDocAction('architecture'));

  // Chat Actions
  sendChatBtn.addEventListener('click', handleSendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });

  clearChatBtn.addEventListener('click', () => {
    state.chatHistory = [];
    chatFeed.innerHTML = `
      <div class="chat-msg assistant">
        <div class="msg-avatar">🤖</div>
        <div class="msg-bubble"><p>Chat history cleared. How can I help you examine this repository?</p></div>
      </div>
    `;
  });

  // Quick Prompts
  document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      chatInput.value = btn.dataset.prompt;
      handleSendMessage();
    });
  });

  // Detach active file
  detachFileBtn.addEventListener('click', () => {
    state.activeFile = null;
    activeFileIndicator.style.display = 'none';
  });

  // Modals
  closeActionModal.addEventListener('click', () => actionModal.style.display = 'none');
  closeModalBtn.addEventListener('click', () => actionModal.style.display = 'none');
  copyModalContentBtn.addEventListener('click', () => {
    const text = modalBody.innerText;
    navigator.clipboard.writeText(text);
    showToast('AI analysis copied to clipboard!');
  });

  settingsBtn.addEventListener('click', openSettingsModal);
  closeSettingsModal.addEventListener('click', () => settingsModal.style.display = 'none');
  saveSettingsBtn.addEventListener('click', handleSaveSettings);
}

// --- API Calls & Data Loading ---

async function loadUserAndConfig() {
  try {
    const [userResp, configResp] = await Promise.all([
      fetch('/api/auth/me'),
      fetch('/api/tools/config')
    ]);

    if (userResp.ok) {
      state.user = await userResp.json();
      document.getElementById('userName').textContent = state.user.login;
      if (state.user.avatar_url) {
        document.getElementById('userAvatar').src = state.user.avatar_url;
      }
    }

    if (configResp.ok) {
      state.config = await configResp.json();
      const modelShort = state.config.groq_model.split('/').pop();
      activeModelName.textContent = modelShort;
      settingModel.value = state.config.groq_model;
    }
  } catch (err) {
    console.error('Failed to load user info or config:', err);
  }
}

async function loadRepositories(preferredFullName = null, keepCurrent = false) {
  if (!keepCurrent) {
    repoSelect.innerHTML = '<option value="">Fetching repositories...</option>';
  }
  try {
    const resp = await fetch('/api/github/repositories?per_page=100');
    if (!resp.ok) throw new Error('Failed to fetch repositories');
    const repos = await resp.json();
    state.repositories = repos;

    if (repos.length === 0) {
      repoSelect.innerHTML = '<option value="">No repositories found</option>';
      return;
    }

    repoSelect.innerHTML = repos.map(r => `
      <option value="${r.full_name}">${r.name} ${r.language ? `(${r.language})` : ''} ${r.private ? '🔒' : ''}</option>
    `).join('');

    let targetRepo = null;
    if (preferredFullName) {
      targetRepo = repos.find(r => r.full_name.toLowerCase() === preferredFullName.toLowerCase());
    } else if (keepCurrent && state.selectedRepo) {
      targetRepo = repos.find(r => r.full_name.toLowerCase() === state.selectedRepo.full_name.toLowerCase());
    }

    if (targetRepo) {
      await selectRepository(targetRepo);
    } else if (!state.selectedRepo && repos.length > 0) {
      await selectRepository(repos[0]);
    }
  } catch (err) {
    console.error(err);
    if (!keepCurrent) {
      repoSelect.innerHTML = '<option value="">Error loading repos</option>';
      showToast('Error loading GitHub repositories: ' + err.message);
    }
  }
}

async function handleCreateNewRepo() {
  const name = newRepoName.value.trim();
  if (!name) {
    showToast('Please enter a repository name.');
    newRepoName.focus();
    return;
  }

  const desc = newRepoDesc.value.trim();
  const visibilityRadio = document.querySelector('input[name="newRepoVisibility"]:checked');
  const isPrivate = visibilityRadio ? visibilityRadio.value === 'private' : false;
  const autoInit = newRepoAutoInit.checked;
  const autoIndex = newRepoAutoIndex.checked;

  submitNewRepoBtn.disabled = true;
  submitNewRepoText.textContent = 'Creating & Updating...';

  try {
    const resp = await fetch('/api/github/repository', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name,
        description: desc || null,
        private: isPrivate,
        auto_init: autoInit,
        auto_index: autoIndex
      })
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || 'Failed to create repository');
    }

    newRepoModal.style.display = 'none';
    showToast(`🎉 Repository "${name}" created and updated in assistant!`, 4500);

    // Refresh repo list and automatically select the newly created repository
    await loadRepositories(data.repository?.full_name);
  } catch (err) {
    console.error('Create repo error:', err);
    showToast(`Failed to create repository: ${err.message}`, 4500);
  } finally {
    submitNewRepoBtn.disabled = false;
    submitNewRepoText.textContent = 'Create & Auto-Index';
  }
}

let autoSyncTimer = null;
function startAutoSync() {
  if (autoSyncTimer) clearInterval(autoSyncTimer);
  // Periodically check for newly created repositories every 15 seconds
  autoSyncTimer = setInterval(async () => {
    try {
      const resp = await fetch('/api/github/sync/status?auto_index=true');
      if (!resp.ok) return;
      const data = await resp.json();
      if (data.has_new && data.new_repos_detected && data.new_repos_detected.length > 0) {
        console.log('[AutoSync] New repositories detected:', data.new_repos_detected);
        const repoNames = data.new_repos_detected.join(', ');
        showToast(`✨ New repository detected: ${repoNames}! Assistant updated & indexed.`, 5000);
        if (syncStatusText) {
          syncStatusText.textContent = '⚡ Updated!';
          setTimeout(() => { if (syncStatusText) syncStatusText.textContent = 'Auto-Sync On'; }, 3000);
        }
        await loadRepositories(data.new_repos_detected[0], false);
      }
    } catch (err) {
      // background polling silent catch
    }
  }, 15000);
}

async function selectRepository(repo) {
  state.selectedRepo = repo;
  repoSelect.value = repo.full_name;
  
  // Update UI Meta
  repoFullName.textContent = repo.full_name;
  repoDescription.textContent = repo.description || 'No description provided';
  statStars.textContent = repo.stargazers_count;
  statForks.textContent = repo.forks_count;
  statBranch.textContent = repo.default_branch;
  statLanguage.textContent = repo.language || 'Codebase';
  repoStatsPills.style.display = 'flex';

  // Load Tree, Index status, Issues & Commits
  await Promise.all([
    fetchIndexStatus(repo),
    fetchFileTree(repo),
    fetchIssues(repo),
    fetchCommits(repo)
  ]);
}

async function fetchIndexStatus(repo) {
  const parts = repo.full_name.split('/');
  try {
    const resp = await fetch(`/api/repository/status/${parts[0]}/${parts[1]}`);
    if (resp.ok) {
      const data = await resp.json();
      updateIndexUI(data);
    }
  } catch (err) {
    console.error('Error fetching index status:', err);
  }
}

function updateIndexUI(statusData) {
  if (statusData.indexed) {
    indexStatusPill.className = 'status-pill ready';
    indexStatusPill.textContent = 'Indexed';
    statChunks.textContent = `${statusData.total_chunks} Chunks Indexed`;
    indexBtnText.textContent = 'Re-Index ChromaDB';
  } else if (statusData.status === 'indexing') {
    indexStatusPill.className = 'status-pill indexing';
    indexStatusPill.textContent = 'Indexing...';
    statChunks.textContent = `Indexing...`;
    indexBtnText.textContent = 'Indexing...';
  } else {
    indexStatusPill.className = 'status-pill idle';
    indexStatusPill.textContent = 'Unindexed';
    statChunks.textContent = '0 Chunks Indexed';
    indexBtnText.textContent = 'Index with ChromaDB';
  }
}

async function handleIndexRepo() {
  const meta = getOwnerAndRepo();
  if (!meta) return;

  indexStatusPill.className = 'status-pill indexing';
  indexStatusPill.textContent = 'Indexing...';
  indexBtnText.textContent = 'Indexing...';
  showToast(`Starting ChromaDB indexing for ${meta.repo}...`);

  try {
    const resp = await fetch('/api/repository/index', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: meta.owner,
        repo: meta.repo,
        branch: state.selectedRepo.default_branch,
        max_files: 60
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Indexing failed');
    }

    const result = await resp.json();
    updateIndexUI(result);
    showToast(`Successfully indexed ${result.total_files} files (${result.total_chunks} chunks) into ChromaDB!`);
  } catch (err) {
    console.error(err);
    indexStatusPill.className = 'status-pill idle';
    indexStatusPill.textContent = 'Failed';
    showToast(`Indexing error: ${err.message}`);
  }
}

async function fetchFileTree(repo) {
  const parts = repo.full_name.split('/');
  fileTreeList.innerHTML = '<div class="empty-state">Loading file tree...</div>';

  try {
    const resp = await fetch(`/api/github/tree/${parts[0]}/${parts[1]}?branch=${repo.default_branch}`);
    if (!resp.ok) throw new Error('Could not load tree');
    const data = await resp.json();
    state.fileTree = data.tree || [];
    renderFileTree();
  } catch (err) {
    fileTreeList.innerHTML = `<div class="empty-state">Failed to load tree: ${err.message}</div>`;
  }
}

function renderFileTree(filterQuery = '') {
  if (!state.fileTree.length) {
    fileTreeList.innerHTML = '<div class="empty-state">No files in tree.</div>';
    return;
  }

  const filtered = state.fileTree.filter(item => {
    if (!filterQuery) return true;
    return item.path.toLowerCase().includes(filterQuery);
  });

  if (filtered.length === 0) {
    fileTreeList.innerHTML = '<div class="empty-state">No matching files found.</div>';
    return;
  }

  // Build HTML list
  let html = '';
  filtered.slice(0, 200).forEach(item => {
    const isDir = item.type === 'tree';
    const icon = isDir ? '📁' : getFileIcon(item.path);
    const depth = (item.path.match(/\//g) || []).length;
    const indent = `<span class="tree-indent" style="width: ${depth * 10}px"></span>`;
    const fileName = item.path.split('/').pop();

    html += `
      <div class="tree-item ${isDir ? 'folder' : 'file'}" data-path="${item.path}" data-type="${item.type}">
        ${indent}
        <span>${icon}</span>
        <span class="file-name">${fileName}</span>
      </div>
    `;
  });

  fileTreeList.innerHTML = html;

  // Add click listeners to files
  fileTreeList.querySelectorAll('.tree-item.file').forEach(el => {
    el.addEventListener('click', () => {
      fileTreeList.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
      el.classList.add('active');
      openFile(el.dataset.path);
    });
  });
}

function getFileIcon(path) {
  const ext = path.split('.').pop().toLowerCase();
  switch (ext) {
    case 'py': return '🐍';
    case 'js':
    case 'jsx': return '🟨';
    case 'ts':
    case 'tsx': return '🔷';
    case 'html': return '🌐';
    case 'css': return '🎨';
    case 'json': return '📋';
    case 'md': return '📝';
    case 'sql': return '🗄️';
    case 'sh': return '🐚';
    default: return '📄';
  }
}

async function openFile(path) {
  const meta = getOwnerAndRepo();
  if (!meta) return;

  activeFilePath.textContent = path;
  codeBlock.textContent = '// Fetching file contents from GitHub...';
  codeBlock.className = 'language-plaintext';

  try {
    const branch = state.selectedRepo.default_branch || 'main';
    const resp = await fetch(`/api/github/file/${meta.owner}/${meta.repo}?path=${encodeURIComponent(path)}&branch=${branch}`);
    if (!resp.ok) throw new Error('Failed to retrieve file content');
    const data = await resp.json();

    state.activeFile = {
      path: data.path,
      content: data.content,
      language: data.language
    };

    // Update Code Viewer
    codeBlock.textContent = data.content;
    codeBlock.className = `language-${data.language || 'plaintext'}`;
    Prism.highlightElement(codeBlock);

    // Update active file indicator in chat
    attachedFileName.textContent = data.path.split('/').pop();
    activeFileIndicator.style.display = 'flex';
  } catch (err) {
    codeBlock.textContent = `// Error: ${err.message}`;
  }
}

async function fetchIssues(repo) {
  const parts = repo.full_name.split('/');
  const issuesList = document.getElementById('issuesList');
  issuesList.innerHTML = '<div class="empty-state">Loading issues & pull requests...</div>';

  try {
    const resp = await fetch(`/api/github/issues/${parts[0]}/${parts[1]}`);
    if (!resp.ok) throw new Error('Failed to fetch issues');
    const items = await resp.json();

    if (items.length === 0) {
      issuesList.innerHTML = '<div class="empty-state">No open or closed issues/PRs found.</div>';
      return;
    }

    issuesList.innerHTML = items.map(item => `
      <div class="issue-card">
        <div class="issue-title-row">
          <span class="issue-title">
            ${item.is_pr ? '🔀' : '⚠️'} #${item.number} ${escapeHtml(item.title)}
          </span>
          <span class="issue-badge ${item.state}">${item.state}</span>
        </div>
        <div class="issue-meta">
          Opened by <strong>${item.user.login}</strong> • Updated ${new Date(item.updated_at).toLocaleDateString()}
        </div>
        <div style="margin-top: 8px;">
          <button class="action-chip" onclick="analyzeIssue(${item.number}, ${item.is_pr})">
            🤖 AI Diagnose & Fix
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    issuesList.innerHTML = `<div class="empty-state">Failed to load issues: ${err.message}</div>`;
  }
}

async function fetchCommits(repo) {
  const parts = repo.full_name.split('/');
  const commitsList = document.getElementById('commitsList');
  commitsList.innerHTML = '<div class="empty-state">Loading commit history...</div>';

  try {
    const resp = await fetch(`/api/github/commits/${parts[0]}/${parts[1]}`);
    if (!resp.ok) throw new Error('Failed to fetch commits');
    const commits = await resp.json();

    if (commits.length === 0) {
      commitsList.innerHTML = '<div class="empty-state">No commits found.</div>';
      return;
    }

    commitsList.innerHTML = commits.map(c => `
      <div class="commit-card">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
          <strong style="font-family: var(--font-mono); color: #818cf8;">${c.sha}</strong>
          <span style="font-size: 0.75rem; color: var(--text-dim);">${new Date(c.date).toLocaleDateString()}</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 4px;">
          ${escapeHtml(c.message)}
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">
          👤 ${c.author}
        </div>
      </div>
    `).join('');
  } catch (err) {
    commitsList.innerHTML = `<div class="empty-state">Failed to load commits: ${err.message}</div>`;
  }
}

// --- AI Quick Actions & Modals ---

async function triggerCodeAction(action) {
  if (!state.activeFile) {
    showToast('Please select a file from the explorer first.');
    return;
  }

  const meta = getOwnerAndRepo();
  const titles = {
    explain: { title: 'Code Walkthrough & Explanation', icon: '🔍' },
    find_bugs: { title: 'Bug & Security Vulnerability Audit', icon: '🐛' },
    generate_tests: { title: 'Automated Unit Test Suite', icon: '🧪' },
    optimize: { title: 'Performance & Architecture Optimization', icon: '⚡' }
  };

  modalTitle.textContent = titles[action].title;
  modalIcon.textContent = titles[action].icon;
  modalBody.innerHTML = `
    <div class="loading-spinner-container">
      <div class="spinner"></div>
      <p>Running multi-agent analysis with Groq 120B on <code>${state.activeFile.path}</code>...</p>
    </div>
  `;
  actionModal.style.display = 'flex';

  try {
    const resp = await fetch('/api/tools/code-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: meta.owner,
        repo: meta.repo,
        file_path: state.activeFile.path,
        code: state.activeFile.content,
        action: action
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Action failed');
    }

    const data = await resp.json();
    modalBody.innerHTML = marked.parse(data.analysis);
  } catch (err) {
    modalBody.innerHTML = `<p style="color: #f43f5e;">Analysis error: ${err.message}</p>`;
  }
}

async function triggerDocAction(docType) {
  const meta = getOwnerAndRepo();
  if (!meta) return;

  const titles = {
    readme: { title: 'Generated Production README.md', icon: '📝' },
    architecture: { title: 'Architectural Blueprint & Mermaid Diagram', icon: '🏛️' }
  };

  modalTitle.textContent = titles[docType].title;
  modalIcon.textContent = titles[docType].icon;
  modalBody.innerHTML = `
    <div class="loading-spinner-container">
      <div class="spinner"></div>
      <p>Synthesizing repository codebase into ${docType.toUpperCase()}...</p>
    </div>
  `;
  actionModal.style.display = 'flex';

  try {
    const resp = await fetch('/api/tools/generate-doc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: meta.owner,
        repo: meta.repo,
        doc_type: docType
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Doc generation failed');
    }

    const data = await resp.json();
    state.lastGeneratedContent = data.markdown_content;
    state.lastGeneratedType = docType;
    modalBody.innerHTML = marked.parse(data.markdown_content);
  } catch (err) {
    modalBody.innerHTML = `<p style="color: #f43f5e;">Generation error: ${err.message}</p>`;
  }
}

window.analyzeIssue = async function(number, isPr) {
  const meta = getOwnerAndRepo();
  if (!meta) return;

  modalTitle.textContent = `Diagnosis for ${isPr ? 'PR' : 'Issue'} #${number}`;
  modalIcon.textContent = '🤖';
  modalBody.innerHTML = `
    <div class="loading-spinner-container">
      <div class="spinner"></div>
      <p>Retrieving issue details and searching ChromaDB for root cause...</p>
    </div>
  `;
  actionModal.style.display = 'flex';

  try {
    const resp = await fetch('/api/tools/analyze-issue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        owner: meta.owner,
        repo: meta.repo,
        number: number,
        is_pr: isPr
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Diagnosis failed');
    }

    const data = await resp.json();
    state.lastGeneratedContent = data.analysis;
    state.lastDiagnosedIssue = number;
    modalBody.innerHTML = marked.parse(data.analysis);
    
    // Add Post Comment to GitHub button inside the modal
    const postBtn = document.createElement('button');
    postBtn.className = 'btn btn-primary';
    postBtn.style.marginTop = '16px';
    postBtn.innerHTML = '💬 Post this AI Review directly to GitHub Issue';
    postBtn.onclick = async () => {
      postBtn.disabled = true;
      postBtn.textContent = 'Posting to GitHub...';
      try {
        const commentResp = await fetch('/api/github/comment', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            owner: meta.owner,
            repo: meta.repo,
            issue_number: number,
            comment: `### 🤖 GitHub AI Assistant Diagnosis\n\n${data.analysis}\n\n*Analyzed with Groq 120B & ChromaDB*`
          })
        });
        if (!commentResp.ok) throw new Error('Failed to post comment');
        showToast(`Comment posted successfully to GitHub issue #${number}!`);
        postBtn.textContent = '✅ Comment Posted on GitHub';
      } catch (e) {
        showToast('Error posting comment: ' + e.message);
        postBtn.disabled = false;
        postBtn.textContent = 'Retry Posting to GitHub';
      }
    };
    modalBody.appendChild(postBtn);
  } catch (err) {
    modalBody.innerHTML = `<p style="color: #f43f5e;">Diagnosis error: ${err.message}</p>`;
  }
};

// --- GitHub Push / PR Handlers ---
let isPrMode = false;

function setupGitHubWriteHandlers() {
  const commitActionBtn = document.getElementById('commitActionBtn');
  const createPrActionBtn = document.getElementById('createPrActionBtn');
  const commitModal = document.getElementById('commitModal');
  const closeCommitModal = document.getElementById('closeCommitModal');
  const cancelCommitBtn = document.getElementById('cancelCommitBtn');
  const submitCommitBtn = document.getElementById('submitCommitBtn');
  const commitFilePath = document.getElementById('commitFilePath');
  const commitBranch = document.getElementById('commitBranch');
  const commitMessage = document.getElementById('commitMessage');
  const prFieldsGroup = document.getElementById('prFieldsGroup');
  const prTitle = document.getElementById('prTitle');
  const prBody = document.getElementById('prBody');

  if (commitActionBtn) {
    commitActionBtn.addEventListener('click', () => {
      isPrMode = false;
      prFieldsGroup.style.display = 'none';
      document.getElementById('commitModalTitle').textContent = 'Commit Directly to GitHub';
      submitCommitBtn.textContent = 'Push Commit to GitHub';
      commitFilePath.value = state.activeFile ? state.activeFile.path : (state.lastGeneratedType === 'readme' ? 'README.md' : 'generated_file.py');
      commitBranch.value = state.selectedRepo ? state.selectedRepo.default_branch : 'main';
      commitMessage.value = `feat: update ${commitFilePath.value} via GitHub AI Assistant`;
      commitModal.style.display = 'flex';
    });
  }

  if (createPrActionBtn) {
    createPrActionBtn.addEventListener('click', () => {
      isPrMode = true;
      prFieldsGroup.style.display = 'block';
      document.getElementById('commitModalTitle').textContent = 'Create Pull Request on GitHub';
      submitCommitBtn.textContent = 'Create Pull Request';
      const path = state.activeFile ? state.activeFile.path : (state.lastGeneratedType === 'readme' ? 'README.md' : 'patch.py');
      commitFilePath.value = path;
      commitBranch.value = `ai-patch-${Date.now().toString().slice(-4)}`;
      commitMessage.value = `feat: AI suggested improvements for ${path}`;
      prTitle.value = `AI Assistant: Updates to ${path}`;
      prBody.value = `This PR contains code generated by the GitHub AI Assistant powered by Groq 120B.\n\n### Summary\n- File: \`${path}\`\n- Generated via AI Assistant RAG pipeline.`;
      commitModal.style.display = 'flex';
    });
  }

  if (closeCommitModal) closeCommitModal.addEventListener('click', () => commitModal.style.display = 'none');
  if (cancelCommitBtn) cancelCommitBtn.addEventListener('click', () => commitModal.style.display = 'none');

  if (submitCommitBtn) {
    submitCommitBtn.addEventListener('click', async () => {
      const meta = getOwnerAndRepo();
      if (!meta) return;

      const path = commitFilePath.value.trim();
      const branch = commitBranch.value.trim();
      const message = commitMessage.value.trim();
      const content = state.lastGeneratedContent || (state.activeFile ? state.activeFile.content : '');

      if (!path || !branch || !message || !content) {
        showToast('Please fill all required fields and ensure content exists.');
        return;
      }

      submitCommitBtn.disabled = true;
      submitCommitBtn.textContent = 'Pushing to GitHub...';

      try {
        if (isPrMode) {
          // 1. Create new branch
          const baseBranch = state.selectedRepo.default_branch || 'main';
          await fetch('/api/github/branch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              owner: meta.owner,
              repo: meta.repo,
              new_branch: branch,
              from_branch: baseBranch
            })
          });

          // 2. Commit file to new branch
          await fetch('/api/github/commit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              owner: meta.owner,
              repo: meta.repo,
              path: path,
              content: content,
              message: message,
              branch: branch
            })
          });

          // 3. Open Pull Request
          const prResp = await fetch('/api/github/pull-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              owner: meta.owner,
              repo: meta.repo,
              title: prTitle.value.trim() || `Update ${path}`,
              body: prBody.value.trim(),
              head: branch,
              base: baseBranch
            })
          });

          if (!prResp.ok) throw new Error('Failed to open PR');
          const prData = await prResp.json();
          commitModal.style.display = 'none';
          showToast(`Pull Request #${prData.pr_number} created on GitHub!`);
          window.open(prData.html_url, '_blank');
        } else {
          // Direct commit
          const commitResp = await fetch('/api/github/commit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              owner: meta.owner,
              repo: meta.repo,
              path: path,
              content: content,
              message: message,
              branch: branch
            })
          });

          if (!commitResp.ok) throw new Error('Commit failed');
          const commitData = await commitResp.json();
          commitModal.style.display = 'none';
          showToast(`Successfully committed ${path} to GitHub!`);
          if (commitData.html_url) {
            window.open(commitData.html_url, '_blank');
          }
        }
      } catch (err) {
        showToast('GitHub operation error: ' + err.message);
      } finally {
        submitCommitBtn.disabled = false;
        submitCommitBtn.textContent = isPrMode ? 'Create Pull Request' : 'Push to GitHub';
      }
    });
  }
}


// --- Chat Copilot Logic ---

async function handleSendMessage() {
  const query = chatInput.value.trim();
  if (!query || state.isStreaming) return;

  const meta = getOwnerAndRepo();
  if (!meta) {
    showToast('Please select a repository first.');
    return;
  }

  // Clear input
  chatInput.value = '';
  chatInput.style.height = 'auto';

  // Append user message to UI
  appendChatMessage('user', query);
  state.chatHistory.push({ role: 'user', content: query });

  // Create assistant placeholder bubble
  const assistantBubble = appendChatMessage('assistant', 'Thinking...');
  state.isStreaming = true;

  try {
    const payload = {
      owner: meta.owner,
      repo: meta.repo,
      message: query,
      history: state.chatHistory.slice(-8),
      current_file_path: state.activeFile ? state.activeFile.path : null,
      current_file_content: state.activeFile ? state.activeFile.content : null,
      use_rag: ragToggle.checked,
      model: settingModel.value
    };

    // Use regular POST for reliable complete response with source citations
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Chat query failed');
    }

    const data = await resp.json();
    assistantBubble.innerHTML = marked.parse(data.answer);

    // Add source citation chips if RAG was used
    if (data.sources && data.sources.length > 0) {
      let citationsHtml = `
        <div class="source-citations">
          <div class="citation-header">📚 ${data.sources.length} Context Chunks (ChromaDB):</div>
      `;
      data.sources.forEach(s => {
        citationsHtml += `<span class="citation-chip" title="Lines ${s.start_line}-${s.end_line}">📄 ${s.file_path}:${s.start_line}</span>`;
      });
      citationsHtml += '</div>';
      assistantBubble.innerHTML += citationsHtml;
    }

    state.chatHistory.push({ role: 'assistant', content: data.answer });
  } catch (err) {
    assistantBubble.innerHTML = `<p style="color: #f43f5e;">Error: ${err.message}</p>`;
  } finally {
    state.isStreaming = false;
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }
}

function appendChatMessage(role, text) {
  const msgEl = document.createElement('div');
  msgEl.className = `chat-msg ${role}`;
  const avatar = role === 'user' ? '👤' : '🤖';

  msgEl.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">${marked.parse(text)}</div>
  `;

  chatFeed.appendChild(msgEl);
  chatFeed.scrollTop = chatFeed.scrollHeight;
  return msgEl.querySelector('.msg-bubble');
}

// --- Settings ---

function openSettingsModal() {
  settingGithubToken.value = '';
  settingGroqKey.value = '';
  if (state.config.groq_model) {
    settingModel.value = state.config.groq_model;
  }
  settingsModal.style.display = 'flex';
}

async function handleSaveSettings() {
  const payload = {};
  if (settingGithubToken.value.trim()) payload.github_token = settingGithubToken.value.trim();
  if (settingGroqKey.value.trim()) payload.groq_api_key = settingGroqKey.value.trim();
  if (settingModel.value) payload.groq_model = settingModel.value;

  try {
    const resp = await fetch('/api/tools/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (resp.ok) {
      showToast('Settings updated successfully!');
      settingsModal.style.display = 'none';
      await loadUserAndConfig();
      if (payload.github_token) {
        await loadRepositories();
      }
    }
  } catch (err) {
    showToast('Failed to update settings: ' + err.message);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
