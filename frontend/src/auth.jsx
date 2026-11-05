import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as api from "./api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(true);

  // Restore the session on page load
  useEffect(() => {
    let cancelled = false;
    api.setOnSessionExpired(() => setUser(null));
    (async () => {
      try {
        if (api.hasSession()) {
          await api.refreshSession();
          const me = await api.me();
          if (!cancelled) setUser(me);
        }
      } catch {
        api.clearSession();
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (payload) => setUser(await api.login(payload)), []);
  const register = useCallback(async (payload) => setUser(await api.register(payload)), []);
  const logout = useCallback(() => { api.clearSession(); setUser(null); }, []);

  const value = useMemo(
    () => ({ user, booting, login, register, logout }),
    [user, booting, login, register, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
