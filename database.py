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
                city TEXT,
                filter_min_age INTEGER DEFAULT 16,
                filter_max_age INTEGER DEFAULT 100,
                filter_only_my_city INTEGER DEFAULT 0,
                notifications_enabled INTEGER NOT NULL DEFAULT 1,
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
    city: str | None = None,
) -> None:
    """Insert a newly registered user into the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users
            (user_id, username, age, name, gender, looking_for, goal, interests, photo_file_id, city, notifications_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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
                city,
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
    notifications_enabled: bool | None = None,
    city: str | None = None,
    filter_min_age: int | None = None,
    filter_max_age: int | None = None,
    filter_only_my_city: bool | None = None,
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
    if notifications_enabled is not None:
        fields.append("notifications_enabled = ?")
        values.append(1 if notifications_enabled else 0)
    if city is not None:
        fields.append("city = ?")
        values.append(city)
    if filter_min_age is not None:
        fields.append("filter_min_age = ?")
        values.append(filter_min_age)
    if filter_max_age is not None:
        fields.append("filter_max_age = ?")
        values.append(filter_max_age)
    if filter_only_my_city is not None:
        fields.append("filter_only_my_city = ?")
        values.append(1 if filter_only_my_city else 0)

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


async def get_notifications_enabled(user_id: int) -> bool:
    """Return True if the user wants incoming-like notifications."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT notifications_enabled FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True


async def set_notifications_enabled(user_id: int, enabled: bool) -> None:
    """Enable or disable incoming-like notifications."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET notifications_enabled = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id),
        )
        await db.commit()


async def update_user_city(user_id: int, city: str | None) -> None:
    """Update the user's city."""
    await update_user(user_id, city=city)


async def update_user_filters(
    user_id: int, *, min_age: int, max_age: int, only_my_city: bool
) -> None:
    """Update the user's feed filter preferences."""
    await update_user(
        user_id,
        filter_min_age=min_age,
        filter_max_age=max_age,
        filter_only_my_city=only_my_city,
    )


async def get_user_filters(user_id: int) -> dict:
    """Return the user's feed filters as a dict with defaults."""
    user = await get_user(user_id)
    if not user:
        return {"min_age": 16, "max_age": 100, "only_my_city": False}
    return {
        "min_age": user.get("filter_min_age", 16),
        "max_age": user.get("filter_max_age", 100),
        "only_my_city": bool(user.get("filter_only_my_city", 0)),
    }
