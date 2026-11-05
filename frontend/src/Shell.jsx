import { useState } from "react";
import Posts from "./Posts";
import Workspace from "./Workspace";
import { useAuth } from "./auth";

export default function Shell() {
  const { user, logout } = useAuth();
  const [view, setView] = useState("documents");

  return (
    <div className="shell">
      <header className="topbar">
        <strong className="brand">Marginalia</strong>
        <nav className="tabs" aria-label="Sections">
          <button aria-current={view === "documents" ? "page" : undefined} onClick={() => setView("documents")}>Documents</button>
          <button aria-current={view === "posts" ? "page" : undefined} onClick={() => setView("posts")}>Posts</button>
        </nav>
        <div className="who">
          <span>{user.name}</span>
          <em className={`badge ${user.role}`}>{user.role}</em>
          <button className="btn small" onClick={logout}>Log out</button>
        </div>
      </header>
      <div className="view">{view === "documents" ? <Workspace /> : <Posts />}</div>
    </div>
  );
}
