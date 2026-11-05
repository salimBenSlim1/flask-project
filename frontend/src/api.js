// API client: error normalisation, automatic token refresh, multipart upload, SSE streaming.
// Access token lives in memory only; the refresh token is persisted so a reload keeps you signed in.
//
// VITE_API_URL (optional): call the backend directly (needed for big uploads/streaming on hosts
// whose proxies cap bodies or buffer responses). Empty = same-origin /api via proxy/rewrite.
const BASE = `${(import.meta.env.VITE_API_URL || "").replace(/\/$/, "")}/api`;
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

async function rawFetch(path, { method = "GET", json, form, token, signal } = {}) {
  const headers = {};
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form; // the browser sets the multipart boundary itself
  }
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    return await fetch(BASE + path, { method, headers, body, signal });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", "Cannot reach the server. Please try again.");
  }
}

async function toError(res) {
  const data = await res.json().catch(() => null); // proxies can return HTML on 502/504
  const e = data?.error;
  return new ApiError(res.status, e?.code ?? "unknown_error", e?.message ?? `Server error (${res.status})`, e?.details);
}

async function parse(res) {
  if (res.status === 204) return null;
  if (!res.ok) throw await toError(res);
  return res.json();
}

export function refreshSession() {
  if (!refreshing) {
    refreshing = rawFetch("/auth/refresh", { method: "POST", json: { refresh_token: store.get() } })
      .then(parse)
      .then(saveSession)
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

// Fetch with the access token; on 401 refresh once and retry.
async function authedResponse(path, opts = {}) {
  let res = await rawFetch(path, { ...opts, token: accessToken });
  if (res.status === 401 && hasSession()) {
    try {
      await refreshSession();
    } catch {
      clearSession();
      onSessionExpired();
      throw new ApiError(401, "session_expired", "Your session expired. Please sign in again.");
    }
    res = await rawFetch(path, { ...opts, token: accessToken });
  }
  return res;
}

const authed = async (path, opts) => parse(await authedResponse(path, opts));

// ---- auth ----
export async function register(payload) {
  const data = await parse(await rawFetch("/auth/register", { method: "POST", json: payload }));
  saveSession(data);
  return data.user;
}

export async function login(payload) {
  const data = await parse(await rawFetch("/auth/login", { method: "POST", json: payload }));
  saveSession(data);
  return data.user;
}

export const me = async () => (await authed("/auth/me")).user;

// ---- posts ----
export const listPosts = async (page = 1) => parse(await rawFetch(`/posts?page=${page}&per_page=5`));
export const createPost = (payload) => authed("/posts", { method: "POST", json: payload });
export const deletePost = (id) => authed(`/posts/${id}`, { method: "DELETE" });

// ---- documents (RAG) ----
export const listDocuments = async () => (await authed("/documents")).data;

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  return (await authed("/documents", { method: "POST", form })).data;
}

export const deleteDocument = (id) => authed(`/documents/${id}`, { method: "DELETE" });

// Streams an answer. Server-sent events: `sources` once, many `token`, then `done` (or `error`).
export async function askStream(docId, { question, history }, { signal, onSources, onToken }) {
  const res = await authedResponse(`/documents/${docId}/ask`, {
    method: "POST",
    json: { question, history, stream: true },
    signal,
  });
  if (!res.ok) throw await toError(res);

  const handle = (raw) => {
    let event = "message";
    let data = "";
    for (const line of raw.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    if (!data) return;
    const payload = JSON.parse(data);
    if (event === "sources") onSources(payload);
    else if (event === "token") onToken(payload.text);
    else if (event === "error") throw new ApiError(502, payload.code, payload.message);
  };

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      handle(buffer.slice(0, end));
      buffer = buffer.slice(end + 2);
    }
  }
}
