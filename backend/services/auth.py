"""
Authentication service for standard auth (email/password, OAuth).
"""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    from passlib.context import CryptContext
    from jose import jwt, JWTError
except ImportError:
    CryptContext = None
    jwt = None
    JWTError = Exception


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if CryptContext else None

# JWT settings
JWT_SECRET_KEY = secrets.token_urlsafe(32)  # Override with env var in production
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


@dataclass
class TokenPayload:
    """Decoded token payload."""
    user_id: str
    tenant_id: str
    email: str
    role: str
    exp: datetime
    type: str  # "access" or "refresh"


class AuthService:
    """Service for authentication operations."""

    def __init__(self, jwt_secret: str = None):
        """Initialize auth service."""
        self.jwt_secret = jwt_secret or JWT_SECRET_KEY

    # ==================== PASSWORD OPERATIONS ====================

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        if pwd_context is None:
            raise RuntimeError("passlib not available")
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        if pwd_context is None:
            raise RuntimeError("passlib not available")
        return pwd_context.verify(plain_password, hashed_password)

    # ==================== TOKEN OPERATIONS ====================

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        role: str,
        expires_delta: timedelta = None
    ) -> str:
        """Create a JWT access token."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "role": role,
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=JWT_ALGORITHM)

    def create_refresh_token(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        role: str,
    ) -> str:
        """Create a JWT refresh token."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "role": role,
            "exp": expire,
            "type": "refresh",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=JWT_ALGORITHM)

    def create_token_pair(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        role: str,
    ) -> TokenPair:
        """Create both access and refresh tokens."""
        return TokenPair(
            access_token=self.create_access_token(user_id, tenant_id, email, role),
            refresh_token=self.create_refresh_token(user_id, tenant_id, email, role),
        )

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """Decode and validate a JWT token."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[JWT_ALGORITHM])
            return TokenPayload(
                user_id=payload["sub"],
                tenant_id=payload["tenant_id"],
                email=payload["email"],
                role=payload["role"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                type=payload["type"],
            )
        except JWTError:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create a new access token from a valid refresh token."""
        payload = self.decode_token(refresh_token)
        if payload is None or payload.type != "refresh":
            return None
        if payload.exp < datetime.now(timezone.utc):
            return None

        return self.create_access_token(
            payload.user_id,
            payload.tenant_id,
            payload.email,
            payload.role,
        )

    # ==================== MAGIC LINK / EMAIL VERIFICATION ====================

    def create_magic_link_token(self, email: str, expires_minutes: int = 15) -> str:
        """Create a token for magic link authentication."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        payload = {
            "email": email,
            "exp": expire,
            "type": "magic_link",
            "nonce": secrets.token_urlsafe(16),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=JWT_ALGORITHM)

    def verify_magic_link_token(self, token: str) -> Optional[str]:
        """Verify a magic link token and return the email if valid."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "magic_link":
                return None
            return payload.get("email")
        except JWTError:
            return None

    def create_email_verification_token(self, user_id: str, email: str) -> str:
        """Create a token for email verification."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "type": "email_verification",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=JWT_ALGORITHM)

    def verify_email_verification_token(self, token: str) -> Optional[Tuple[str, str]]:
        """Verify an email verification token. Returns (user_id, email) if valid."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "email_verification":
                return None
            return payload.get("sub"), payload.get("email")
        except JWTError:
            return None

    def create_password_reset_token(self, user_id: str, email: str) -> str:
        """Create a token for password reset."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "type": "password_reset",
            "nonce": secrets.token_urlsafe(16),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=JWT_ALGORITHM)

    def verify_password_reset_token(self, token: str) -> Optional[Tuple[str, str]]:
        """Verify a password reset token. Returns (user_id, email) if valid."""
        if jwt is None:
            raise RuntimeError("python-jose not available")

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "password_reset":
                return None
            return payload.get("sub"), payload.get("email")
        except JWTError:
            return None

    # ==================== UTILITY ====================

    def extract_token_from_header(self, authorization: str) -> Optional[str]:
        """Extract token from Authorization header."""
        if not authorization:
            return None
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None
