import { useMemo, useState } from 'react';
import { Box, Button, Typography, TextField, Alert, Stack, Divider } from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Tooltip, IconButton } from '@mui/material';

type RecActivity = {
  id: string;
  name?: string;
  request_id?: string | null;
  score?: number;
};

function getAuthToken(): string | null {
  return (
    localStorage.getItem('auth.token') ||
    localStorage.getItem('token') ||
    localStorage.getItem('access_token')
  );
}

async function fetchJson(url: string, init?: RequestInit): Promise<any> {
  const res = await fetch(url, init);
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `${res.status} ${res.statusText}`;
    throw new Error(msg);
  }
  return data;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function InfoTip({ text }: { text: string }) {
  return (
    <Tooltip title={text} arrow>
      <IconButton size="small" sx={{ ml: 0.5, verticalAlign: "middle" }}>
        <InfoOutlinedIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  );
}

export default function PopulatePage() {
  const [loading, setLoading] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const recommenderBase = useMemo(
    () =>
      (import.meta as any).env?.VITE_API_BASE_URL?.replace(/\/$/, "") ||
      "/api/v1",
    []
  );
  const [recUserId, setRecUserId] = useState('');
  const [recLat, setRecLat] = useState('41.3851'); // Barcelona-ish default
  const [recLon, setRecLon] = useState('2.1734');
  const [recRadiusKm, setRecRadiusKm] = useState('8');
  const [recHorizonHours, setRecHorizonHours] = useState('4');
  const [recLimit, setRecLimit] = useState('20');
  const [recLoops, setRecLoops] = useState('10');
  const [recClickRate, setRecClickRate] = useState('0.25');
  const [recSaveRate, setRecSaveRate] = useState('0.08');
  const [recLogViewsClientSide, setRecLogViewsClientSide] = useState('no'); // "yes" | "no"

  const authToken = getAuthToken();

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

  async function fetchFirstUserId(): Promise<string | null> {
    try {
      const users = await fetchJson(`${recommenderBase}/auth/users`);
      return users.length > 0 ? users[0].id : null;
    } catch {
      return null;
    }
  }

  const handlePopulateRecommenderInteractions = async () => {
    setLoading('recommender-populate');
    setMessage('');
    setError('');

    try {
      // basic validation
      const lat = Number(recLat);
      const lon = Number(recLon);
      const radiusKm = Number(recRadiusKm);
      const horizonHours = Number(recHorizonHours);
      const limit = Number(recLimit);
      const loops = Number(recLoops);
      const clickRate = Number(recClickRate);
      const saveRate = Number(recSaveRate);

      if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error('Invalid lat/lon.');
      if (!Number.isFinite(radiusKm) || radiusKm <= 0) throw new Error('Invalid radius_km.');
      if (!Number.isFinite(horizonHours) || horizonHours <= 0) throw new Error('Invalid horizon_hours.');
      if (!Number.isFinite(limit) || limit <= 0) throw new Error('Invalid limit.');
      if (!Number.isFinite(loops) || loops <= 0) throw new Error('Invalid loops.');
      if (clickRate < 0 || clickRate > 1 || saveRate < 0 || saveRate > 1) {
        throw new Error('clickRate/saveRate must be between 0 and 1.');
      }

      let userId = recUserId;
      if (!userId) {
        userId = await fetchFirstUserId();
        if (!userId) throw new Error('No users found in the database. Please register a user first.');
        setRecUserId(userId);
      }

      const headers: Record<string, string> = {};
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

      let totalPos = 0;
      let totalEvents = 0;

      for (let i = 1; i <= loops; i++) {
        setMessage(`Recommender populate: loop ${i}/${loops} - fetching recommendations...`);

        const qs = new URLSearchParams({
          lat: String(lat),
          lon: String(lon),
          radius_km: String(radiusKm),
          horizon_hours: String(horizonHours),
          limit: String(limit),
        });

        const recs = (await fetchJson(`${recommenderBase}/recommendations?${qs.toString()}`, {
          method: 'GET',
          headers,
        })) as RecActivity[];

        // If backend returns a request_id per item, use it; otherwise create one per batch.
        const fallbackRequestId = (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`);

        if (recLogViewsClientSide === 'yes') {
          for (let pos = 0; pos < recs.length; pos++) {
            const r = recs[pos];
            const requestId = r.request_id ?? fallbackRequestId;
            await fetchJson(`${recommenderBase}/events`, {
              method: 'POST',
              headers: { ...headers, 'Content-Type': 'application/json' },
              body: JSON.stringify({
                user_id: userId,
                activity_id: r.id,
                event_type: 'view',
                request_id: requestId,
                position: pos + 1,
                user_lat: lat,
                user_lon: lon,
              }),
            });
            totalEvents += 1;
          }
        }

        // Create synthetic outcomes for training positives
        for (let pos = 0; pos < recs.length; pos++) {
          const r = recs[pos];
          const requestId = r.request_id ?? fallbackRequestId;
          const u = Math.random();

          let eventType: 'click' | 'save' | null = null;
          if (u < saveRate) eventType = 'save';
          else if (u < saveRate + clickRate) eventType = 'click';

          if (eventType) {
            await fetchJson(`${recommenderBase}/events`, {
              method: 'POST',
              headers: { ...headers, 'Content-Type': 'application/json' },
              body: JSON.stringify({
                user_id: userId,
                activity_id: r.id,
                event_type: eventType,
                request_id: requestId,
                position: pos + 1,
                user_lat: lat,
                user_lon: lon,
              }),
            });
            totalEvents += 1;
            totalPos += 1;
          }
        }

        setMessage(`Recommender populate: loop ${i}/${loops} done (events so far: ${totalEvents}, positives: ${totalPos}).`);
        await sleep(300);
      }

      setMessage(`Recommender populate complete. Total events: ${totalEvents}, positives: ${totalPos}.`);
    } catch (e: any) {
      setError(e.message ?? 'Failed to populate recommender interactions');
    }

    setLoading('');
  };

  return (
    <Box sx={{ maxWidth: 700, mx: 'auto', mt: 4, p: 3, bgcolor: 'background.paper', borderRadius: 2, boxShadow: 2 }}>
      <Typography variant="h5" gutterBottom>
        Populate Data
      </Typography>

      <Stack spacing={2} sx={{ my: 2 }}>
        <Typography variant="h6">Meteocat</Typography>

        <Button variant="contained" onClick={handlePopulateStations} disabled={!!loading}>
          {loading === 'stations' ? 'Populating...' : 'Populate Stations'}
        </Button>

        <Button variant="contained" onClick={handlePopulateVariablesMetadata} disabled={!!loading}>
          {loading === 'variables-metadata' ? 'Populating...' : 'Populate Variables Metadata'}
        </Button>

        <Box>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Populate Variables for Date Range
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 1, flexWrap: 'wrap' }}>
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
            <Button variant="contained" onClick={handlePopulateVariablesRange} disabled={!!loading}>
              {loading === 'variables-range' ? 'Populating...' : 'Populate'}
            </Button>
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Typography variant="h6">Recommender system (training data)</Typography>
        <Typography variant="body2" sx={{ opacity: 0.8 }}>
          This generates recommendation requests and posts synthetic click/save events to build a training dataset.
          It assumes the recommender API is reachable at: <b>{recommenderBase || '(same origin)'}</b>
        </Typography>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <TextField
            label={
              <>
                User ID (UUID) for /events
                <InfoTip text="The user identifier used when posting synthetic events to the recommender backend. It should be a valid UUID." />
              </>
            }
            value={recUserId}
            onChange={(e) => setRecUserId(e.target.value)}
            size="small"
            fullWidth
          />
          <TextField
            label={
              <>
                Client logs views?
                <InfoTip text="If set to 'yes', the frontend will post a 'view' event for each recommendation to the backend. If 'no', it assumes the backend logs impressions automatically." />
              </>
            }
            value={recLogViewsClientSide}
            onChange={(e) => setRecLogViewsClientSide(e.target.value)}
            size="small"
            helperText="Set to 'yes' only if backend does NOT log impressions in /recommendations"
          />

          <TextField
            label={
              <>
                Latitude
                <InfoTip text="The latitude for which recommendations are requested." />
              </>
            }
            value={recLat}
            onChange={(e) => setRecLat(e.target.value)}
            size="small"
          />
          <TextField
            label={
              <>
                Longitude
                <InfoTip text="The longitude for which recommendations are requested." />
              </>
            }
            value={recLon}
            onChange={(e) => setRecLon(e.target.value)}
            size="small"
          />
          <TextField
            label={
              <>
                Radius km
                <InfoTip text="The search radius (in kilometers) around the specified location for recommendations." />
              </>
            }
            value={recRadiusKm}
            onChange={(e) => setRecRadiusKm(e.target.value)}
            size="small"
          />
          <TextField
            label={
              <>
                Horizon hours
                <InfoTip text="How far into the future recommendations should be considered (e.g., activities available in the next X hours)." />
              </>
            }
            value={recHorizonHours}
            onChange={(e) => setRecHorizonHours(e.target.value)}
            size="small"
          />
          <TextField
            label={
              <>
                Limit
                <InfoTip text="The number of recommendations to fetch per request (e.g., if limit=20, you get 20 activities per batch)." />
              </>
            }
            value={recLimit}
            onChange={(e) => setRecLimit(e.target.value)}
            size="small"
          />
          <TextField
            label={
              <>
                Loops
                <InfoTip text="The number of times to repeat the recommendation request and event posting process. For example, if loops=10, it will simulate 10 rounds of recommendations and events." />
              </>
            }
            value={recLoops}
            onChange={(e) => setRecLoops(e.target.value)}
            size="small"
          />
          <TextField
            label={
              <>
                Click rate (0..1)
                <InfoTip text="The probability that a synthetic 'click' event is posted for a recommended activity. For example, if click rate=0.25, about 25% of recommendations will get a 'click' event." />
              </>
            }
            value={recClickRate}
            onChange={(e) => setRecClickRate(e.target.value)}
            size="small"
          />
          <TextField
            label={
              <>
                Save rate (0..1)
                <InfoTip text="The probability that a synthetic 'save' event is posted for a recommended activity. If save rate=0.08, about 8% of recommendations will get a 'save' event." />
              </>
            }
            value={recSaveRate}
            onChange={(e) => setRecSaveRate(e.target.value)}
            size="small"
          />
        </Box>

        <Button variant="contained" onClick={handlePopulateRecommenderInteractions} disabled={!!loading}>
          {loading === 'recommender-populate' ? 'Populating...' : 'Populate Recommender Interactions'}
        </Button>

        {message && <Alert severity="success">{message}</Alert>}
        {error && <Alert severity="error">{error}</Alert>}
      </Stack>
    </Box>
  );
}
