import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Paper,
  Stack,
  TextField,
  Button,
  Alert,
  IconButton,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";

export default function ManageCategoriesPage() {
  const [categories, setCategories] = useState<string[]>([]);
  const [newCategory, setNewCategory] = useState("");
  const [editCategory, setEditCategory] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const fetchCategories = () => {
    fetch("/api/v1/categories")
      .then(res => res.json())
      .then(setCategories)
      .catch(() => setError("Failed to fetch categories"));
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  const handleAdd = async () => {
    setError(""); setMessage("");
    if (!newCategory.trim()) return;
    try {
      const res = await fetch(`/api/v1/categories?name=${encodeURIComponent(newCategory.trim())}`, {
        method: "POST"
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to add category");
      }
      setMessage("Category added!");
      setNewCategory("");
      fetchCategories();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleEdit = (cat: string) => {
    setEditCategory(cat);
    setEditValue(cat);
    setMessage(""); setError("");
  };

  const handleUpdate = async () => {
    if (!editCategory || !editValue.trim()) return;
    setError(""); setMessage("");
    try {
      const res = await fetch(`/api/v1/categories/${encodeURIComponent(editCategory)}?new_name=${encodeURIComponent(editValue.trim())}`, {
        method: "PUT"
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to update category");
      }
      setMessage("Category updated!");
      setEditCategory(null);
      setEditValue("");
      fetchCategories();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (cat: string) => {
    if (!window.confirm(`Delete category "${cat}"?`)) return;
    setError(""); setMessage("");
    try {
      const res = await fetch(`/api/v1/categories/${encodeURIComponent(cat)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to delete category");
      }
      setMessage("Category deleted!");
      fetchCategories();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <Box sx={{ maxWidth: 500, mx: "auto", mt: 4 }}>
      <Typography variant="h5" gutterBottom>Manage Categories</Typography>
      {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2}>
          <TextField
            label="New Category"
            value={newCategory}
            onChange={e => setNewCategory(e.target.value)}
            size="small"
          />
          <Button variant="contained" onClick={handleAdd}>Add</Button>
        </Stack>
      </Paper>
      <Stack spacing={2}>
        {categories.map(cat => (
          <Paper key={cat} sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            {editCategory === cat ? (
              <>
                <TextField
                  value={editValue}
                  onChange={e => setEditValue(e.target.value)}
                  size="small"
                  sx={{ mr: 2 }}
                />
                <Button variant="contained" size="small" onClick={handleUpdate}>Save</Button>
                <Button variant="outlined" size="small" onClick={() => setEditCategory(null)}>Cancel</Button>
              </>
            ) : (
              <>
                <Typography>{cat}</Typography>
                <Box>
                  <IconButton onClick={() => handleEdit(cat)}><EditIcon /></IconButton>
                  <IconButton color="error" onClick={() => handleDelete(cat)}><DeleteIcon /></IconButton>
                </Box>
              </>
            )}
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}