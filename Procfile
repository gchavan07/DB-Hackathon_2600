# Used by OpenShift Source-to-Image (s2i), Heroku, Railway, Render, etc.
# Gunicorn binds to 0.0.0.0:$PORT  – OpenShift injects $PORT automatically.
web: gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120
