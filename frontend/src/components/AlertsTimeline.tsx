import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";

import { useAuth } from "../auth/AuthContext";
import { getAlertTimeline } from "../api/endpoints";
import type { AlertTimelineSlot } from "../api/types";

type Props = {
  lat?: number;
  lon?: number;
  radiusKm?: number;
};

function severityColor(severity: number): "default" | "success" | "warning" | "error" {
  if (severity >= 4) return "error";
  if (severity >= 2) return "warning";
  if (severity >= 1) return "success";
  return "default";
}

export default function AlertsTimeline({ lat, lon, radiusKm = 8 }: Props) {
  const { token } = useAuth();
  const [slots, setSlots] = useState<AlertTimelineSlot[]>([]);

  useEffect(() => {
    async function load() {
      if (!token) return;

      const data = await getAlertTimeline(token, lat, lon, radiusKm, 2);
      setSlots(data);
    }

    load();
  }, [token, lat, lon, radiusKm]);

  if (!token || slots.length === 0) return null;

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Alerts timeline
      </Typography>

      <Stack direction="row" spacing={1} sx={{ overflowX: "auto", pb: 1 }}>
        {slots.map(slot => (
          <Card
            key={slot.starts_at}
            variant="outlined"
            sx={{
              minWidth: 180,
              borderWidth: slot.max_severity >= 3 ? 2 : 1,
            }}
          >
            <CardContent>
              <Typography variant="body2" fontWeight="bold">
                {slot.label}
              </Typography>

              <Chip
                sx={{ mt: 1 }}
                size="small"
                color={severityColor(slot.max_severity)}
                label={
                  slot.max_severity > 0
                    ? `Max SMP ${slot.max_severity}`
                    : "No warning"
                }
              />

              {slot.cards.length > 0 && (
                <Box sx={{ mt: 1 }}>
                  {slot.cards.map(card => (
                    <Typography key={card.id} variant="caption" display="block">
                      {card.meteor}: {card.affected_comarques.length} comarca(s)
                    </Typography>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
}