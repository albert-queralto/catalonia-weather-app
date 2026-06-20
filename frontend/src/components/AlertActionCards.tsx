import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";

import { useAuth } from "../auth/AuthContext";
import { getAlertActionCards } from "../api/endpoints";
import type { AlertActionCard } from "../api/types";

type Props = {
  lat?: number;
  lon?: number;
  radiusKm?: number;
};

function formatDateTime(value: string) {
  return new Date(value).toLocaleString([], {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function severityColor(severity: number): "success" | "warning" | "error" {
  if (severity >= 4) return "error";
  if (severity >= 2) return "warning";
  return "success";
}

export default function AlertActionCards({ lat, lon, radiusKm = 8 }: Props) {
  const { token } = useAuth();
  const [cards, setCards] = useState<AlertActionCard[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      if (!token) return;

      setLoading(true);

      try {
        const data = await getAlertActionCards(token, lat, lon, radiusKm, 2);
        setCards(data);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [token, lat, lon, radiusKm]);

  if (!token) return null;

  if (loading) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        Checking personalized Meteocat alerts...
      </Alert>
    );
  }

  if (cards.length === 0) {
    return (
      <Alert severity="success" sx={{ mb: 2 }}>
        No subscribed Meteocat warnings for your selected area.
      </Alert>
    );
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Weather alert action cards
      </Typography>

      <Stack spacing={2}>
        {cards.map(card => (
          <Card key={card.id} variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: "wrap" }}>
                <Chip
                  label={`SMP ${card.severity}`}
                  color={severityColor(card.severity)}
                  size="small"
                />

                <Chip label={card.severity_label} size="small" />

                <Chip label={card.meteor} size="small" />
              </Stack>

              <Typography variant="subtitle1" fontWeight="bold">
                {card.meteor} warning from {formatDateTime(card.starts_at)} to{" "}
                {formatDateTime(card.ends_at)}
              </Typography>

              <Typography variant="body2" sx={{ mt: 1 }}>
                <b>Affected comarques:</b>{" "}
                {card.affected_comarques.map(c => c.name).join(", ")}
              </Typography>

              <Typography variant="body2" sx={{ mt: 1 }}>
                <b>Recommended action:</b> {card.recommended_action}
              </Typography>

              <Typography variant="body2" sx={{ mt: 1 }}>
                <b>Recommender effect:</b> {card.recommender_effect}
              </Typography>

              {card.affected_recommended_activities.length > 0 && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  <b>Affected activities:</b>{" "}
                  {card.affected_recommended_activities
                    .map(a => a.name)
                    .join(", ")}
                </Typography>
              )}
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
}