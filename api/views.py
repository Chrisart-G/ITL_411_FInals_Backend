# api/views.py
import os
import requests
from datetime import datetime, timezone
from collections import defaultdict

from django.conf import settings
from django.http import JsonResponse
from django.core.cache import cache

OWM_API_KEY = settings.OWM_API_KEY
SESSION = requests.Session()
TIMEOUT = 12

def _json_error(message, status=400):
    # Always stringify exceptions so JSON encoding never fails
    return JsonResponse({"error": str(message)}, status=status)

def _require_key():
    if not OWM_API_KEY:
        raise RuntimeError("Missing OWM_API_KEY in environment/.env")


def _geocode_city(city: str):
    """
    Resolve a city string to (lat, lon). We are defensive here:
    - Accept long strings like 'Bacolod City, Negros Occidental, Philippines'
    - Try several simplified variants: 'Bacolod,PH', 'Bacolod'
    Result is cached for 1 day.
    """
    if not city:
        city = "Bacolod,PH"

    key = f"geocode:{city.lower()}"
    cached = cache.get(key)
    if cached:
        return cached

    _require_key()

    base = city.strip()
    lowered = base.lower()

    # Build candidate queries, most specific first
    candidates = []

    # 1. Whatever the frontend sent
    candidates.append(base)

    # 2. If it includes "Philippines", strip that and add ",PH"
    if "philippines" in lowered:
        first_part = base.split(",")[0].strip()  # e.g. 'Bacolod City'
        candidates.append(f"{first_part},PH")
        candidates.append(first_part)

    # 3. If it has commas but no 'Philippines', also try first part & first+PH
    if "," in base and "philippines" not in lowered:
        first_part = base.split(",")[0].strip()
        candidates.append(first_part)
        candidates.append(f"{first_part},PH")

    # 4. If it still doesn't explicitly specify country, try adding PH
    if ",ph" not in lowered and "philippines" not in lowered:
        short = base.split(",")[0].strip()
        candidates.append(f"{short},PH")

    # Deduplicate while preserving order
    seen = set()
    final_candidates = []
    for q in candidates:
        q_norm = q.strip().lower()
        if q_norm and q_norm not in seen:
            seen.add(q_norm)
            final_candidates.append(q.strip())

    url = "https://api.openweathermap.org/geo/1.0/direct"

    last_err = None
    for q in final_candidates:
        try:
            params = {"q": q, "limit": 1, "appid": OWM_API_KEY}
            r = SESSION.get(url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            arr = r.json()
            if not arr:
                # no result for this candidate, try next
                continue
            item = arr[0]
            lat, lon = float(item["lat"]), float(item["lon"])
            cache.set(key, (lat, lon), 60 * 60 * 24)
            return lat, lon
        except requests.HTTPError as e:
            last_err = e
            continue

    # If we reach here, everything failed
    if last_err is not None:
        raise RuntimeError(f"City not found (OWM): {city}")
    raise RuntimeError(f"City not found: {city}")


def _current_weather(lat: float, lon: float):
    """Current weather (free endpoint). Cache 60s."""
    key = f"wx:current:{lat:.4f}:{lon:.4f}"
    cached = cache.get(key)
    if cached:
        return cached
    _require_key()
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": OWM_API_KEY, "units": "metric"}
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    cache.set(key, data, 60)
    return data

def _forecast_5d3h(lat: float, lon: float):
    """5-day / 3-hour forecast (free endpoint). Cache 3 min."""
    key = f"wx:fcst:{lat:.4f}:{lon:.4f}"
    cached = cache.get(key)
    if cached:
        return cached
    _require_key()
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": OWM_API_KEY, "units": "metric"}
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    cache.set(key, data, 60 * 3)
    return data

def weather_summary(request):
    """
    Returns:
    {
      city, lat, lon,
      current: { temp_c, humidity, wind_speed, sunrise, sunset, description },
      daily: [
        { date, temp_min, temp_max, pop, rain_mm, wind_speed },
        ... up to 5 days ...
      ]
    }
    All from OpenWeatherMap free endpoints (no OneCall required).
    """
    try:
        # default to Bacolod,PH if nothing is passed
        city = request.GET.get("city") or "Bacolod,PH"
        lat, lon = _geocode_city(city)

        wx = _current_weather(lat, lon)
        fc = _forecast_5d3h(lat, lon)

        # Current
        current = {
            "temp_c": wx.get("main", {}).get("temp"),
            "humidity": wx.get("main", {}).get("humidity"),
            "wind_speed": wx.get("wind", {}).get("speed"),
            "sunrise": datetime.fromtimestamp(
                wx.get("sys", {}).get("sunrise", 0),
                tz=timezone.utc
            ).isoformat() if wx.get("sys") else None,
            "sunset": datetime.fromtimestamp(
                wx.get("sys", {}).get("sunset", 0),
                tz=timezone.utc
            ).isoformat() if wx.get("sys") else None,
            "description": (wx.get("weather") or [{}])[0].get("description"),
        }

        # Aggregate 3-hourly list into daily metrics (up to 5 days)
        buckets = defaultdict(lambda: {
            "temps_min": [], "temps_max": [], "pops": [], "rains": [], "winds": []
        })
        for item in (fc.get("list") or []):
            ts = item.get("dt")
            if not ts:
                continue
            date_key = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            main = item.get("main", {})
            wind = item.get("wind", {})
            pop = item.get("pop", 0) or 0
            rain_mm = (item.get("rain", {}) or {}).get("3h", 0) or 0

            buckets[date_key]["temps_min"].append(main.get("temp_min"))
            buckets[date_key]["temps_max"].append(main.get("temp_max"))
            buckets[date_key]["pops"].append(pop * 100.0)
            buckets[date_key]["rains"].append(rain_mm)
            buckets[date_key]["winds"].append(wind.get("speed"))

        # Produce sorted daily rows (today → +4)
        daily_rows = []
        for day in sorted(buckets.keys())[:5]:
            b = buckets[day]
            temps_min = [t for t in b["temps_min"] if t is not None]
            temps_max = [t for t in b["temps_max"] if t is not None]
            winds = [w for w in b["winds"] if w is not None]

            daily_rows.append({
                "date": day,
                "temp_min": round(min(temps_min), 1) if temps_min else None,
                "temp_max": round(max(temps_max), 1) if temps_max else None,
                "pop": round(max(b["pops"]), 1) if b["pops"] else None,
                "rain_mm": round(sum(b["rains"]), 1) if b["rains"] else 0,
                "wind_speed": (
                    round(sum(winds) / max(1, len(winds)), 1) if winds else None
                ),
            })

        payload = {
            "city": fc.get("city", {}).get("name") or city,
            "lat": lat,
            "lon": lon,
            "current": current,
            "daily": daily_rows,
        }
        return JsonResponse(payload)
    except requests.HTTPError as e:
        try:
            return _json_error(e.response.json(), status=e.response.status_code)
        except Exception:
            return _json_error(str(e), status=502)
    except Exception as e:
        return _json_error(e, status=500)


# --- Your analytics placeholders (unchanged) ---

def metrics(request):
    return _json_error("Use /api/weather/summary instead for weather KPIs.", status=400)

def timeseries(request):
    return _json_error("Use /api/weather/summary instead for weather KPIs.", status=400)

def forecast(request):
    return _json_error("Use /api/weather/summary instead for weather KPIs.", status=400)

def feature_importance(request):
    data = [
        {"feature": "humidity", "importance": 0.30},
        {"feature": "pressure", "importance": 0.22},
        {"feature": "temp_day", "importance": 0.20},
        {"feature": "wind_speed", "importance": 0.15},
        {"feature": "clouds", "importance": 0.13},
    ]
    return JsonResponse(data, safe=False)
