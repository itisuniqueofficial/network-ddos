from dataclasses import dataclass
from faker import Faker
import json
import random

fake = Faker()

@dataclass
class AttackProfile:
    name: str
    methods: list
    headers: dict
    payload_generator: callable
    delay_variance: float

    def generate_request(self, request_id: int, url: str, proxies: list = None) -> dict:
        method = random.choice(self.methods)
        headers = {k: v() if callable(v) else v for k, v in self.headers.items()}
        payload = self.payload_generator()
        proxy = random.choice(proxies) if proxies else None
        return {
            "id": request_id,
            "method": method,
            "url": url,
            "headers": headers,
            "payload": payload,
            "delay_variance": self.delay_variance,
            "proxy": proxy
        }

DEFAULT_PROFILES = [
    AttackProfile(
        name="Normal Traffic",
        methods=["GET"],
        headers={"User-Agent": lambda: fake.user_agent(), "Accept": "*/*"},
        payload_generator=lambda: None,
        delay_variance=0.1
    ),
    AttackProfile(
        name="API Stress",
        methods=["POST", "PUT"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Type": "application/json"},
        payload_generator=lambda: json.dumps({"id": random.randint(1, 1000), "data": fake.text()}),
        delay_variance=0.05
    ),
    AttackProfile(
        name="Heavy Load",
        methods=["POST"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Length": "1024"},
        payload_generator=lambda: fake.text(max_nb_chars=1024),
        delay_variance=0.02
    )
]
