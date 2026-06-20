# database.py

import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    """Create all tables if they do not exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                age INTEGER NOT NULL,
                name TEXT NOT NULL,
                gender TEXT NOT NULL,
                looking_for TEXT NOT NULL,
                goal TEXT NOT NULL,
                interests TEXT NOT NULL,
                photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS likes (
                like_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS views (
                view_id INTEGER PRIMARY KEY AUTOINCREMENT,
                viewer_id INTEGER NOT NULL,
                viewed_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(viewer_id, viewed_id)
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
    gender: str,
    looking_for: str,
    goal: str,
    interests: list[str],
    photo_file_id: str | None = None,
) -> None:
    """Insert a newly registered user into the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users
            (user_id, username, age, name, gender, looking_for, goal, interests, photo_file_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                age,
                name,
                gender,
                looking_for,
                goal,
                ",".join(sorted(interests)),
                photo_file_id,
            ),
        )
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    """Return user row as a dict or None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_user(
    user_id: int,
    *,
    age: int | None = None,
    name: str | None = None,
    looking_for: str | None = None,
    goal: str | None = None,
    interests: list[str] | None = None,
    photo_file_id: str | None = None,
) -> None:
    """Update one or more user fields."""
    fields = []
    values = []
    if age is not None:
        fields.append("age = ?")
        values.append(age)
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if looking_for is not None:
        fields.append("looking_for = ?")
        values.append(looking_for)
    if goal is not None:
        fields.append("goal = ?")
        values.append(goal)
    if interests is not None:
        fields.append("interests = ?")
        values.append(",".join(sorted(interests)))
    if photo_file_id is not None:
        fields.append("photo_file_id = ?")
        values.append(photo_file_id)

    if not fields:
        return

    values.append(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?",
            values,
        )
        await db.commit()


async def get_all_users() -> list[dict]:
    """Return all users as a list of dicts."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_like(from_user_id: int, to_user_id: int) -> None:
    """Record a like, ignoring duplicates."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO likes (from_user_id, to_user_id)
            VALUES (?, ?)
            """,
            (from_user_id, to_user_id),
        )
        await db.commit()


async def has_like(from_user_id: int, to_user_id: int) -> bool:
    """Return True if from_user_id has liked to_user_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM likes WHERE from_user_id = ? AND to_user_id = ?",
            (from_user_id, to_user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_like_stats(user_id: int) -> tuple[int, int]:
    """Return (sent_likes, received_likes)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM likes WHERE from_user_id = ?", (user_id,)
        ) as cursor:
            sent = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM likes WHERE to_user_id = ?", (user_id,)
        ) as cursor:
            received = (await cursor.fetchone())[0]
        return sent, received


async def add_view(viewer_id: int, viewed_id: int) -> None:
    """Mark a profile as viewed, ignoring duplicates."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO views (viewer_id, viewed_id)
            VALUES (?, ?)
            """,
            (viewer_id, viewed_id),
        )
        await db.commit()


async def get_viewed_ids(viewer_id: int) -> set[int]:
    """Return set of user IDs already viewed by viewer_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT viewed_id FROM views WHERE viewer_id = ?", (viewer_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
