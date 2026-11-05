import { useCallback, useEffect, useState } from "react";
import * as api from "./api";
import { useAuth } from "./auth";
import { ErrorBanner, Field } from "./components";

export default function Posts() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [meta, setMeta] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formError, setFormError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (p) => {
    setLoading(true);
    try {
      const res = await api.listPosts(p);
      if (res.data.length === 0 && p > 1) return setPage(p - 1); // deleted the last item on a page
      setPosts(res.data);
      setMeta(res.meta);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(page); }, [page, load]);

  async function onCreate(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const payload = Object.fromEntries(new FormData(form));
    setFormError(null);
    setBusy(true);
    try {
      await api.createPost(payload);
      form.reset();
      page === 1 ? await load(1) : setPage(1);
    } catch (err) {
      setFormError(err);
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id) {
    setError(null);
    try {
      await api.deletePost(id);
      await load(page);
    } catch (err) {
      setError(err);
    }
  }

  const fe = formError?.details || {};
  const canDelete = (p) => p.author.id === user.id || user.role === "admin";

  return (
    <div className="posts">
      <main className="content">
        <form className="card" onSubmit={onCreate} noValidate>
          <h2>New post</h2>
          <ErrorBanner error={formError} />
          <Field label="Title" name="title" errors={fe.title} />
          <Field label="Body" name="body" as="textarea" rows={3} errors={fe.body} />
          <button className="btn primary" disabled={busy}>{busy ? "Publishing…" : "Publish"}</button>
        </form>

        <section>
          <h2>Posts {meta && <small className="muted">({meta.total})</small>}</h2>
          <ErrorBanner error={error} />
          {loading && posts.length === 0 && <p className="muted">Loading…</p>}
          {!loading && !error && posts.length === 0 && <p className="muted">No posts yet.</p>}

          {posts.map((p) => (
            <article className="card post" key={p.id}>
              <div className="post-head">
                <h3>{p.title}</h3>
                {canDelete(p) && (
                  <button className="btn danger" onClick={() => onDelete(p.id)}>Delete</button>
                )}
              </div>
              <p>{p.body}</p>
              <small className="muted">
                by {p.author.name} · {new Date(p.created_at).toLocaleString()}
              </small>
            </article>
          ))}

          {meta && meta.pages > 1 && (
            <div className="pager">
              <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Prev</button>
              <span className="muted">Page {meta.page} / {meta.pages}</span>
              <button className="btn" disabled={page >= meta.pages} onClick={() => setPage(page + 1)}>Next →</button>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
