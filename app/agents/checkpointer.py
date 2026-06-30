#type: ignore

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings

_conn = None
_checkpointer = None

async def get_checkpointer():
    global _conn, _checkpointer

    if _checkpointer is None:
        url = settings.alembic_database_url.replace("+psycopg", "")

        _conn = await AsyncConnection.connect(url, autocommit=True, row_factory=dict_row)
        _checkpointer = AsyncPostgresSaver(_conn)

        await _checkpointer.setup()

    return _checkpointer