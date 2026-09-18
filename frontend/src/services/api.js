const BASE_URL = '/api';

export const api = {
  // Auth & Rate Limit
  getUser: async () => (await fetch(`${BASE_URL}/auth/me`)).json(),
  getRateLimit: async () => (await fetch(`${BASE_URL}/auth/rate-limit`)).json(),

  // GitHub Repos & Files
  getRepositories: async () => (await fetch(`${BASE_URL}/github/repositories?per_page=100`)).json(),
  getRepository: async (owner, repo) => (await fetch(`${BASE_URL}/github/repository/${owner}/${repo}`)).json(),
  createRepository: async (payload) => {
    const res = await fetch(`${BASE_URL}/github/repository`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },
  getSyncStatus: async (autoIndex = true) => (await fetch(`${BASE_URL}/github/sync/status?auto_index=${autoIndex}`)).json(),
  getFileTree: async (owner, repo, branch) => (await fetch(`${BASE_URL}/github/tree/${owner}/${repo}?branch=${branch || 'main'}`)).json(),
  getFileContent: async (owner, repo, path, branch) => (await fetch(`${BASE_URL}/github/file/${owner}/${repo}?path=${encodeURIComponent(path)}&branch=${branch || 'main'}`)).json(),
  getIssues: async (owner, repo) => (await fetch(`${BASE_URL}/github/issues/${owner}/${repo}`)).json(),
  getCommits: async (owner, repo) => (await fetch(`${BASE_URL}/github/commits/${owner}/${repo}`)).json(),

  // ChromaDB RAG
  getIndexStatus: async (owner, repo) => (await fetch(`${BASE_URL}/repository/status/${owner}/${repo}`)).json(),
  indexRepository: async (owner, repo, branch) => {
    const res = await fetch(`${BASE_URL}/repository/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner, repo, branch, max_files: 60 })
    });
    return res.json();
  },

  // Chat
  chat: async (payload) => {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  // AI Tools & Code Actions
  codeAction: async (owner, repo, filePath, code, action) => {
    const res = await fetch(`${BASE_URL}/tools/code-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner, repo, file_path: filePath, code, action })
    });
    return res.json();
  },

  generateDoc: async (owner, repo, docType) => {
    const res = await fetch(`${BASE_URL}/tools/generate-doc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner, repo, doc_type: docType })
    });
    return res.json();
  },

  analyzeIssue: async (owner, repo, number, isPr) => {
    const res = await fetch(`${BASE_URL}/tools/analyze-issue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner, repo, number, is_pr: isPr })
    });
    return res.json();
  },

  getConfig: async () => (await fetch(`${BASE_URL}/tools/config`)).json(),
  updateConfig: async (payload) => {
    const res = await fetch(`${BASE_URL}/tools/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  // GitHub Write Actions
  commitFile: async (payload) => {
    const res = await fetch(`${BASE_URL}/github/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  createBranch: async (payload) => {
    const res = await fetch(`${BASE_URL}/github/branch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  createPullRequest: async (payload) => {
    const res = await fetch(`${BASE_URL}/github/pull-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  postComment: async (payload) => {
    const res = await fetch(`${BASE_URL}/github/comment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  createIssue: async (payload) => {
    const res = await fetch(`${BASE_URL}/github/issue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  }
};
