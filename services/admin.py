from config import OWNER_ID


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id == OWNER_ID
