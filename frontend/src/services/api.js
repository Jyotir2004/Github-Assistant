// Resolve base API URL from environment variables
// Supports VITE_API_BASE_URL, VITE_API_URL, and VITE_BACKEND_URL
const envBase = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_BACKEND_URL ||
  ''
).trim().replace(/\/+$/, '');

export const BASE_URL = envBase
  ? (envBase.endsWith('/api') ? envBase : `${envBase}/api`)
  : '/api';

/**
 * Robust fetch wrapper that safely handles non-JSON responses (e.g. 404/500/502 HTML pages)
 * to avoid "Unexpected token 'T', 'The page c'... is not valid JSON" errors.
 */
async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  let res;

  try {
    res = await fetch(url, options);
  } catch (netErr) {
    throw new Error(
      `Cannot connect to backend server at ${url}. ` +
      `Make sure the backend is running and CORS/network settings allow access. (${netErr.message})`
    );
  }

  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  if (!res.ok) {
    let errorDetail = '';
    if (isJson) {
      try {
        const errorJson = await res.json();
        errorDetail = errorJson?.detail || errorJson?.message || errorJson?.error || JSON.stringify(errorJson);
      } catch {
        errorDetail = '';
      }
    } else {
      const text = await res.text().catch(() => '');
      if (text.includes('The page could not be found') || res.status === 404) {
        errorDetail = `Endpoint not found (404) at ${url}. If deployed on Vercel/Render, ensure VITE_API_BASE_URL or VITE_API_URL is set in your environment variables and points to your active backend.`;
      } else if (res.status === 502 || res.status === 503) {
        errorDetail = `Backend server is starting up or temporarily unavailable (HTTP ${res.status}). If hosted on Render free tier, it may need 30-60 seconds to wake up.`;
      } else {
        errorDetail = text.slice(0, 200);
      }
    }

    throw new Error(errorDetail || `Request failed with HTTP status ${res.status} (${res.statusText || 'Error'})`);
  }

  if (isJson) {
    try {
      return await res.json();
    } catch (parseErr) {
      throw new Error(`Failed to parse backend JSON response: ${parseErr.message}`);
    }
  }

  // Fallback for text responses
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  // Auth & Rate Limit
  getUser: () => request('/auth/me'),
  getRateLimit: () => request('/auth/rate-limit'),

  // GitHub Repos & Files
  getRepositories: () => request('/github/repositories?per_page=100'),
  getRepository: (owner, repo) => request(`/github/repository/${owner}/${repo}`),
  createRepository: (payload) => request('/github/repository', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }),
  getSyncStatus: (autoIndex = true) => request(`/github/sync/status?auto_index=${autoIndex}`),
  getFileTree: (owner, repo, branch) => request(`/github/tree/${owner}/${repo}?branch=${branch || 'main'}`),
  getFileContent: (owner, repo, path, branch) =>
    request(`/github/file/${owner}/${repo}?path=${encodeURIComponent(path)}&branch=${branch || 'main'}`),
  getIssues: (owner, repo) => request(`/github/issues/${owner}/${repo}`),
  getCommits: (owner, repo) => request(`/github/commits/${owner}/${repo}`),

  // ChromaDB RAG
  getIndexStatus: (owner, repo) => request(`/repository/status/${owner}/${repo}`),
  indexRepository: (owner, repo, branch) => request('/repository/index', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner, repo, branch, max_files: 60 })
  }),

  // Chat
  chat: (payload) => request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }),

  // AI Tools & Code Actions
  codeAction: (owner, repo, filePath, code, action) => request('/tools/code-action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner, repo, file_path: filePath, code, action })
  }),

  generateDoc: (owner, repo, docType) => request('/tools/generate-doc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner, repo, doc_type: docType })
  }),

  analyzeIssue: (owner, repo, number, isPr) => request('/tools/analyze-issue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner, repo, number, is_pr: isPr })
  }),

  getConfig: () => request('/tools/config'),
  updateConfig: (payload) => request('/tools/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }),

  // GitHub Write Actions
  commitFile: (payload) => request('/github/commit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }),

  createBranch: (payload) => request('/github/branch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }),

  createPullRequest: (payload) => request('/github/pull-request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }),

  postComment: (payload) => request('/github/comment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }),

  createIssue: (payload) => request('/github/issue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
};
