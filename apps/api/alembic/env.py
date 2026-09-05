import asyncio
from logging.config import fileConfig

import alembic.ddl.impl
from sqlalchemy import (
    pool,
    text,
    Table,
    Column,
    String,
    MetaData,
    PrimaryKeyConstraint,
)
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Patch DefaultImpl.version_table_impl to support descriptive revision strings > 32 chars
def _custom_version_table_impl(
    self,
    *,
    version_table: str,
    version_table_schema=None,
    version_table_pk: bool = True,
    **kw,
) -> Table:
    vt = Table(
        version_table,
        MetaData(),
        Column("version_num", String(128), nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        vt.append_constraint(
            PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc")
        )
    return vt

alembic.ddl.impl.DefaultImpl.version_table_impl = _custom_version_table_impl

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import os
from app.core.config import settings, Settings
from app.models import Base

# add your model's MetaData object here
target_metadata = Base.metadata

# Priority: explicitly passed DATABASE_URL in os.environ > settings.DATABASE_URL
target_db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
target_db_url = Settings.assemble_database_url(target_db_url)
config.set_main_option("sqlalchemy.url", target_db_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
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
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    try:
        connection.execute(
            text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(128) NOT NULL CONSTRAINT alembic_version_pkc PRIMARY KEY);")
        )
        connection.execute(
            text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);")
        )
    except Exception:
        pass

    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
