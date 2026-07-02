#type: ignore

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings


async def get_checkpointer():
    url = settings.alembic_database_url.replace("+psycopg", "")

    conn = await AsyncConnection.connect(url, autocommit=True, row_factory=dict_row)
    checkpointer = AsyncPostgresSaver(conn)

    await checkpointer.setup()

    return checkpointer