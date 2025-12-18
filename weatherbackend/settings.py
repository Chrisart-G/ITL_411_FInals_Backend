import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # loads .env in project root
OWM_API_KEY = os.environ.get("OWM_API_KEY")
CORS_ALLOWED_ORIGIN = os.environ.get("CORS_ALLOWED_ORIGIN")
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "api",  # your app
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be high
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "weatherbackend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "weatherbackend.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# ---- CORS ----
CORS_ALLOWED_ORIGINS = [
    # Local dev (Vite)
    "http://localhost:5173",
    "http://127.0.0.1:5173",

    # Production frontend (Netlify)
    "https://itl-411-weather-app.netlify.app",
]

# We are NOT sending cookies from the frontend, so keep this False
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = [
    "https://itl-411-finals-backend.onrender.com",
    "https://itl-411-weather-app.netlify.app",
]
# ---- Cache (simple, in-memory) ----
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "weather-cache",
    }
}

# OpenWeatherMap key
OWM_API_KEY = os.environ.get("OWM_API_KEY", "")
