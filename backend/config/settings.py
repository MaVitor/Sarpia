import os
from pathlib import Path

from dotenv import load_dotenv
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-inseguro-troque-no-env")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

postgres_values = {
    "POSTGRES_DB": os.getenv("POSTGRES_DB", "").strip(),
    "POSTGRES_USER": os.getenv("POSTGRES_USER", "").strip(),
    "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
    "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "").strip(),
    "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "").strip(),
}
postgres_requested = any(postgres_values.values())
if postgres_requested and not all(postgres_values.values()):
    raise RuntimeError(
        "Configuração PostgreSQL incompleta. Defina POSTGRES_DB, "
        "POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST e POSTGRES_PORT."
    )

if postgres_requested:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": postgres_values["POSTGRES_DB"],
            "USER": postgres_values["POSTGRES_USER"],
            "PASSWORD": postgres_values["POSTGRES_PASSWORD"],
            "HOST": postgres_values["POSTGRES_HOST"],
            "PORT": postgres_values["POSTGRES_PORT"],
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "optional")
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_RATE_LIMITS = {
    "login": "5/m/ip",
    "signup": "5/m/ip",
}
HEADLESS_CLIENTS = ("browser",)
HEADLESS_ONLY = True
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{FRONTEND_ORIGIN}/auth/verify-email/{{key}}",
    "account_signup": f"{FRONTEND_ORIGIN}/auth",
}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@localhost")
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    *default_headers,
    "x-request-id",
    "x-idempotency-key",
)
CORS_EXPOSE_HEADERS = ("X-Request-ID",)
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv("CSRF_TRUSTED_ORIGINS", os.getenv("CORS_ORIGINS", "")).split(",")
    if o.strip()
]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None
CSRF_COOKIE_DOMAIN = os.getenv("CSRF_COOKIE_DOMAIN") or None

# ---- Sarpia ----
GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
MAX_PDF_MB = int(os.getenv("MAX_PDF_MB", "8"))
MAX_PAGINAS = int(os.getenv("MAX_PAGINAS", "20"))
MAX_CARACTERES_MATERIAL = int(os.getenv("MAX_CARACTERES_MATERIAL", "50000"))
MAX_CARACTERES_ENSAIO = int(os.getenv("MAX_CARACTERES_ENSAIO", "30000"))
# google-genai 2.x recebe timeout em milissegundos; o valor cobre uma chamada.
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))
GEMINI_MAX_TENTATIVAS = int(os.getenv("GEMINI_MAX_TENTATIVAS", "2"))
