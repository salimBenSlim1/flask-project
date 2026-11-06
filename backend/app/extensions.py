"""Extension singletons, created unbound and initialised in create_app()."""
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
cors = CORS()
