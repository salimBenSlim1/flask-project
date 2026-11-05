// Minimal renderer for model answers: paragraphs, lists, **bold**, `code` and [n] citations.
const INLINE = /(\*\*[^*\n]+\*\*|`[^`\n]+`|\[\d+\])/g;
const LIST_ITEM = /^\s*(?:[-*•]|\d+[.)])\s+(.*)/;

function toBlocks(text) {
  const blocks = [];
  let list = null;
  for (const line of text.split("\n")) {
    const item = line.match(LIST_ITEM);
    if (item) {
      const ordered = /^\s*\d/.test(line);
      if (!list || list.ordered !== ordered) {
        list = { type: "list", ordered, items: [] };
        blocks.push(list);
      }
      list.items.push(item[1]);
      continue;
    }
    list = null;
    if (!line.trim()) {
      blocks.push({ type: "gap" });
      continue;
    }
    const last = blocks[blocks.length - 1];
    if (last && last.type === "p") last.lines.push(line);
    else blocks.push({ type: "p", lines: [line] });
  }
  return blocks.filter((b) => b.type !== "gap");
}

function Inline({ text, sources, activeNote, onCite }) {
  return text.split(INLINE).map((part, i) => {
    if (!part) return null;
    if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
    const cite = part.match(/^\[(\d+)\]$/);
    if (cite && sources.some((s) => s.index === Number(cite[1]))) {
      const n = Number(cite[1]);
      return (
        <button
          key={i}
          type="button"
          className="cite"
          aria-label={`Show source ${n}`}
          aria-pressed={activeNote === n}
          onMouseEnter={() => onCite(n)}
          onFocus={() => onCite(n)}
          onClick={() => onCite(n)}
        >
          {n}
        </button>
      );
    }
    return part;
  });
}

export default function RichText({ text, sources = [], activeNote, onCite = () => {}, streaming = false }) {
  const blocks = toBlocks(text);
  const props = { sources, activeNote, onCite };
  return (
    <div className="answer">
      {blocks.map((b, i) => {
        const isLast = i === blocks.length - 1;
        const caret = streaming && isLast ? <span className="caret" aria-hidden="true" /> : null;
        if (b.type === "list") {
          const Tag = b.ordered ? "ol" : "ul";
          return (
            <Tag key={i}>
              {b.items.map((it, j) => (
                <li key={j}>
                  <Inline text={it} {...props} />
                  {caret && j === b.items.length - 1 ? caret : null}
                </li>
              ))}
            </Tag>
          );
        }
        return (
          <p key={i}>
            <Inline text={b.lines.join(" ")} {...props} />
            {caret}
          </p>
        );
      })}
      {streaming && blocks.length === 0 && <p><span className="caret" aria-hidden="true" /></p>}
    </div>
  );
}
