import React, { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

type User = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
};

export default function UserManagementPage() {
  const { token, user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUsers() {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/auth/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setUsers(await res.json());
      }
      setLoading(false);
    }
    fetchUsers();
  }, [token]);

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this user?")) return;
    const res = await fetch(`${API_BASE_URL}/users/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      setUsers(users.filter(u => u.id !== id));
      alert("User deleted.");
    } else {
      alert("Failed to delete user.");
    }
  };

    const handleRoleChange = async (id: string, newRole: string) => {
        const res = await fetch(`${API_BASE_URL}/users/${id}/role?role=${encodeURIComponent(newRole)}`, {
            method: "PUT",
            headers: {
            Authorization: `Bearer ${token}`,
            },
        });
        if (res.ok) {
            setUsers(users.map(u => u.id === id ? { ...u, role: newRole } : u));
            alert("Role updated.");
        } else {
            let errorMsg = "Failed to update role.";
            try {
            const data = await res.json();
            if (data && data.detail) {
                errorMsg += ` ${typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)}`;
            }
            } catch (e) {}
            alert(errorMsg);
        }
    };

  if (loading) return <div>Loading users...</div>;

  return (
    <div>
      <h2>User Management</h2>
      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>
                <select
                  value={u.role}
                  onChange={e => handleRoleChange(u.id, e.target.value)}
                  disabled={u.id === user?.id}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td>{u.is_active ? "Yes" : "No"}</td>
              <td>
                <button onClick={() => handleDelete(u.id)} disabled={u.id === user?.id}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}