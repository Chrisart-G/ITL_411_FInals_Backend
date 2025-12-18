from django.urls import path
from . import views

urlpatterns = [
    # Weather summary (current + 5-day daily aggregates) — used by the dashboard
    path("weather/summary", views.weather_summary),

    # (Optional) keep your analytics endpoints if you still need them
    path("analytics/metrics", views.metrics),
    path("analytics/timeseries", views.timeseries),
    path("analytics/forecast", views.forecast),
    path("analytics/feature-importance", views.feature_importance),
    path('analytics/', views.weather_analytics, name='weather-analytics'),  # ADD THIS LINE
]
