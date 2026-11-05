import AuthPage from "./AuthPage";
import Dashboard from "./Dashboard";
import { useAuth } from "./auth";

export default function App() {
  const { user, booting } = useAuth();
  if (booting) return <p className="muted center">Loading…</p>;
  return user ? <Dashboard /> : <AuthPage />;
}
