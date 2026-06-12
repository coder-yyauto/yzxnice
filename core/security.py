from __future__ import annotations

import base64
import io
import os
import random
import secrets
import string
import time
import uuid
from datetime import datetime, timedelta
from typing import cast

import argon2
from PIL import Image, ImageDraw, ImageFont

TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"


class PasswordManager:
    _hasher: argon2.PasswordHasher = argon2.PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32)

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cast(str, cls._hasher.hash(password))

    @classmethod
    def verify_password(cls, hashed_password: str, password: str) -> bool:
        try:
            cls._hasher.verify(hashed_password, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
        except argon2.exceptions.VerificationError:
            return False
        except argon2.exceptions.InvalidHashError:
            return False

    @staticmethod
    def generate_random_password(length: int = 8) -> str:
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(length))


class LoginAttemptManager:
    MAX_ATTEMPTS: int = 5
    MAX_IP_ATTEMPTS: int = 30
    LOCK_SECONDS: int = 15 * 60

    @classmethod
    def _count_recent(cls, username: str) -> int:
        from core.models import LoginAttempt
        from database import get_db

        cutoff = datetime.utcnow() - timedelta(seconds=cls.LOCK_SECONDS)
        with get_db() as db:
            return cast(
                int,
                db.query(LoginAttempt)
                .filter(
                    LoginAttempt.username == username,
                    LoginAttempt.attempted_at >= cutoff,
                )
                .count(),
            )

    @classmethod
    def is_locked(cls, username: str) -> bool:
        return cls._count_recent(username) >= cls.MAX_ATTEMPTS

    @classmethod
    def record_failure(cls, username: str, ip_address: str = "") -> int:
        from core.models import LoginAttempt
        from database import get_db

        with get_db() as db:
            attempt = LoginAttempt(username=username, ip_address=ip_address or None)
            db.add(attempt)
            db.commit()
        recent = cls._count_recent(username)
        remaining = cls.MAX_ATTEMPTS - recent
        return max(remaining, 0)

    @classmethod
    def is_ip_blocked(cls, ip_address: str) -> bool:
        if not ip_address:
            return False
        from core.models import LoginAttempt
        from database import get_db

        cutoff = datetime.utcnow() - timedelta(seconds=cls.LOCK_SECONDS)
        with get_db() as db:
            count = (
                db.query(LoginAttempt)
                .filter(
                    LoginAttempt.ip_address == ip_address,
                    LoginAttempt.attempted_at >= cutoff,
                )
                .count()
            )
        return cast(bool, count >= cls.MAX_IP_ATTEMPTS)

    @classmethod
    def reset(cls, username: str) -> None:
        from core.models import LoginAttempt
        from database import get_db

        with get_db() as db:
            db.query(LoginAttempt).filter(LoginAttempt.username == username).delete()
            db.commit()

    @classmethod
    def get_lock_remaining(cls, username: str) -> int:
        from core.models import LoginAttempt
        from database import get_db

        with get_db() as db:
            oldest = (
                db.query(LoginAttempt)
                .filter(LoginAttempt.username == username)
                .order_by(LoginAttempt.attempted_at.asc())
                .first()
            )
        if oldest is None:
            return 0
        recent_count = cls._count_recent(username)
        if recent_count < cls.MAX_ATTEMPTS:
            return 0
        elapsed = (datetime.utcnow() - oldest.attempted_at).total_seconds()
        return max(int(cls.LOCK_SECONDS - elapsed), 0)


class CaptchaManager:
    _captchas: dict[str, tuple[str, float]] = {}

    @classmethod
    def generate(cls) -> tuple[str, str, str]:
        captcha_id: str = str(uuid.uuid4())
        captcha_text: str = "1234" if TEST_MODE else "".join(secrets.choice(string.digits) for _ in range(4))
        image: Image.Image = cls._generate_image(captcha_text)
        buffer: io.BytesIO = io.BytesIO()
        image.save(buffer, format="PNG")

        image_base64: str = base64.b64encode(buffer.getvalue()).decode()
        image_data_url: str = f"data:image/png;base64,{image_base64}"
        cls._captchas[captcha_id] = (captcha_text, time.time())
        cls._cleanup_expired()
        return captcha_id, captcha_text, image_data_url

    @classmethod
    def verify(cls, captcha_id: str, user_input: str) -> bool:
        if TEST_MODE:
            return True
        if captcha_id not in cls._captchas:
            return False
        stored_text: str
        created_time: float
        stored_text, created_time = cls._captchas[captcha_id]
        if time.time() - created_time > 300:
            del cls._captchas[captcha_id]
            return False
        del cls._captchas[captcha_id]
        return stored_text == user_input.strip()

    @classmethod
    def _generate_image(cls, text: str) -> Image.Image:
        width: int = 140
        height: int = 44
        image: Image.Image = Image.new("RGB", (width, height), color=(240, 242, 245))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except Exception:
            font = ImageFont.load_default()
        char_spacing: int = 28
        total_w: int = char_spacing * (len(text) - 1)
        text_x: float = (width - total_w) // 2
        text_y: float = (height - 24) // 2
        for _ in range(100):
            x: int = random.randint(0, width - 1)
            y: int = random.randint(0, height - 1)
            draw.point(
                (x, y),
                fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)),
            )
        for i, char in enumerate(text):
            cx: int = int(text_x + i * char_spacing + random.randint(-3, 3))
            cy: int = int(text_y + random.randint(-3, 3))
            color: tuple[int, int, int] = (
                random.randint(30, 100),
                random.randint(30, 100),
                random.randint(30, 100),
            )
            draw.text((cx, cy), char, font=font, fill=color)
        return image

    @classmethod
    def _cleanup_expired(cls) -> None:
        current_time: float = time.time()
        expired_ids: list[str] = [
            cid for cid, (_, created_time) in cls._captchas.items() if current_time - created_time > 300
        ]
        for cid in expired_ids:
            del cls._captchas[cid]
