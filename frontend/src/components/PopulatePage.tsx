import { useState } from 'react';
import { Box, Button, Typography, TextField, Alert, Stack } from '@mui/material';

export default function PopulatePage() {
  const [loading, setLoading] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const handlePopulateStations = async () => {
    setLoading('stations');
    setMessage('');
    setError('');
    try {
      const res = await fetch('/api/v1/meteocat/stations/populate', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to populate stations');
      setMessage('Stations populated successfully.');
    } catch (e: any) {
      setError(e.message);
    }
    setLoading('');
  };

  const handlePopulateVariablesMetadata = async () => {
    setLoading('variables-metadata');
    setMessage('');
    setError('');
    try {
      const res = await fetch('/api/v1/meteocat/stations/variables/metadata/store-all', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to populate variables metadata');
      setMessage('Variables metadata populated successfully.');
    } catch (e: any) {
      setError(e.message);
    }
    setLoading('');
  };

  const handlePopulateVariablesRange = async () => {
    setLoading('variables-range');
    setMessage('');
    setError('');
    try {
      if (!startDate || !endDate) throw new Error('Please select a date range.');
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
      const res = await fetch(`/api/v1/meteocat/stations/variables/store-range?${params.toString()}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to populate variables for range');
      setMessage('Variables for date range are being processed.');
    } catch (e: any) {
      setError(e.message);
    }
    setLoading('');
  };

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', mt: 4, p: 3, bgcolor: 'background.paper', borderRadius: 2, boxShadow: 2 }}>
      <Typography variant="h5" gutterBottom>
        Populate Meteocat Data
      </Typography>
      <Stack spacing={2} sx={{ my: 2 }}>
        <Button
          variant="contained"
          onClick={handlePopulateStations}
          disabled={!!loading}
        >
          {loading === 'stations' ? 'Populating...' : 'Populate Stations'}
        </Button>
        <Button
          variant="contained"
          onClick={handlePopulateVariablesMetadata}
          disabled={!!loading}
        >
          {loading === 'variables-metadata' ? 'Populating...' : 'Populate Variables Metadata'}
        </Button>
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Populate Variables for Date Range
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
            <TextField
              label="Start Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
              size="small"
            />
            <TextField
              label="End Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
              size="small"
            />
            <Button
              variant="contained"
              onClick={handlePopulateVariablesRange}
              disabled={!!loading}
            >
              {loading === 'variables-range' ? 'Populating...' : 'Populate'}
            </Button>
          </Box>
        </Box>
        {message && <Alert severity="success">{message}</Alert>}
        {error && <Alert severity="error">{error}</Alert>}
      </Stack>
    </Box>
  );
}