web: source venv/bin/activate && python manage.py force_migrate && gunicorn harakacare.wsgi:application --bind 0.0.0.0:$PORT
