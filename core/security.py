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
        width, height = 120, 40
        image = Image.new("RGB", (width, height), color=(240, 242, 245))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except Exception:
            font = ImageFont.load_default()
        text_width = draw.textlength(text, font=font)
        text_x = (width - text_width) // 2
        text_y = (height - 24) // 2
        for _ in range(100):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point(
                (x, y),
                fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)),
            )
        for i, char in enumerate(text):
            x = text_x + i * 25 + random.randint(-5, 5)
            y = text_y + random.randint(-5, 5)
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
