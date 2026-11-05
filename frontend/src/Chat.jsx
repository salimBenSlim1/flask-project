import { useEffect, useRef, useState } from "react";
import * as api from "./api";
import RichText from "./richtext";

const STARTERS = [
  "Summarize this document in a few sentences",
  "List the key dates, names and numbers",
  "What are the main conclusions?",
];
const STOPWORDS = new Set("what when where which who whom whose this that these those with from about have does your their there then than into over under".split(" "));

function queryTerms(question = "") {
  const words = question.toLowerCase().match(/\p{L}{4,}/gu) || [];
  return [...new Set(words.filter((w) => !STOPWORDS.has(w)))];
}

function Highlighted({ text, terms }) {
  if (!terms.length) return text;
  const re = new RegExp(`(${terms.join("|")})`, "gi");
  return text.split(re).map((part, i) => (i % 2 === 1 ? <mark key={i}>{part}</mark> : part));
}

function Note({ source, active, terms }) {
  const [open, setOpen] = useState(false);
  return (
    <li id={`note-${source.index}`} className={`note${active ? " active" : ""}`}>
      <div className="note-head">
        <span className="tab">p. {source.page}</span>
        <span className="cite static">{source.index}</span>
      </div>
      <button type="button" className={`excerpt${open ? " open" : ""}`} onClick={() => setOpen(!open)} aria-expanded={open}>
        <Highlighted text={source.text} terms={terms} />
      </button>
    </li>
  );
}

function Turn({ question, message }) {
  const [active, setActive] = useState(null);
  const terms = queryTerms(question);
  const streaming = message.status === "streaming";

  return (
    <section className="turn">
      <h3 className="q">{question}</h3>
      <div className="a-grid">
        <div className="a-col">
          {message.status === "error" && (
            <div className="alert" role="alert">{message.error}</div>
          )}
          {(message.content || streaming) && (
            <RichText text={message.content} sources={message.sources} activeNote={active} onCite={setActive} streaming={streaming} />
          )}
          {message.status === "done" && !message.content && <p className="muted">No answer came back. Try rephrasing.</p>}
          {message.stopped && <p className="muted small-note">Stopped.</p>}
        </div>

        {message.sources.length > 0 && (
          <details className="notes" open>
            <summary>Where this comes from ({message.sources.length})</summary>
            <ol>
              {message.sources.map((s) => (
                <Note key={s.index} source={s} active={active === s.index} terms={terms} />
              ))}
            </ol>
          </details>
        )}
      </div>
    </section>
  );
}

export default function Chat({ doc, messages, setThread, onBack, onDelete }) {
  const [text, setText] = useState("");
  const abort = useRef(null);
  const scroller = useRef(null);
  const stick = useRef(true);
  const busy = messages.some((m) => m.status === "streaming");

  // Abort any in-flight answer when switching documents / leaving.
  useEffect(() => () => abort.current?.abort(), []);

  // Keep the newest text in view unless the reader scrolled up.
  useEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const patch = (id, change) =>
    setThread(doc.id, (ms) => ms.map((m) => (m.id === id ? { ...m, ...(typeof change === "function" ? change(m) : change) } : m)));

  async function send(raw) {
    const question = raw.trim();
    if (!question || busy) return;
    const history = messages
      .filter((m) => m.status === "done" && m.content)
      .slice(-6)
      .map(({ role, content }) => ({ role, content }));

    const key = Date.now().toString(36);
    const aid = `${key}-a`;
    setThread(doc.id, (ms) => [
      ...ms,
      { id: `${key}-q`, role: "user", content: question },
      { id: aid, role: "assistant", question, content: "", sources: [], status: "streaming" },
    ]);
    setText("");
    stick.current = true;

    const ctrl = new AbortController();
    abort.current = ctrl;
    try {
      await api.askStream(doc.id, { question, history }, {
        signal: ctrl.signal,
        onSources: (sources) => patch(aid, { sources }),
        onToken: (t) => patch(aid, (m) => ({ content: m.content + t })),
      });
      patch(aid, { status: "done" });
    } catch (err) {
      if (err.name === "AbortError") patch(aid, { status: "done", stopped: true });
      else patch(aid, { status: "error", error: err.message });
    }
  }

  // Pair each question with its answer for rendering
  const turns = [];
  for (let i = 0; i < messages.length; i += 2) turns.push([messages[i], messages[i + 1]]);

  return (
    <section className="chat">
      <header className="chat-head">
        <button className="btn back" onClick={onBack}>Back to documents</button>
        <div className="chat-title">
          <h2>{doc.filename}</h2>
          <span className="muted">{doc.page_count} {doc.page_count === 1 ? "page" : "pages"}</span>
        </div>
        <button className="btn danger small" onClick={onDelete}>Delete</button>
      </header>

      <div
        className="thread"
        ref={scroller}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
        }}
      >
        <div className="thread-inner">
          {turns.length === 0 ? (
            <div className="starter">
              <h3>Ask anything about this document</h3>
              <p className="muted">Answers cite the pages they come from, shown in the margin.</p>
              <div className="starter-list">
                {STARTERS.map((s) => (
                  <button key={s} className="btn" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          ) : (
            turns.map(([q, a]) => <Turn key={q.id} question={q.content} message={a} />)
          )}
        </div>
      </div>

      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <textarea
          value={text}
          rows={1}
          placeholder="Ask a question about this document"
          aria-label="Your question"
          maxLength={1000}
          onChange={(e) => {
            setText(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); }
          }}
        />
        {busy ? (
          <button type="button" className="btn" onClick={() => abort.current?.abort()}>Stop</button>
        ) : (
          <button className="btn primary" disabled={!text.trim()}>Ask</button>
        )}
      </form>
    </section>
  );
}
