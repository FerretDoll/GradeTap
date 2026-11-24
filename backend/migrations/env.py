from alembic import context
from app.db import models
from app.db.session import Base
from app.core.config import settings
from sqlalchemy import create_engine

# Alembic rebuilds SQLite tables in batch mode on its own connection.
engine = create_engine(settings.database_url)

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
