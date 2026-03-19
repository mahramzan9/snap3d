/**
 * snap3D — Frontend API Client
 * Talks to the FastAPI backend at /api/v1/
 */

const BASE = '/api/v1';

const Auth = {
  getToken: () => localStorage.getItem('snap3d_token'),
  setToken: (t) => localStorage.setItem('snap3d_token', t),
  clearToken: () => localStorage.removeItem('snap3d_token'),
  getUser: () => JSON.parse(localStorage.getItem('snap3d_user') || 'null'),
  setUser: (u) => localStorage.setItem('snap3d_user', JSON.stringify(u)),
  isLoggedIn: () => !!localStorage.getItem('snap3d_token'),
};

alasync function apiFetch(path, opts = {}) {
  const token = Auth.getToken();
  const headers = { ...(opts.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(opts.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (res.status === 401) { Auth.clearToken(); showLoginModal(); throw new Error('Unauthorized'); }
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(err.detail || 'Error'); }
  return res.status === 204 ? null : res.json();
}

function apiGet(path) { return apiFetch(path, { method: 'GET' }); }
function apiPost(path, body) { return apiFetch(path, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) }); }
function apiPatch(path, body) { return apiFetch(path, { method: 'PATCH', body: JSON.stringify(body) }); }
function apiDelete(path) { return apiFetch(path, { method: 'DELETE' }); }

const AuthAPI = {
  async register(email, password, nickname) {
    const data = await apiPost('/auth/register', { email, password, nickname });
    Auth.setToken(data.access_token); Auth.setUser({ id: data.user_id, email: data.email, plan: data.plan });
    return data;
  },
  async login(email, password) {
    const form = new FormData();
    form.append('username', email); form.append('password', password);
    const data = await apiFetch('/auth/login', { method: 'POST', body: form });
    Auth.setToken(data.access_token); Auth.setUser({ id: data.user_id, email: data.email, plan: data.plan });
    return data;
  },
  logout() { Auth.clearToken(); Auth.setUser(null); location.reload(); },
  me() { return apiGet('/auth/me'); },
};

const UploadAPI = {
  async uploadImages(files, quality = 'standard', onProgress) {
    const form = new FormData();
    for (const f of files) form.append('files', f);
    form.append('quality', quality);
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${BASE}/upload/images`);
      const token = Auth.getToken();
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded/e.total)*100)); };
      xhr.onload = () => { if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText)); else reject(new Error(JSON.parse(xhr.responseText).detail || 'Error')); };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(form);
    });
  },
};

const TasksAPI = {
  list: () => apiGet('/tasks'),
  get: (id) => apiGet(`/tasks/${id}`),
  streamProgress(taskId, onProgress, onComplete, onError) {
    const token = Auth.getToken();
    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/v1/tasks/${taskId}/ws?token=${token}`;
    let ws=null,pollTimer=null,stopped=false;
    const stop = () => { stopped=true; if(ws){try{ws.close();}catch(_){}} if(pollTimer)clearInterval(pollTimer); };
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (evt) => { const data=JSON.parse(evt.data); onProgress(data); if(data.status==='success'){onComplete(data);stop();}else if(data.status==='failed'){onError(data.phase);stop();} };
      ws.onerror = () => { ws=null; startPolling(); };
    } catch (_) { startPolling(); }
    function startPolling() {
      if (stopped) return;
      pollTimer = setInterval(async () => {
        if (stopped) return;
        try { const task=await TasksAPI.get(taskId); onProgress(task); if(task.status==='success'){onComplete(task);stop();}else if(task.status==='failed'){onError(task.error_msg);stop();} } catch(e){onError(e.message);stop();}
      }, 3000);
    }
    return stop;
  },
};

const ModelsAPI = {
  list: () => apiGet('/models'),
  get: (id) => apiGet(`/models/${id}`),
  rename: (id, name) => apiPatch(`/models/${id}`, { name }),
  delete: (id) => apiDelete(`/models/${id}`),
  async download(modelId, format, filename) {
    const data = await apiGet(`/models/${modelId}/download/${format}`);
    const a = document.createElement('a'); a.href = data.download_url; a.download = filename || `model.${format}`; a.click();
  },
};

const PrintersAPI = {
  list: () => apiGet('/printers'),
  add: (body) => apiPost('/printers', body),
  delete: (id) => apiDelete(`/printers/${id}`),
  send: (printerId, modelId) => apiPost(`/printers/${printerId}/send`, { model_id: modelId }),
};
