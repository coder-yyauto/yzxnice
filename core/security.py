import io
import os
import random
import string
import time
import uuid

import argon2
from PIL import Image, ImageDraw, ImageFont

from config import config

TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"


class PasswordManager:
    _hasher = argon2.PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32)

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls._hasher.hash(password)

    @classmethod
    def verify_password(cls, hashed_password: str, password: str) -> bool:
        try:
            cls._hasher.verify(hashed_password, password)
            return True
        except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError):
            return False
        except Exception:
            return False


class LoginAttemptManager:
    _attempts: dict[str, list[float]] = {}
    MAX_ATTEMPTS = 5
    LOCK_SECONDS = 15 * 60

    @classmethod
    def is_locked(cls, username: str) -> bool:
        cls._cleanup(username)
        attempts = cls._attempts.get(username, [])
        return len(attempts) >= cls.MAX_ATTEMPTS

    @classmethod
    def record_failure(cls, username: str) -> int:
        cls._cleanup(username)
        if username not in cls._attempts:
            cls._attempts[username] = []
        cls._attempts[username].append(time.time())
        remaining = cls.MAX_ATTEMPTS - len(cls._attempts[username])
        return max(remaining, 0)

    @classmethod
    def reset(cls, username: str):
        cls._attempts.pop(username, None)

    @classmethod
    def get_lock_remaining(cls, username: str) -> int:
        cls._cleanup(username)
        attempts = cls._attempts.get(username, [])
        if len(attempts) < cls.MAX_ATTEMPTS:
            return 0
        elapsed = time.time() - attempts[0]
        return max(int(cls.LOCK_SECONDS - elapsed), 0)

    @classmethod
    def _cleanup(cls, username: str):
        now = time.time()
        attempts = cls._attempts.get(username, [])
        cls._attempts[username] = [t for t in attempts if now - t < cls.LOCK_SECONDS]
        if not cls._attempts[username]:
            cls._attempts.pop(username, None)


class CaptchaManager:
    _captchas: dict[str, tuple[str, float]] = {}

    @classmethod
    def generate(cls) -> tuple[str, str, str]:
        captcha_id = str(uuid.uuid4())
        if TEST_MODE:
            captcha_text = "1234"
        else:
            captcha_text = "".join(random.choices(string.digits, k=4))
        image = cls._generate_image(captcha_text)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        import base64

        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        image_data_url = f"data:image/png;base64,{image_base64}"
        cls._captchas[captcha_id] = (captcha_text, time.time())
        cls._cleanup_expired()
        return captcha_id, captcha_text, image_data_url

    @classmethod
    def verify(cls, captcha_id: str, user_input: str) -> bool:
        if TEST_MODE:
            return True
        if captcha_id not in cls._captchas:
            return False
        stored_text, created_time = cls._captchas[captcha_id]
        if time.time() - created_time > 300:
            del cls._captchas[captcha_id]
            return False
        del cls._captchas[captcha_id]
        return stored_text == user_input.strip()

    @classmethod
    def _generate_image(cls, text: str) -> Image.Image:
        width, height = 140, 44
        image = Image.new("RGB", (width, height), color=(240, 242, 245))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except Exception:
            font = ImageFont.load_default()
        char_spacing = 28
        total_w = char_spacing * (len(text) - 1)
        text_x = (width - total_w) // 2
        text_y = (height - 24) // 2
        for _ in range(100):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            draw.point(
                (x, y),
                fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)),
            )
        for i, char in enumerate(text):
            x = text_x + i * char_spacing + random.randint(-3, 3)
            y = text_y + random.randint(-3, 3)
            color = (random.randint(30, 100), random.randint(30, 100), random.randint(30, 100))
            draw.text((x, y), char, font=font, fill=color)
        return image

    @classmethod
    def _cleanup_expired(cls):
        current_time = time.time()
        expired_ids = [
            cid for cid, (_, created_time) in cls._captchas.items() if current_time - created_time > 300
        ]
        for cid in expired_ids:
            del cls._captchas[cid]
