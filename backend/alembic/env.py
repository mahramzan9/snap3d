from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.core.database import Base
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(con):
    context.configure(connection=con, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.",
        poolclass=pool.NullPool)
    async with connectable.connect() as con:
        await con.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_online())
