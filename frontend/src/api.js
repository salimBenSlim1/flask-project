// Tiny API client: error normalisation + automatic token refresh.
// Access token lives in memory only; the refresh token is persisted so a reload keeps you signed in.
const BASE = "/api";
const REFRESH_KEY = "refresh_token";

let accessToken = null;
let refreshing = null; // shared promise so parallel 401s trigger only one refresh
let onSessionExpired = () => {};

export const setOnSessionExpired = (fn) => (onSessionExpired = fn);

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details; // { field: ["msg", ...] } for validation errors
  }
}

const store = {
  get: () => { try { return localStorage.getItem(REFRESH_KEY); } catch { return null; } },
  set: (v) => { try { localStorage.setItem(REFRESH_KEY, v); } catch { /* storage unavailable */ } },
  clear: () => { try { localStorage.removeItem(REFRESH_KEY); } catch { /* ignore */ } },
};

export const hasSession = () => Boolean(store.get());

export function clearSession() {
  accessToken = null;
  store.clear();
}

function saveSession(data) {
  accessToken = data.access_token;
  if (data.refresh_token) store.set(data.refresh_token);
}

async function send(path, { method = "GET", body, token } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the server. Please try again.");
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null); // proxies can return HTML on 502/504

  if (!res.ok) {
    const e = data?.error;
    throw new ApiError(res.status, e?.code ?? "unknown_error", e?.message ?? `Server error (${res.status})`, e?.details);
  }
  return data;
}

export function refreshSession() {
  if (!refreshing) {
    refreshing = send("/auth/refresh", { method: "POST", body: { refresh_token: store.get() } })
      .then(saveSession)
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

async function authed(path, opts = {}) {
  try {
    return await send(path, { ...opts, token: accessToken });
  } catch (err) {
    if (err.status !== 401 || !hasSession()) throw err;
    try {
      await refreshSession();
    } catch {
      clearSession();
      onSessionExpired();
      throw new ApiError(401, "session_expired", "Your session expired. Please sign in again.");
    }
    return send(path, { ...opts, token: accessToken }); // retry once with the new token
  }
}

export async function register(payload) {
  const data = await send("/auth/register", { method: "POST", body: payload });
  saveSession(data);
  return data.user;
}

export async function login(payload) {
  const data = await send("/auth/login", { method: "POST", body: payload });
  saveSession(data);
  return data.user;
}

export const me = async () => (await authed("/auth/me")).user;
export const listPosts = (page = 1) => send(`/posts?page=${page}&per_page=5`);
export const createPost = (payload) => authed("/posts", { method: "POST", body: payload });
export const deletePost = (id) => authed(`/posts/${id}`, { method: "DELETE" });
