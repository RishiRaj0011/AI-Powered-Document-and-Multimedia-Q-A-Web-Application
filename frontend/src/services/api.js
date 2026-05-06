import axios from "axios";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------
const api = axios.create({ baseURL: "/api/v1" });

// ---------------------------------------------------------------------------
// Request interceptor — attach access token
// ---------------------------------------------------------------------------
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ---------------------------------------------------------------------------
// Response interceptor — refresh on 401, retry once, then redirect to /login
// ---------------------------------------------------------------------------
let _refreshing = false;
let _queue = []; // pending requests while refresh is in flight

function _processQueue(error, token = null) {
  _queue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(token)
  );
  _queue = [];
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    // Don't try to refresh if the failing request IS the refresh call
    if (original.url?.includes("/auth/refresh")) {
      _clearAuth();
      return Promise.reject(error);
    }

    if (_refreshing) {
      // Queue this request until the refresh resolves
      return new Promise((resolve, reject) => {
        _queue.push({ resolve, reject });
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      });
    }

    original._retry = true;
    _refreshing = true;

    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      _clearAuth();
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post("/api/v1/auth/refresh", {
        refresh_token: refreshToken,
      });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
      _processQueue(null, data.access_token);
      original.headers.Authorization = `Bearer ${data.access_token}`;
      return api(original);
    } catch (refreshError) {
      _processQueue(refreshError, null);
      _clearAuth();
      return Promise.reject(refreshError);
    } finally {
      _refreshing = false;
    }
  }
);

function _clearAuth() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

// ---------------------------------------------------------------------------
// Named API groups
// ---------------------------------------------------------------------------
export const authAPI = {
  register: (email, password, fullName) =>
    api.post("/auth/register", { email, password, full_name: fullName }).then((r) => r.data),
  login: (email, password) =>
    api.post("/auth/login", { email, password }).then((r) => r.data),
  refresh: (refreshToken) =>
    api.post("/auth/refresh", { refresh_token: refreshToken }).then((r) => r.data),
  me: () => api.get("/auth/me").then((r) => r.data),
  logout: () => api.post("/auth/logout").then((r) => r.data),
};

export const documentsAPI = {
  upload: (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post("/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (onProgress && e.total) {
            onProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      })
      .then((r) => r.data);
  },
  list: () => api.get("/documents/").then((r) => r.data),
  get: (id) => api.get(`/documents/${id}`).then((r) => r.data),
  getStatus: (id) => api.get(`/documents/${id}/status`).then((r) => r.data),
  delete: (id) => api.delete(`/documents/${id}`),
  getSummary: (id) => api.get(`/documents/${id}/summary`).then((r) => r.data),
  getTopics: (id) => api.get(`/documents/${id}/topics`).then((r) => r.data),
};

export const chatAPI = {
  createSession: (documentId) =>
    api.post("/chat/sessions", { document_id: documentId }).then((r) => r.data),
  getSessions: () => api.get("/chat/sessions").then((r) => r.data),
  getSession: (id) => api.get(`/chat/sessions/${id}`).then((r) => r.data),
  sendMessage: (sessionId, question) =>
    api
      .post(`/chat/sessions/${sessionId}/messages`, { question })
      .then((r) => r.data),
  // SSE streaming — returns a native EventSource-compatible URL
  getStreamUrl: (sessionId, question) =>
    `/api/v1/chat/sessions/${sessionId}/stream?question=${encodeURIComponent(question)}`,
};

export default api;
