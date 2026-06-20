# database.py

import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    """Create the users table if the database file does not exist yet."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                age INTEGER NOT NULL,
                name TEXT NOT NULL,
                interests TEXT NOT NULL,
                photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def user_exists(user_id: int) -> bool:
    """Return True if a user with the given Telegram ID is already registered."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def add_user(
    user_id: int,
    username: str | None,
    age: int,
    name: str,
    interests: list[str],
    photo_file_id: str | None = None,
) -> None:
    """Insert a newly registered user into the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, age, name, interests, photo_file_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, age, name, ",".join(interests), photo_file_id),
        )
        await db.commit()
