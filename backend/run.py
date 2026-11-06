"""Entry point. Dev:  python run.py   |  Prod:  gunicorn run:app -w 4 -b 0.0.0.0:8000"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
