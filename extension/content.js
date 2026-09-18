/**
 * GitHub AI Assistant — Content Script
 * Injected directly into github.com pages
 */

(function () {
  const BACKEND_URL = 'http://127.0.0.1:8000';
  let isConnected = false;
  let chatHistory = [];

  // 1. Detect GitHub Page Context
  function parseGitHubUrl() {
    const path = window.location.pathname.split('/').filter(Boolean);
    const context = {
      owner: path[0] || null,
      repo: path[1] || null,
      type: path[2] || null, // 'blob', 'tree', 'issues', 'pull'
      detail: path.slice(3).join('/') || null,
      filePath: null,
      itemNumber: null
    };

    if (context.type === 'blob' || context.type === 'tree') {
      context.filePath = path.slice(4).join('/');
    } else if (context.type === 'issues' || context.type === 'pull') {
      context.itemNumber = parseInt(path[3], 10) || null;
    }

    return context;
  }

  // 2. Initialize and Inject UI Elements
  function init() {
    if (document.getElementById('gh-ai-fab-btn')) return;

    checkBackendHealth();
    injectFloatingButton();
    injectDrawer();
    injectHeaderButton();
  }

  // Check if FastAPI backend is running locally
  async function checkBackendHealth() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`, { method: 'GET' });
      if (res.ok) {
        isConnected = true;
        updateStatusDot(true);
      } else {
        updateStatusDot(false);
      }
    } catch (e) {
      isConnected = false;
      updateStatusDot(false);
    }
  }

  function updateStatusDot(online) {
    const dot = document.querySelector('.gh-ai-status-dot');
    if (dot) {
      dot.className = `gh-ai-status-dot ${online ? '' : 'offline'}`;
      dot.title = online ? 'AI Assistant Backend: Online' : 'AI Backend: Offline (Run run.bat)';
    }
  }

  // 3. Inject Floating Action Button
  function injectFloatingButton() {
    const fab = document.createElement('div');
    fab.id = 'gh-ai-fab-btn';
    fab.title = 'GitHub AI Assistant';
    fab.innerHTML = `
      <span id="gh-ai-fab-icon">⚡</span>
      <span class="gh-ai-status-dot ${isConnected ? '' : 'offline'}"></span>
    `;

    fab.addEventListener('click', toggleDrawer);
    document.body.appendChild(fab);
  }

  // 4. Inject Top Header Button
  function injectHeaderButton() {
    const navContainer = document.querySelector('.Header-item--full') ||
                         document.querySelector('[data-target="search-input.container"]') ||
                         document.querySelector('header');
    if (!navContainer || document.getElementById('gh-ai-nav-btn')) return;

    const navBtn = document.createElement('a');
    navBtn.id = 'gh-ai-nav-btn';
    navBtn.className = 'gh-ai-nav-item';
    navBtn.innerHTML = `⚡ <span>AI Copilot</span>`;
    navBtn.addEventListener('click', (e) => {
      e.preventDefault();
      toggleDrawer();
    });

    navContainer.appendChild(navBtn);
  }

  // 5. Inject Slide-out AI Drawer
  function injectDrawer() {
    const ctx = parseGitHubUrl();
    const drawer = document.createElement('div');
    drawer.id = 'gh-ai-drawer';
    drawer.className = 'hidden';

    const repoDisplay = ctx.repo ? `${ctx.owner}/${ctx.repo}` : (ctx.owner ? `@${ctx.owner}` : 'GitHub');
    const fileDisplay = ctx.filePath ? `📄 ${ctx.filePath.split('/').pop()}` : (ctx.itemNumber ? `#${ctx.itemNumber}` : '');

    drawer.innerHTML = `
      <div class="gh-ai-drawer-header">
        <div class="gh-ai-brand">
          <span>⚡</span>
          <span class="gh-ai-brand-gradient">GitHub AI Assistant</span>
        </div>
        <div class="gh-ai-header-controls">
          <a href="http://127.0.0.1:8000" target="_blank" class="gh-ai-btn-icon" title="Open Full Dashboard">↗</a>
          <button id="gh-ai-close-btn" class="gh-ai-btn-icon" title="Close">×</button>
        </div>
      </div>

      <div class="gh-ai-context-banner">
        <span class="gh-ai-repo-tag">📦 <strong id="gh-ai-repo-label">${repoDisplay}</strong></span>
        <span id="gh-ai-file-label">${fileDisplay}</span>
      </div>

      <div class="gh-ai-tabs">
        <button class="gh-ai-tab active" data-tab="chat">💬 Copilot Chat</button>
        <button class="gh-ai-tab" data-tab="actions">⚡ Quick AI</button>
      </div>

      <div class="gh-ai-body" id="gh-ai-messages">
        <div class="gh-ai-msg assistant">
          <div class="gh-ai-bubble">
            <strong>Hi Jyotir! ⚡</strong><br/>
            I am your GitHub AI Assistant. I can read your repo code, explain functions, find bugs, and answer questions.
          </div>
        </div>
      </div>

      <div class="gh-ai-footer">
        <textarea id="gh-ai-input" placeholder="Ask about this repo, code, or PR..." rows="1"></textarea>
        <button id="gh-ai-send-btn">➤</button>
      </div>
    `;

    document.body.appendChild(drawer);

    // Event listeners inside drawer
    document.getElementById('gh-ai-close-btn').addEventListener('click', toggleDrawer);
    document.getElementById('gh-ai-send-btn').addEventListener('click', handleUserSend);

    const input = document.getElementById('gh-ai-input');
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleUserSend();
      }
    });

    // Tab switching
    drawer.querySelectorAll('.gh-ai-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        drawer.querySelectorAll('.gh-ai-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const mode = tab.dataset.tab;
        renderTabContent(mode);
      });
    });
  }

  function toggleDrawer() {
    const drawer = document.getElementById('gh-ai-drawer');
    if (!drawer) return;
    drawer.classList.toggle('hidden');
    if (!drawer.classList.contains('hidden')) {
      checkBackendHealth();
      updateContextLabels();
    }
  }

  function updateContextLabels() {
    const ctx = parseGitHubUrl();
    const repoLabel = document.getElementById('gh-ai-repo-label');
    const fileLabel = document.getElementById('gh-ai-file-label');
    if (repoLabel) {
      repoLabel.textContent = ctx.repo ? `${ctx.owner}/${ctx.repo}` : (ctx.owner ? `@${ctx.owner}` : 'GitHub');
    }
    if (fileLabel) {
      fileLabel.textContent = ctx.filePath ? `📄 ${ctx.filePath.split('/').pop()}` : (ctx.itemNumber ? `#${ctx.itemNumber}` : '');
    }
  }

  function renderTabContent(mode) {
    const body = document.getElementById('gh-ai-messages');
    if (mode === 'actions') {
      const ctx = parseGitHubUrl();
      body.innerHTML = `
        <div style="font-size: 12px; font-weight: 600; color: #818cf8; margin-bottom: 8px;">1-Click AI Operations:</div>
        <div class="gh-ai-actions-grid">
          <button class="gh-ai-action-btn" id="extActOverview">📖 Repo Overview</button>
          <button class="gh-ai-action-btn" id="extActExplain">🔍 Explain Code</button>
          <button class="gh-ai-action-btn" id="extActBugs">🐛 Find Bugs</button>
          <button class="gh-ai-action-btn" id="extActTests">🧪 Generate Tests</button>
          <button class="gh-ai-action-btn" id="extActReadme">📝 Draft README</button>
          <button class="gh-ai-action-btn" id="extActPR">🔀 Review PR/Issue</button>
        </div>
        <div id="extActionResult" style="font-size: 12px; line-height: 1.5;"></div>
      `;

      // Wire quick actions
      document.getElementById('extActOverview').onclick = () => runPrompt("Give me a high-level architectural overview of this repository.");
      document.getElementById('extActExplain').onclick = () => runActiveFileAction('explain');
      document.getElementById('extActBugs').onclick = () => runActiveFileAction('find_bugs');
      document.getElementById('extActTests').onclick = () => runActiveFileAction('generate_tests');
      document.getElementById('extActReadme').onclick = () => runPrompt("Generate a professional README.md for this repository.");
      document.getElementById('extActPR').onclick = () => runPRReview();
    } else {
      // Re-render chat
      body.innerHTML = `
        <div class="gh-ai-msg assistant">
          <div class="gh-ai-bubble">
            <strong>Hi Jyotir! ⚡</strong><br/>
            I am your GitHub AI Assistant. I can read your repo code, explain functions, find bugs, and answer questions.
          </div>
        </div>
      `;
      chatHistory.forEach(m => appendChatMessage(m.role, m.content));
    }
  }

  // 6. Handle Chat Send
  async function handleUserSend() {
    const input = document.getElementById('gh-ai-input');
    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    appendChatMessage('user', query);
    chatHistory.push({ role: 'user', content: query });

    const assistantBubble = appendChatMessage('assistant', 'Thinking with Groq 120B...');
    const ctx = parseGitHubUrl();

    if (!ctx.owner || !ctx.repo) {
      assistantBubble.innerHTML = "Please navigate to any specific repository page to chat with its codebase!";
      return;
    }

    try {
      const resp = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          owner: ctx.owner,
          repo: ctx.repo,
          message: query,
          history: chatHistory.slice(-6),
          use_rag: true
        })
      });

      if (!resp.ok) throw new Error('Backend query failed');
      const data = await resp.json();
      assistantBubble.innerHTML = formatMarkdown(data.answer);

      if (data.sources && data.sources.length > 0) {
        let sourcesHtml = '<div style="margin-top: 8px; font-size: 11px; color: #a855f7;">📚 Sources: ';
        data.sources.forEach(s => {
          sourcesHtml += `<span style="background: rgba(168,85,247,0.15); padding: 1px 4px; border-radius: 4px; margin-right: 4px;">${s.file_path}</span>`;
        });
        sourcesHtml += '</div>';
        assistantBubble.innerHTML += sourcesHtml;
      }

      chatHistory.push({ role: 'assistant', content: data.answer });
    } catch (e) {
      assistantBubble.innerHTML = `<span style="color: #ef4444;">Error connecting to backend (${e.message}). Make sure \`run.bat\` is running at http://127.0.0.1:8000!</span>`;
    }
  }

  function appendChatMessage(role, text) {
    const container = document.getElementById('gh-ai-messages');
    if (!container) return null;

    const msgEl = document.createElement('div');
    msgEl.className = `gh-ai-msg ${role}`;
    msgEl.innerHTML = `<div class="gh-ai-bubble">${formatMarkdown(text)}</div>`;
    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;
    return msgEl.querySelector('.gh-ai-bubble');
  }

  function runPrompt(promptText) {
    // Switch to chat tab
    document.querySelector('.gh-ai-tab[data-tab="chat"]').click();
    const input = document.getElementById('gh-ai-input');
    input.value = promptText;
    handleUserSend();
  }

  async function runActiveFileAction(action) {
    const ctx = parseGitHubUrl();
    const resEl = document.getElementById('extActionResult');
    resEl.innerHTML = `<p style="color: #818cf8;">Analyzing file with Groq...</p>`;

    if (!ctx.owner || !ctx.repo) {
      resEl.innerHTML = `<p style="color: #ef4444;">Navigate into a repository first.</p>`;
      return;
    }

    try {
      // If user is currently viewing a file on GitHub, grab the code directly from page or backend
      const filePath = ctx.filePath || 'main.py';
      const fileResp = await fetch(`${BACKEND_URL}/api/github/file/${ctx.owner}/${ctx.repo}?path=${encodeURIComponent(filePath)}`);
      if (!fileResp.ok) throw new Error('Could not fetch file content');
      const fileData = await fileResp.json();

      const actionResp = await fetch(`${BACKEND_URL}/api/tools/code-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          owner: ctx.owner,
          repo: ctx.repo,
          file_path: filePath,
          code: fileData.content,
          action: action
        })
      });

      const actionData = await actionResp.json();
      resEl.innerHTML = `
        <div style="background: #0d1117; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px; margin-top: 8px; max-height: 250px; overflow-y: auto;">
          ${formatMarkdown(actionData.analysis)}
        </div>
      `;
    } catch (err) {
      resEl.innerHTML = `<p style="color: #ef4444;">Action failed: ${err.message}</p>`;
    }
  }

  async function runPRReview() {
    const ctx = parseGitHubUrl();
    const resEl = document.getElementById('extActionResult');
    if (!ctx.itemNumber) {
      resEl.innerHTML = `<p style="color: #ef4444;">Please open a GitHub Issue or Pull Request page first!</p>`;
      return;
    }

    resEl.innerHTML = `<p style="color: #818cf8;">Diagnosing Issue/PR #${ctx.itemNumber} with ChromaDB & Groq 120B...</p>`;
    try {
      const resp = await fetch(`${BACKEND_URL}/api/tools/analyze-issue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          owner: ctx.owner,
          repo: ctx.repo,
          number: ctx.itemNumber,
          is_pr: ctx.type === 'pull'
        })
      });
      const data = await resp.json();
      resEl.innerHTML = `
        <div style="background: #0d1117; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px; margin-top: 8px; max-height: 250px; overflow-y: auto;">
          ${formatMarkdown(data.analysis)}
        </div>
      `;
    } catch (e) {
      resEl.innerHTML = `<p style="color: #ef4444;">Review error: ${e.message}</p>`;
    }
  }

  // Simple Markdown Formatter
  function formatMarkdown(text) {
    if (!text) return '';
    return text
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br/>');
  }

  // Run on page load and on GitHub Turbo/PJAX navigation
  window.addEventListener('load', init);
  document.addEventListener('turbo:render', init);
  document.addEventListener('pjax:end', init);
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    init();
  }
})();
