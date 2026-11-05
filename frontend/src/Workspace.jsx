import { useCallback, useEffect, useState } from "react";
import * as api from "./api";
import Chat from "./Chat";
import Library from "./Library";

export default function Workspace() {
  const [docs, setDocs] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [threads, setThreads] = useState({});
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await api.listDocuments());
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Open the newest ready document on desktop; on mobile start from the library.
  useEffect(() => {
    if (docs && selectedId === null && window.matchMedia("(min-width: 861px)").matches) {
      const first = docs.find((d) => d.status === "ready");
      if (first) setSelectedId(first.id);
    }
  }, [docs, selectedId]);

  // Poll while something is being processed.
  const processing = docs?.some((d) => d.status === "processing");
  useEffect(() => {
    if (!processing) return undefined;
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, [processing, refresh]);

  const setThread = useCallback(
    (id, update) => setThreads((t) => ({ ...t, [id]: update(t[id] || []) })),
    []
  );

  async function onUpload(file) {
    setUploading(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file);
      setDocs((d) => [doc, ...(d || [])]);
      setSelectedId(doc.id);
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(doc) {
    if (!window.confirm(`Delete “${doc.filename}” and its conversation?`)) return;
    try {
      await api.deleteDocument(doc.id);
      setDocs((d) => d.filter((x) => x.id !== doc.id));
      setThreads(({ [doc.id]: _gone, ...rest }) => rest);
      setSelectedId(null);
    } catch (err) {
      setError(err);
    }
  }

  const doc = docs?.find((d) => d.id === selectedId) || null;

  return (
    <div className="workspace" data-view={doc ? "chat" : "library"}>
      <Library docs={docs} selectedId={selectedId} onSelect={setSelectedId} onUpload={onUpload} uploading={uploading} error={error} />

      <main className="stage">
        {!doc && (
          <div className="state">
            <h2>Ask your documents</h2>
            <p className="muted">Upload a PDF, then ask questions. Every answer points back to the pages it used.</p>
          </div>
        )}

        {doc?.status === "processing" && (
          <div className="state">
            <h2>Reading “{doc.filename}”</h2>
            <p className="muted">Splitting it into passages and indexing them. This usually takes a few seconds.</p>
            <span className="bar wide" aria-hidden="true" />
          </div>
        )}

        {doc?.status === "failed" && (
          <div className="state">
            <h2>We couldn’t read this file</h2>
            <p className="alert" role="alert">{doc.error}</p>
            <button className="btn danger" onClick={() => onDelete(doc)}>Delete file</button>
          </div>
        )}

        {doc?.status === "ready" && (
          <Chat
            key={doc.id}
            doc={doc}
            messages={threads[doc.id] || []}
            setThread={setThread}
            onBack={() => setSelectedId(null)}
            onDelete={() => onDelete(doc)}
          />
        )}
      </main>
    </div>
  );
}
