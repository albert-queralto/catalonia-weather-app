import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import VisibilityIcon from '@mui/icons-material/Visibility';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import StarIcon from '@mui/icons-material/Star';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

interface OverallMetrics {
  total_sessions: number;
  total_impressions: number;
  total_engagements: number;
  total_clicks: number;
  total_saves: number;
  total_completes: number;
  total_ratings: number;
  overall_avg_rating: number;
  avg_ctr: number;
}

interface DailyStats {
  date: string;
  sessions: number;
  impressions: number;
  engagements: number;
  ctr: number;
}

interface CategoryStats {
  category: string;
  impressions: number;
  engagements: number;
  ctr: number;
  avg_rating: number;
}

interface TopActivity {
  activity_id: string;
  name: string;
  category: string;
  impressions: number;
  engagements: number;
  ctr: number;
  avg_rating: number;
}

interface PositionStats {
  position: number;
  impressions: number;
  engagements: number;
  ctr: number;
}

interface AnalyticsData {
  overall: OverallMetrics;
  daily: DailyStats[];
  by_category: CategoryStats[];
  top_activities: TopActivity[];
  by_position: PositionStats[];
  period_days: number;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

function getAuthToken(): string | null {
  return (
    localStorage.getItem('auth.token') ||
    localStorage.getItem('token') ||
    localStorage.getItem('access_token')
  );
}

function MetricCard({ title, value, icon, color, subtitle }: any) {
  return (
    <Card sx={{ height: '100%', bgcolor: color + '10' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ color: color, fontWeight: 'bold', mb: 1 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="textSecondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box sx={{ color: color, opacity: 0.7 }}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function RecommenderAnalyticsDashboard() {
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<AnalyticsData | null>(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError('');
    
    try {
      const token = getAuthToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(
        `${API_BASE_URL}/analytics/recommendation-performance?days=${days}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }

      const result = await response.json();
      setData(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!data) {
    return <Alert severity="info">No data available</Alert>;
  }

  const { overall, daily, by_category, top_activities, by_position } = data;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="bold">
          Recommender Analytics
        </Typography>
        
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Time Period</InputLabel>
          <Select value={days} label="Time Period" onChange={(e) => setDays(Number(e.target.value))}>
            <MenuItem value={7}>Last 7 days</MenuItem>
            <MenuItem value={14}>Last 14 days</MenuItem>
            <MenuItem value={30}>Last 30 days</MenuItem>
            <MenuItem value={60}>Last 60 days</MenuItem>
            <MenuItem value={90}>Last 90 days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Overall Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Sessions"
            value={overall.total_sessions.toLocaleString()}
            icon={<VisibilityIcon sx={{ fontSize: 40 }} />}
            color="#1976d2"
            subtitle={`${overall.total_impressions} impressions`}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Engagement Rate"
            value={`${(overall.avg_ctr * 100).toFixed(1)}%`}
            icon={<TouchAppIcon sx={{ fontSize: 40 }} />}
            color="#2e7d32"
            subtitle={`${overall.total_engagements} total engagements`}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Avg Rating"
            value={overall.overall_avg_rating.toFixed(2)}
            icon={<StarIcon sx={{ fontSize: 40 }} />}
            color="#ed6c02"
            subtitle={`${overall.total_ratings} ratings`}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Interactions"
            value={overall.total_clicks + overall.total_saves + overall.total_completes}
            icon={<TrendingUpIcon sx={{ fontSize: 40 }} />}
            color="#9c27b0"
            subtitle={`${overall.total_saves} saves • ${overall.total_completes} completes`}
          />
        </Grid>
      </Grid>

      {/* Daily Trend Chart */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Daily Performance Trend
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="impressions"
              stroke="#1976d2"
              strokeWidth={2}
              name="Impressions"
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="engagements"
              stroke="#2e7d32"
              strokeWidth={2}
              name="Engagements"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="ctr"
              stroke="#ed6c02"
              strokeWidth={2}
              name="CTR"
            />
          </LineChart>
        </ResponsiveContainer>
      </Paper>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Category Performance */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Performance by Category
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={by_category}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="category" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="impressions" fill="#1976d2" name="Impressions" />
                <Bar dataKey="engagements" fill="#2e7d32" name="Engagements" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Category CTR Pie Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Engagement Rate by Category
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={by_category}
                  dataKey="ctr"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry) => `${entry.category}: ${(entry.ctr * 100).toFixed(1)}%`}
                >
                  {by_category.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => `${(value * 100).toFixed(2)}%`} />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Position Analysis */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Click-Through Rate by Position
        </Typography>
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          Shows how position in recommendation list affects engagement
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={by_position}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="position" />
            <YAxis />
            <Tooltip formatter={(value: number) => `${(value * 100).toFixed(2)}%`} />
            <Legend />
            <Bar dataKey="ctr" fill="#ed6c02" name="CTR" />
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      {/* Top Performing Activities */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Top Performing Activities
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Activity</TableCell>
                <TableCell>Category</TableCell>
                <TableCell align="right">Impressions</TableCell>
                <TableCell align="right">Engagements</TableCell>
                <TableCell align="right">CTR</TableCell>
                <TableCell align="right">Avg Rating</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {top_activities.map((activity) => (
                <TableRow key={activity.activity_id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {activity.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={activity.category} size="small" color="primary" variant="outlined" />
                  </TableCell>
                  <TableCell align="right">{activity.impressions}</TableCell>
                  <TableCell align="right">{activity.engagements}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1 }}>
                      <Box sx={{ width: 60 }}>
                        <LinearProgress
                          variant="determinate"
                          value={activity.ctr * 100}
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                      </Box>
                      <Typography variant="body2" fontWeight="medium">
                        {(activity.ctr * 100).toFixed(1)}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    {activity.avg_rating > 0 ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                        <StarIcon sx={{ fontSize: 16, color: '#ed6c02' }} />
                        <Typography variant="body2">{activity.avg_rating.toFixed(1)}</Typography>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="textSecondary">
                        N/A
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
}