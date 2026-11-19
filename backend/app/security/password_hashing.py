"""Password hashing with bcrypt. We only ever store the hash, never the real password."""

from passlib.context import CryptContext

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Turn a plain password into a salted bcrypt hash that is safe to store."""
    return password_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check whether a plain password matches the stored bcrypt hash."""
    try:
        return password_context.verify(plain_password, password_hash)
    except ValueError:
        # The stored value is not a valid bcrypt hash
        return False
