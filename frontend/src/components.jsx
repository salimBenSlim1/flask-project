// Shows the API's message; per-field validation details are rendered under each input.
export function ErrorBanner({ error }) {
  if (!error) return null;
  const text = error.code === "validation_error" ? "Please fix the errors below." : error.message;
  return <div className="alert" role="alert">{text}</div>;
}

export function Field({ label, errors, as: Tag = "input", ...props }) {
  const msg = errors ? (Array.isArray(errors) ? errors.join(" ") : String(errors)) : null;
  return (
    <label className="field">
      <span>{label}</span>
      <Tag {...props} aria-invalid={Boolean(msg)} />
      {msg && <small className="field-error">{msg}</small>}
    </label>
  );
}
