import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config # Use async engine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Alembic Autogenerate Setup --- 
import os
import sys
from pathlib import Path # Import Path
from dotenv import load_dotenv # Import load_dotenv

# Determine the project root directory (assuming env.py is in backend/alembic)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = PROJECT_ROOT / '.env'

# Load the .env file from the project root
if DOTENV_PATH.exists():
    print(f"Loading environment variables from: {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}")

# Add the 'backend' directory to the path, one level above 'app'
sys.path.insert(0, str(PROJECT_ROOT / 'backend')) # Use PROJECT_ROOT for path

# Reverted to original absolute imports from app
# These imports MUST come *after* load_dotenv()
from app.db.base_class import Base # Reverted path
from app.models.financials import * # Reverted path
from app.models.company import * # Keep company model
from app.config import settings # Reverted path



target_metadata = Base.metadata
# ----------------------------------


# other values from the config, defined by the needs of env.py,
# can be acquired:-
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use the DATABASE_URL from settings (should be loaded from .env now)
    
    url = settings.database_url 
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Use the DATABASE_URL from settings (should be loaded from .env now)
    db_url = settings.database_url # Re-read from the potentially re-imported settings
     
    connectable = async_engine_from_config(
        {"sqlalchemy.url": db_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 