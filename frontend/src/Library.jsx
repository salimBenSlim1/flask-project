import { useRef, useState } from "react";
import { ErrorBanner } from "./components";

function statusText(doc) {
  if (doc.status === "processing") return "Reading…";
  if (doc.status === "failed") return "Couldn't read this file";
  return doc.page_count === 1 ? "1 page" : `${doc.page_count} pages`;
}

export default function Library({ docs, selectedId, onSelect, onUpload, uploading, error }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);

  function pick(files) {
    const file = files?.[0];
    if (file) onUpload(file);
  }

  return (
    <aside
      className={`library${dragging ? " dragging" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files); }}
    >
      <div className="library-head">
        <h2>Documents</h2>
        <button className="btn primary small" onClick={() => input.current.click()} disabled={uploading}>
          {uploading ? "Uploading…" : "Upload PDF"}
        </button>
        <input
          ref={input}
          type="file"
          accept="application/pdf"
          hidden
          onChange={(e) => { pick(e.target.files); e.target.value = ""; }}
        />
      </div>

      <ErrorBanner error={error} />

      {docs === null && <p className="muted pad">Loading…</p>}
      {docs?.length === 0 && (
        <p className="muted pad">Drop a PDF here or use Upload PDF. Your files are private to you.</p>
      )}

      <ul className="doc-list">
        {docs?.map((d) => (
          <li key={d.id}>
            <button
              className={`doc ${d.status}`}
              aria-current={d.id === selectedId ? "true" : undefined}
              onClick={() => onSelect(d.id)}
            >
              <span className="doc-name">{d.filename}</span>
              <span className="doc-status">{statusText(d)}</span>
              {d.status === "processing" && <span className="bar" aria-hidden="true" />}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
