from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AirQualityHealth:
    score: float
    label: str
    advice: str
    dominant_pollutant: Optional[str] = None


def label_european_aqi(score: Optional[float]) -> AirQualityHealth:
    if score is None:
        return AirQualityHealth(
            score=0.0,
            label="unknown",
            advice="Air-quality data is not available.",
            dominant_pollutant=None,
        )

    s = float(score)

    if s <= 20:
        return AirQualityHealth(s, "good", "Good conditions for outdoor activities.")
    if s <= 40:
        return AirQualityHealth(s, "reasonably_good", "Generally fine for outdoor activities.")
    if s <= 60:
        return AirQualityHealth(
            s,
            "regular",
            "Acceptable, but sensitive users should reduce intense outdoor activity.",
        )
    if s <= 80:
        return AirQualityHealth(
            s,
            "unfavorable",
            "Consider shorter or less intense outdoor activities.",
        )
    if s <= 100:
        return AirQualityHealth(
            s,
            "very_unfavorable",
            "Prefer indoor activities, especially for sensitive users.",
        )

    return AirQualityHealth(
        s,
        "extremely_unfavorable",
        "Avoid strenuous outdoor activity.",
    )


def classify_uv_index(uv: Optional[float]) -> str:
    if uv is None:
        return "unknown"
    if uv < 3:
        return "low"
    if uv < 6:
        return "moderate"
    if uv < 8:
        return "high"
    if uv < 11:
        return "very_high"
    return "extreme"