import { useEffect, useState } from "react";
import { api, type UserRecord } from "../lib/api";
import { useAuthStore } from "../store/authStore";

const ROLES = ["admin", "editor", "viewer"] as const;

export default function UsersPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "editor" | "viewer">("viewer");
  const [showForm, setShowForm] = useState(false);
  const { user: me } = useAuthStore();

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      setUsers(await api.users.list());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const u = await api.users.create({ email: newEmail, password: newPassword, role: newRole });
      setUsers((prev) => [...prev, u]);
      setNewEmail("");
      setNewPassword("");
      setNewRole("viewer");
      setShowForm(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  }

  async function handleRoleChange(id: string, role: string) {
    try {
      const updated = await api.users.update(id, { role });
      setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update role");
    }
  }

  async function handleToggleActive(u: UserRecord) {
    try {
      const updated = await api.users.update(u.id, { is_active: !u.is_active });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this user permanently?")) return;
    try {
      await api.users.delete(id);
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete user");
    }
  }

  const roleBadge: Record<string, string> = {
    admin: "bg-purple-900/50 text-purple-300 border-purple-800",
    editor: "bg-blue-900/50 text-blue-300 border-blue-800",
    viewer: "bg-zinc-800 text-zinc-400 border-zinc-700",
  };
  const ssoIcon = (subject: string | null) => subject ? (
    <span className="text-[10px] text-text-muted border border-border rounded px-1 py-0.5">
      {subject.split(":")[0].toUpperCase()}
    </span>
  ) : null;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Users</h1>
          <p className="text-sm text-text-secondary mt-1">Manage access to your Nexus workspace</p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover transition-colors"
        >
          {showForm ? "Cancel" : "Invite user"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-md bg-red-950/50 border border-red-900 text-status-error text-sm flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-text-muted hover:text-text-primary">✕</button>
        </div>
      )}

      {/* Create user form */}
      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 p-4 border border-border rounded-lg bg-surface-raised space-y-3">
          <h2 className="text-sm font-medium">New user</h2>
          <div className="grid grid-cols-3 gap-3">
            <input
              type="email"
              placeholder="email@example.com"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              required
              className="col-span-1 px-3 py-2 bg-surface border border-border rounded-md text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
            />
            <input
              type="password"
              placeholder="Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="col-span-1 px-3 py-2 bg-surface border border-border rounded-md text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
            />
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as typeof newRole)}
              className="col-span-1 px-3 py-2 bg-surface border border-border rounded-md text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50"
            >
              {creating ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="text-text-muted text-sm">Loading users…</div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-raised border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wide">User</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wide">Role</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wide">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wide">Auth</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wide">Joined</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((u) => (
                <tr key={u.id} className="bg-surface hover:bg-surface-raised transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-text-primary">{u.email}</div>
                    {u.id === me?.id && <span className="text-[10px] text-accent">you</span>}
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      disabled={u.id === me?.id}
                      className={`text-xs font-medium border rounded px-2 py-0.5 bg-transparent ${roleBadge[u.role] ?? ""} disabled:opacity-60 cursor-pointer`}
                    >
                      {ROLES.map((r) => <option key={r} value={r} className="bg-surface text-text-primary">{r}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggleActive(u)}
                      disabled={u.id === me?.id}
                      className={`text-xs font-medium px-2 py-0.5 rounded border transition-colors disabled:opacity-60 ${
                        u.is_active
                          ? "border-green-800 text-green-400 hover:bg-red-950/30 hover:border-red-800 hover:text-red-400"
                          : "border-red-800 text-red-400 hover:bg-green-950/30 hover:border-green-800 hover:text-green-400"
                      }`}
                    >
                      {u.is_active ? "Active" : "Disabled"}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    {u.sso_subject ? ssoIcon(u.sso_subject) : (
                      <span className="text-[10px] text-text-muted border border-border rounded px-1 py-0.5">PASSWORD</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-text-muted text-xs">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.id !== me?.id && (
                      <button
                        onClick={() => handleDelete(u.id)}
                        className="text-text-muted hover:text-status-error transition-colors text-xs"
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
