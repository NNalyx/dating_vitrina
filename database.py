# database.py

import sqlite3

import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    """Create all tables and migrate existing ones."""
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
                filter_interests INTEGER DEFAULT 0,
                notifications_enabled INTEGER NOT NULL DEFAULT 1,
                is_banned INTEGER NOT NULL DEFAULT 0,
                is_fake INTEGER NOT NULL DEFAULT 0,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for column in ("is_banned", "is_fake", "filter_interests"):
            try:
                await db.execute(
                    f"ALTER TABLE users ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN bio TEXT")
        except sqlite3.OperationalError:
            pass

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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL,
                reported_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS interests (
                category_key TEXT NOT NULL,
                category_label TEXT NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (category_key, name)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS fake_avatars (
                avatar_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gender TEXT NOT NULL,
                file_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()
        await _seed_interests(db)


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
    is_fake: bool = False,
    bio: str | None = None,
) -> None:
    """Insert a newly registered user into the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users
            (user_id, username, age, name, gender, looking_for, goal, interests, photo_file_id, city, notifications_enabled, is_fake, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
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
                1 if is_fake else 0,
                bio,
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
    username: str | None = None,
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
    filter_interests: bool | None = None,
    bio: str | None = None,
) -> None:
    """Update one or more user fields."""
    fields = []
    values = []
    if username is not None:
        fields.append("username = ?")
        values.append(username)
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
    if filter_interests is not None:
        fields.append("filter_interests = ?")
        values.append(1 if filter_interests else 0)
    if bio is not None:
        fields.append("bio = ?")
        values.append(bio)

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


async def get_matches(user_id: int) -> list[dict]:
    """Return users with mutual likes."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.* FROM users u
            WHERE u.user_id != ?
              AND EXISTS (
                  SELECT 1 FROM likes l1
                  WHERE l1.from_user_id = ? AND l1.to_user_id = u.user_id
              )
              AND EXISTS (
                  SELECT 1 FROM likes l2
                  WHERE l2.from_user_id = u.user_id AND l2.to_user_id = ?
              )
            ORDER BY u.name
            """,
            (user_id, user_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


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


async def clear_views(viewer_id: int) -> None:
    """Remove all viewed records for a given viewer."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM views WHERE viewer_id = ?", (viewer_id,))
        await db.commit()


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
        return {"min_age": 16, "max_age": 100, "only_my_city": False, "filter_interests": False}
    return {
        "min_age": user.get("filter_min_age", 16),
        "max_age": user.get("filter_max_age", 100),
        "only_my_city": bool(user.get("filter_only_my_city", 0)),
        "filter_interests": bool(user.get("filter_interests", 0)),
    }


async def _seed_interests(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("SELECT COUNT(*) FROM interests")
    if (await cursor.fetchone())[0] > 0:
        return
    from config import INTEREST_CATEGORIES

    rows = []
    for cat_key, cat_label, items in INTEREST_CATEGORIES:
        for idx, name in enumerate(items):
            rows.append((cat_key, cat_label, name, idx))
    await db.executemany(
        "INSERT INTO interests (category_key, category_label, name, sort_order) VALUES (?, ?, ?, ?)",
        rows,
    )
    await db.commit()


async def ban_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def unban_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False


async def delete_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.execute(
            "DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?",
            (user_id, user_id),
        )
        await db.execute(
            "DELETE FROM views WHERE viewer_id = ? OR viewed_id = ?",
            (user_id, user_id),
        )
        await db.commit()


async def get_user_by_username(username: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_report(reporter_id: int, reported_id: int, reason: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reports (reporter_id, reported_id, reason) VALUES (?, ?, ?)",
            (reporter_id, reported_id, reason),
        )
        await db.commit()


async def get_pending_reports(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reports WHERE status = 'pending' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_report(report_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reports WHERE report_id = ?", (report_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def resolve_report(report_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reports SET status = ? WHERE report_id = ?",
            (status, report_id),
        )
        await db.commit()


async def add_admin_log(
    admin_id: int,
    action: str,
    target_id: int | None = None,
    details: str = "",
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)",
            (admin_id, action, target_id, details),
        )
        await db.commit()


async def get_admin_logs(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_interests_from_db() -> list[dict]:
    """Return interests grouped by category for the Mini App."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT category_key, category_label, name FROM interests ORDER BY category_key, sort_order"
        ) as cursor:
            rows = await cursor.fetchall()
    grouped: dict[str, dict] = {}
    for row in rows:
        key = row["category_key"]
        if key not in grouped:
            grouped[key] = {"key": key, "label": row["category_label"], "items": []}
        grouped[key]["items"].append(row["name"])
    return list(grouped.values())


async def add_interest(category_key: str, category_label: str, name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO interests (category_key, category_label, name, sort_order)
            VALUES (
                ?, ?, ?,
                (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM interests WHERE category_key = ?)
            )
            """,
            (category_key, category_label, name, category_key),
        )
        await db.commit()


async def remove_interest(category_key: str, name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM interests WHERE category_key = ? AND name = ?",
            (category_key, name),
        )
        await db.commit()


async def remove_category(category_key: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM interests WHERE category_key = ?", (category_key,))
        await db.commit()


async def get_admin_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now')"
        ) as cursor:
            new_today = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-7 days')"
        ) as cursor:
            new_week = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-30 days')"
        ) as cursor:
            new_month = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM likes") as cursor:
            total_likes = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM views") as cursor:
            total_views = (await cursor.fetchone())[0]
        async with db.execute(
            """
            SELECT COUNT(DISTINCT user_id) FROM (
                SELECT from_user_id AS user_id FROM likes
                UNION
                SELECT to_user_id AS user_id FROM likes
                UNION
                SELECT viewer_id AS user_id FROM views
                UNION
                SELECT viewed_id AS user_id FROM views
            )
            """
        ) as cursor:
            active_users = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM reports WHERE status = 'pending'"
        ) as cursor:
            pending_reports = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned = 1"
        ) as cursor:
            banned_users = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_fake = 1"
        ) as cursor:
            fake_users = (await cursor.fetchone())[0]
    return {
        "total_users": total_users,
        "new_today": new_today,
        "new_week": new_week,
        "new_month": new_month,
        "total_likes": total_likes,
        "total_views": total_views,
        "active_users": active_users,
        "pending_reports": pending_reports,
        "banned_users": banned_users,
        "fake_users": fake_users,
    }


async def get_banned_users(limit: int = 20) -> list[dict]:
    """Return recently banned users."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE is_banned = 1 ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_fake_users(limit: int = 100) -> list[dict]:
    """Return all fake profiles."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE is_fake = 1 ORDER BY user_id LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def delete_fake_users() -> int:
    """Delete all fake profiles and return count of removed rows."""
    fake_users = await get_fake_users(limit=10000)
    async with aiosqlite.connect(DB_PATH) as db:
        for user in fake_users:
            uid = user["user_id"]
            await db.execute("DELETE FROM users WHERE user_id = ?", (uid,))
            await db.execute(
                "DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?",
                (uid, uid),
            )
            await db.execute(
                "DELETE FROM views WHERE viewer_id = ? OR viewed_id = ?",
                (uid, uid),
            )
        await db.commit()
    return len(fake_users)


async def get_next_fake_user_id() -> int:
    """Return the next negative user_id for a fake profile."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT MIN(user_id) FROM users WHERE user_id < 0"
        ) as cursor:
            row = await cursor.fetchone()
            min_id = row[0] if row and row[0] is not None else 0
    return min(min_id - 1, -1)


async def add_fake_user(
    *,
    name: str,
    age: int,
    gender: str,
    looking_for: str,
    goal: str,
    interests: list[str],
    city: str | None = None,
    photo_file_id: str | None = None,
    bio: str | None = None,
) -> int:
    """Create a fake profile and return its generated user_id."""
    user_id = await get_next_fake_user_id()
    await add_user(
        user_id=user_id,
        username=None,
        age=age,
        name=name,
        gender=gender,
        looking_for=looking_for,
        goal=goal,
        interests=interests,
        photo_file_id=photo_file_id,
        city=city,
        is_fake=True,
        bio=bio,
    )
    return user_id


async def add_fake_avatar(gender: str, file_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO fake_avatars (gender, file_id) VALUES (?, ?)",
            (gender, file_id),
        )
        await db.commit()


async def get_random_fake_avatar_file_id(gender: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for g in (gender, "neutral"):
            async with db.execute(
                "SELECT file_id FROM fake_avatars WHERE gender = ? ORDER BY RANDOM() LIMIT 1",
                (g,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row["file_id"]
        async with db.execute(
            "SELECT file_id FROM fake_avatars ORDER BY RANDOM() LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row["file_id"] if row else None


async def count_fake_avatars(gender: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        if gender:
            async with db.execute(
                "SELECT COUNT(*) FROM fake_avatars WHERE gender = ?", (gender,)
            ) as cursor:
                return (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM fake_avatars") as cursor:
            return (await cursor.fetchone())[0]
