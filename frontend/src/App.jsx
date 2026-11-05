import AuthPage from "./AuthPage";
import Shell from "./Shell";
import { useAuth } from "./auth";

export default function App() {
  const { user, booting } = useAuth();
  if (booting) return <p className="muted center">Loading…</p>;
  return user ? <Shell /> : <AuthPage />;
}
