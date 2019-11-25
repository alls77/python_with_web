## Примеры запуска:


. .env/bin/activate
python testrun.py


gunicorn main:app.wsgi_app


uwsgi --ini uwsgi.ini
