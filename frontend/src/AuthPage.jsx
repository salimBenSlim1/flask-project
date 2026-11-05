import { useState } from "react";
import { useAuth } from "./auth";
import { ErrorBanner, Field } from "./components";

export default function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function onSubmit(e) {
    e.preventDefault();
    const payload = Object.fromEntries(new FormData(e.currentTarget));
    setError(null);
    setBusy(true);
    try {
      await (isLogin ? login(payload) : register(payload));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function switchMode() {
    setError(null);
    setMode(isLogin ? "register" : "login");
  }

  const fe = error?.details || {};

  return (
    <main className="auth">
      <form className="card" onSubmit={onSubmit} key={mode} noValidate>
        <p className="brand">Marginalia</p>
        <h1>{isLogin ? "Sign in" : "Create your account"}</h1>
        <p className="muted tagline">Ask questions about your PDFs and see which pages each answer comes from.</p>
        <ErrorBanner error={error} />

        {!isLogin && <Field label="Name" name="name" autoComplete="name" errors={fe.name} />}
        <Field label="Email" name="email" type="email" autoComplete="email" errors={fe.email} />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete={isLogin ? "current-password" : "new-password"}
          errors={fe.password}
        />

        <button className="btn primary" disabled={busy}>
          {busy ? "Please wait…" : isLogin ? "Sign in" : "Sign up"}
        </button>

        <p className="muted">
          {isLogin ? "No account yet?" : "Already registered?"}{" "}
          <button type="button" className="link" onClick={switchMode}>
            {isLogin ? "Sign up" : "Sign in"}
          </button>
        </p>
        {isLogin && <p className="hint">Demo: alice@example.com / Alice1234!</p>}
      </form>
    </main>
  );
}
