import { useEffect, useMemo, useState, type ReactNode } from "react";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EmailIcon from "@mui/icons-material/Email";
import FilterListIcon from "@mui/icons-material/FilterList";
import GroupIcon from "@mui/icons-material/Group";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import SecurityIcon from "@mui/icons-material/Security";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  deleteUser,
  listUsers,
  updateUserActive,
  updateUserRole,
  updateUserVerified,
} from "../api/endpoints";
import type { Me, Role } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RoleFilter = "all" | Role;
type StatusFilter = "all" | "active" | "inactive" | "verified" | "unverified";
type UserAction = "role" | "active" | "verified" | "delete";

function formatDate(value?: string | null): string {
  if (!value) return "Never";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Never";

  return date.toLocaleString([], {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object") {
    const maybeMessage = (error as { message?: unknown }).message;
    if (maybeMessage) return String(maybeMessage);
  }

  return "The user operation failed.";
}

function userInitial(email: string): string {
  return email.slice(0, 1).toUpperCase();
}

function shortId(id: string): string {
  return `${id.slice(0, 8)}...${id.slice(-4)}`;
}

function roleColor(role: Role) {
  return role === "admin" ? "secondary" : "default";
}

export default function UserManagementPage() {
  const { token, user, updateUser } = useAuth();
  const [users, setUsers] = useState<Me[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ severity: "success" | "error" | "info"; message: string } | null>(null);
  const [busyUserActions, setBusyUserActions] = useState<Record<string, UserAction | undefined>>({});
  const [deleteTarget, setDeleteTarget] = useState<Me | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  async function refreshUsers(showMessage = false) {
    if (!token) {
      setLoading(false);
      setFeedback({ severity: "error", message: "Admin token is missing." });
      return;
    }

    setLoading(true);
    setFeedback(null);

    try {
      const rows = await listUsers(token);
      setUsers(rows);
      if (showMessage) setFeedback({ severity: "success", message: "User list refreshed." });
    } catch (error) {
      setFeedback({ severity: "error", message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshUsers();
  }, [token]);

  const stats = useMemo(() => {
    const total = users.length;
    const admins = users.filter(row => row.role === "admin").length;
    const active = users.filter(row => row.is_active).length;
    const unverified = users.filter(row => !row.is_verified).length;

    return { total, admins, active, unverified };
  }, [users]);

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase();

    return users.filter(row => {
      const matchesSearch =
        query.length === 0 ||
        row.email.toLowerCase().includes(query) ||
        row.id.toLowerCase().includes(query);
      const matchesRole = roleFilter === "all" || row.role === roleFilter;
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && row.is_active) ||
        (statusFilter === "inactive" && !row.is_active) ||
        (statusFilter === "verified" && row.is_verified) ||
        (statusFilter === "unverified" && !row.is_verified);

      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [roleFilter, search, statusFilter, users]);

  const pagedUsers = useMemo(
    () => filteredUsers.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [filteredUsers, page, rowsPerPage],
  );

  useEffect(() => {
    setPage(0);
  }, [roleFilter, rowsPerPage, search, statusFilter]);

  function setBusy(userId: string, action: UserAction | undefined) {
    setBusyUserActions(prev => ({ ...prev, [userId]: action }));
  }

  function replaceUser(updated: Me) {
    setUsers(prev => prev.map(row => (row.id === updated.id ? updated : row)));

    if (updated.id === user?.id) {
      updateUser(updated);
    }
  }

  async function handleRoleChange(target: Me, nextRole: Role) {
    if (!token || target.role === nextRole) return;

    setBusy(target.id, "role");
    setFeedback(null);

    try {
      const updated = await updateUserRole(token, target.id, nextRole);
      replaceUser(updated);
      setFeedback({ severity: "success", message: `${target.email} is now ${nextRole}.` });
    } catch (error) {
      setFeedback({ severity: "error", message: getErrorMessage(error) });
    } finally {
      setBusy(target.id, undefined);
    }
  }

  async function handleActiveChange(target: Me, checked: boolean) {
    if (!token || target.is_active === checked) return;

    setBusy(target.id, "active");
    setFeedback(null);

    try {
      const updated = await updateUserActive(token, target.id, checked);
      replaceUser(updated);
      setFeedback({
        severity: "success",
        message: checked ? `${target.email} can sign in.` : `${target.email} has been deactivated.`,
      });
    } catch (error) {
      setFeedback({ severity: "error", message: getErrorMessage(error) });
    } finally {
      setBusy(target.id, undefined);
    }
  }

  async function handleVerifiedChange(target: Me, checked: boolean) {
    if (!token || target.is_verified === checked) return;

    setBusy(target.id, "verified");
    setFeedback(null);

    try {
      const updated = await updateUserVerified(token, target.id, checked);
      replaceUser(updated);
      setFeedback({
        severity: "success",
        message: checked ? `${target.email} is marked verified.` : `${target.email} is marked unverified.`,
      });
    } catch (error) {
      setFeedback({ severity: "error", message: getErrorMessage(error) });
    } finally {
      setBusy(target.id, undefined);
    }
  }

  async function handleDeleteConfirmed() {
    if (!token || !deleteTarget) return;

    setBusy(deleteTarget.id, "delete");
    setFeedback(null);

    try {
      await deleteUser(token, deleteTarget.id);
      setUsers(prev => prev.filter(row => row.id !== deleteTarget.id));
      setFeedback({ severity: "success", message: `${deleteTarget.email} was deleted.` });
      setDeleteTarget(null);
    } catch (error) {
      setFeedback({ severity: "error", message: getErrorMessage(error) });
    } finally {
      setBusy(deleteTarget.id, undefined);
    }
  }

  function clearFilters() {
    setSearch("");
    setRoleFilter("all");
    setStatusFilter("all");
  }

  return (
    <Box sx={{ maxWidth: 1240, mx: "auto", px: { xs: 2, md: 3 }, py: { xs: 2, md: 4 } }}>
      <Stack spacing={2.5}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr auto" },
            gap: 2,
            alignItems: "center",
          }}
        >
          <Box>
            <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 0.75 }}>
              <AdminPanelSettingsIcon color="primary" />
              <Typography variant="h4">User Management</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Manage account access, roles, verification, and destructive user operations.
            </Typography>
          </Box>

          <Button
            variant="outlined"
            startIcon={loading ? <CircularProgress size={18} /> : <RefreshIcon />}
            onClick={() => void refreshUsers(true)}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>

        {feedback && (
          <Alert severity={feedback.severity} onClose={() => setFeedback(null)}>
            {feedback.message}
          </Alert>
        )}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" },
            gap: 1.5,
          }}
        >
          <MetricCard icon={<GroupIcon />} label="Total users" value={stats.total} />
          <MetricCard icon={<SecurityIcon />} label="Admins" value={stats.admins} />
          <MetricCard icon={<LockOpenIcon />} label="Active" value={stats.active} />
          <MetricCard icon={<WarningAmberIcon />} label="Unverified" value={stats.unverified} tone="warning" />
        </Box>

        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <Stack direction="row" spacing={1.25} alignItems="center">
                <FilterListIcon color="primary" />
                <Typography variant="h6">Directory</Typography>
                <Chip size="small" label={`${filteredUsers.length} shown`} />
              </Stack>

              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "minmax(280px, 1fr) 180px 190px auto" },
                  gap: 1.25,
                  alignItems: "center",
                }}
              >
                <TextField
                  label="Search users"
                  value={search}
                  onChange={event => setSearch(event.target.value)}
                  fullWidth
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                />

                <FormControl fullWidth>
                  <InputLabel id="role-filter-label">Role</InputLabel>
                  <Select
                    labelId="role-filter-label"
                    label="Role"
                    value={roleFilter}
                    onChange={event => setRoleFilter(event.target.value as RoleFilter)}
                  >
                    <MenuItem value="all">All roles</MenuItem>
                    <MenuItem value="admin">Admins</MenuItem>
                    <MenuItem value="user">Users</MenuItem>
                  </Select>
                </FormControl>

                <FormControl fullWidth>
                  <InputLabel id="status-filter-label">Status</InputLabel>
                  <Select
                    labelId="status-filter-label"
                    label="Status"
                    value={statusFilter}
                    onChange={event => setStatusFilter(event.target.value as StatusFilter)}
                  >
                    <MenuItem value="all">All statuses</MenuItem>
                    <MenuItem value="active">Active</MenuItem>
                    <MenuItem value="inactive">Inactive</MenuItem>
                    <MenuItem value="verified">Verified</MenuItem>
                    <MenuItem value="unverified">Unverified</MenuItem>
                  </Select>
                </FormControl>

                <Button variant="outlined" onClick={clearFilters}>
                  Clear
                </Button>
              </Box>

              <Divider />

              <TableContainer sx={{ overflowX: "auto" }}>
                <Table size="small" aria-label="User management table">
                  <TableHead>
                    <TableRow>
                      <TableCell>User</TableCell>
                      <TableCell width={160}>Role</TableCell>
                      <TableCell width={210}>Access</TableCell>
                      <TableCell>Preferences</TableCell>
                      <TableCell width={190}>Activity</TableCell>
                      <TableCell align="right" width={90}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {loading && users.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <Stack direction="row" spacing={1} alignItems="center" sx={{ py: 3 }}>
                            <CircularProgress size={20} />
                            <Typography variant="body2">Loading users...</Typography>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    )}

                    {!loading && filteredUsers.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <Alert severity="info">No users match the current filters.</Alert>
                        </TableCell>
                      </TableRow>
                    )}

                    {pagedUsers.map(row => {
                      const isSelf = row.id === user?.id;
                      const busy = busyUserActions[row.id];
                      const disabled = Boolean(busy);

                      return (
                        <TableRow key={row.id} hover>
                          <TableCell>
                            <Stack direction="row" spacing={1.25} alignItems="center">
                              <Avatar sx={{ width: 40, height: 40, bgcolor: row.role === "admin" ? "secondary.main" : "primary.main" }}>
                                {userInitial(row.email)}
                              </Avatar>
                              <Box sx={{ minWidth: 0 }}>
                                <Stack direction="row" spacing={0.75} alignItems="center" sx={{ flexWrap: "wrap", gap: 0.75 }}>
                                  <Typography variant="subtitle2" sx={{ overflowWrap: "anywhere" }}>
                                    {row.email}
                                  </Typography>
                                  {isSelf && <Chip size="small" label="You" color="primary" />}
                                </Stack>
                                <Typography variant="caption" color="text.secondary">
                                  {shortId(row.id)}
                                </Typography>
                              </Box>
                            </Stack>
                          </TableCell>

                          <TableCell>
                            <FormControl size="small" fullWidth>
                              <Select
                                value={row.role}
                                onChange={event => void handleRoleChange(row, event.target.value as Role)}
                                disabled={disabled || isSelf}
                              >
                                <MenuItem value="user">User</MenuItem>
                                <MenuItem value="admin">Admin</MenuItem>
                              </Select>
                            </FormControl>
                            <Box sx={{ mt: 0.75 }}>
                              <Chip size="small" label={row.role} color={roleColor(row.role)} />
                            </Box>
                          </TableCell>

                          <TableCell>
                            <Stack spacing={0.5}>
                              <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                                <Typography variant="caption">Active</Typography>
                                <Switch
                                  checked={row.is_active}
                                  size="small"
                                  onChange={(_, checked) => void handleActiveChange(row, checked)}
                                  disabled={disabled || isSelf}
                                />
                              </Stack>
                              <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                                <Typography variant="caption">Verified</Typography>
                                <Switch
                                  checked={row.is_verified}
                                  size="small"
                                  onChange={(_, checked) => void handleVerifiedChange(row, checked)}
                                  disabled={disabled || isSelf}
                                />
                              </Stack>
                              {busy && (
                                <Stack direction="row" spacing={0.75} alignItems="center">
                                  <CircularProgress size={14} />
                                  <Typography variant="caption" color="text.secondary">
                                    Updating {busy}
                                  </Typography>
                                </Stack>
                              )}
                            </Stack>
                          </TableCell>

                          <TableCell>
                            <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap", gap: 0.75 }}>
                              <Chip
                                size="small"
                                icon={<EmailIcon />}
                                label={row.notification_preferences ? "Notifications" : "Muted"}
                                color={row.notification_preferences ? "success" : "default"}
                                variant={row.notification_preferences ? "filled" : "outlined"}
                              />
                              <Chip size="small" label={`${row.favorite_comarques?.length || 0} comarques`} />
                              <Chip size="small" label={`Severity ${row.alert_min_severity ?? 0}+`} />
                              {(row.alert_meteor_types?.length || 0) > 0 && (
                                <Chip size="small" label={`${row.alert_meteor_types.length} meteors`} />
                              )}
                              {row.alert_subscribe_current_location && (
                                <Chip size="small" label="Current location" color="primary" variant="outlined" />
                              )}
                            </Stack>
                          </TableCell>

                          <TableCell>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Joined {formatDate(row.created_at)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" display="block">
                              Last login {formatDate(row.last_login)}
                            </Typography>
                          </TableCell>

                          <TableCell align="right">
                            <Tooltip title={isSelf ? "You cannot delete your own account" : "Delete user"}>
                              <span>
                                <IconButton
                                  color="error"
                                  onClick={() => setDeleteTarget(row)}
                                  disabled={disabled || isSelf}
                                  aria-label={`Delete ${row.email}`}
                                >
                                  <DeleteOutlineIcon />
                                </IconButton>
                              </span>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>

              <TablePagination
                component="div"
                count={filteredUsers.length}
                page={page}
                onPageChange={(_, nextPage) => setPage(nextPage)}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={event => {
                  setRowsPerPage(Number(event.target.value));
                  setPage(0);
                }}
                rowsPerPageOptions={[5, 10, 25, 50]}
              />
            </Stack>
          </CardContent>
        </Card>
      </Stack>

      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        aria-labelledby="delete-user-dialog-title"
      >
        <DialogTitle id="delete-user-dialog-title">Delete user</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will permanently delete {deleteTarget?.email}. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => void handleDeleteConfirmed()}
            disabled={Boolean(deleteTarget && busyUserActions[deleteTarget.id] === "delete")}
            startIcon={
              deleteTarget && busyUserActions[deleteTarget.id] === "delete"
                ? <CircularProgress size={18} color="inherit" />
                : <DeleteOutlineIcon />
            }
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function MetricCard({
  icon,
  label,
  value,
  tone = "default",
}: {
  icon: ReactNode;
  label: string;
  value: number;
  tone?: "default" | "warning";
}) {
  return (
    <Card variant="outlined">
      <CardContent sx={{ py: 2 }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Avatar
            sx={{
              width: 38,
              height: 38,
              bgcolor: tone === "warning" ? "warning.main" : "primary.main",
              color: "primary.contrastText",
            }}
          >
            {icon}
          </Avatar>
          <Box>
            <Typography variant="h5">{value}</Typography>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
