import aiohttp
import asyncio
import random
import logging
import sys
import argparse
import time
import json
from fake_useragent import UserAgent
from colorama import init, Fore, Style
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from bs4 import BeautifulSoup
import urllib.parse
from queue import Queue
import sqlite3
from aiohttp_socks import ProxyConnector

# Initialize tools
init()  # Colorama
console = Console()
logging.basicConfig(
    filename='advanced_traffic_simulation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
DEFAULT_TARGET = "http://localhost:8000"
DEFAULT_CONCURRENCY = 10
DEFAULT_DELAY = 0.5
DEFAULT_TIMEOUT = 5
DEFAULT_MAX_REQUESTS = 50

# Global state
request_counter = 0
success_counter = 0
error_counter = 0
active_tasks = 0
lock = asyncio.Lock()
ua = UserAgent()
page_queue = Queue()
stats = {'rate': 0, 'last_update': time.time()}
proxy_list = []

# SQLite setup for analytics
conn = sqlite3.connect('traffic_stats.db')
conn.execute('''CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    url TEXT,
    status INTEGER,
    thread_id INTEGER,
    proxy TEXT
)''')
conn.commit()

async def fetch_proxies():
    """Fetch free proxies from an API."""
    global proxy_list
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http") as resp:
                proxies = await resp.text()
                proxy_list = [{'http': f"http://{p}"} for p in proxies.splitlines() if p]
        console.print(f"[yellow]Fetched {len(proxy_list)} proxies[/yellow]")
    except Exception as e:
        logging.error(f"Proxy fetch failed: {str(e)}")
        proxy_list = []

def get_random_headers(referer=None):
    """Generate realistic browser headers."""
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'fr-FR,fr;q=0.9', 'de-DE,de;q=0.9']),
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': referer or random.choice(['https://google.com', 'https://bing.com', None]),
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
    }

async def discover_pages(base_url, session):
    """Dynamically discover pages and forms."""
    try:
        async with session.get(base_url, headers=get_random_headers()) as response:
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            links = [urllib.parse.urljoin(base_url, a.get('href')) 
                     for a in soup.find_all('a', href=True) 
                     if urllib.parse.urljoin(base_url, a.get('href')).startswith(base_url)]
            forms = [urllib.parse.urljoin(base_url, form.get('action')) 
                     for form in soup.find_all('form') if form.get('action')]
            return list(set(links + forms)) if links or forms else [base_url]
    except Exception as e:
        logging.error(f"Page discovery failed: {str(e)}")
        return [base_url]

async def simulate_user(thread_id, base_url, pages, args, semaphore):
    """Simulate a complex user journey asynchronously."""
    global request_counter, success_counter, error_counter, active_tasks
    sent_requests = 0
    async with semaphore:
        async with lock:
            active_tasks += 1
        
        # Proxy setup
        proxy = random.choice(proxy_list) if proxy_list else None
        connector = ProxyConnector.from_url(proxy['http']) if proxy else None
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=args.timeout)) as session:
            user_state = {'logged_in': False, 'visited': []}  # Track user state
            
            while sent_requests < args.max_requests:
                target_url = (random.choice(pages) if random.random() > 0.3 
                              else page_queue.get() if not page_queue.empty() else base_url)
                headers = get_random_headers(referer=user_state['visited'][-1] if user_state['visited'] else None)
                
                try:
                    # Behavioral simulation
                    if 'login' in target_url.lower() and not user_state['logged_in'] and random.random() < 0.3:
                        data = {'username': 'test', 'password': 'pass123'}
                        async with session.post(target_url, headers=headers, data=data) as response:
                            user_state['logged_in'] = response.status == 200
                    elif 'search' in target_url.lower() and random.random() < 0.2:
                        data = {'query': random.choice(['test', 'product', 'info'])}
                        async with session.post(target_url, headers=headers, data=data) as response:
                            pass
                    else:
                        async with session.get(target_url, headers=headers) as response:
                            pass

                    status = response.status
                    async with lock:
                        request_counter += 1
                        success_counter += 1 if status == 200 else 0
                        error_counter += 1 if status != 200 else 0
                        now = time.time()
                        stats['rate'] = (request_counter / (now - stats['last_update'])) * 60
                        stats['last_update'] = now
                    
                    log_msg = f"Thread {thread_id} | {response.method} {target_url} | Status: {status}"
                    console.print(f"{Fore.GREEN if status == 200 else Fore.RED}[{'SUCCESS' if status == 200 else 'ERROR'}]{Style.RESET_ALL} {log_msg}")
                    logging.info(log_msg)
                    conn.execute("INSERT INTO requests (timestamp, url, status, thread_id, proxy) VALUES (?, ?, ?, ?, ?)",
                                 (time.strftime('%Y-%m-%d %H:%M:%S'), target_url, status, thread_id, str(proxy)))
                    conn.commit()

                    user_state['visited'].append(target_url)
                    if random.random() < 0.2:
                        new_pages = await discover_pages(target_url, session)
                        for page in new_pages:
                            page_queue.put(page)
                    
                    # Simulate sub-resource or time on page
                    if random.random() < 0.5:
                        sub_url = f"{target_url.rstrip('/')}/static/{random.randint(1, 100)}.js"
                        async with session.get(sub_url, headers=headers) as _:
                            pass
                    await asyncio.sleep(random.uniform(1, 6))

                except Exception as e:
                    async with lock:
                        request_counter += 1
                        error_counter += 1
                    log_msg = f"Thread {thread_id} | Failed {target_url}: {str(e)}"
                    console.print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {log_msg}")
                    logging.error(log_msg)

                sent_requests += 1
                await asyncio.sleep(args.delay * random.uniform(0.5, 1.5))
        
        async with lock:
            active_tasks -= 1

def create_dashboard():
    """Create an interactive dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="stats", size=12),
        Layout(name="controls", size=5)
    )
    return layout

def update_dashboard(layout, live):
    """Update the real-time dashboard."""
    with lock:
        layout["header"].update(
            Table.grid(expand=True).add_row(
                f"[yellow]Advanced Traffic Simulation - Target: {args.target}[/yellow]",
                f"[yellow]Tasks: {active_tasks}/{args.concurrency}[/yellow]",
                f"[yellow]Press Ctrl+C to stop[/yellow]"
            )
        )
        
        stats_table = Table(title="Real-Time Stats", expand=True)
        stats_table.add_column("Metric", justify="left")
        stats_table.add_column("Value", justify="right")
        stats_table.add_row("Total Requests", str(request_counter))
        stats_table.add_row("Successes", str(success_counter))
        stats_table.add_row("Errors", str(error_counter))
        stats_table.add_row("Req/Min", f"{stats['rate']:.2f}")
        stats_table.add_row("Queue Size", str(page_queue.qsize()))
        stats_table.add_row("Proxies", str(len(proxy_list)))
        layout["stats"].update(stats_table)
        
        controls_table = Table(title="Controls", expand=True)
        controls_table.add_column("Action", justify="left")
        controls_table.add_row("[Not Implemented] Pause/Resume: P")
        controls_table.add_row("[Not Implemented] Adjust Rate: +/-")
        layout["controls"].update(controls_table)

async def start_simulation(args):
    """Start the advanced simulation."""
    console.print(f"[yellow]Starting advanced traffic simulation...[/yellow]")
    logging.info(f"Simulation started on {args.target} with {args.concurrency} tasks")

    # Fetch proxies
    await fetch_proxies()
    
    # Initial page discovery
    async with aiohttp.ClientSession() as session:
        pages = await discover_pages(args.target, session)
    for page in pages:
        page_queue.put(page)
    console.print(f"[yellow]Initial pages: {pages}[/yellow]")

    # Setup dashboard
    layout = create_dashboard()
    semaphore = asyncio.Semaphore(args.concurrency)
    
    async with Live(layout, refresh_per_second=4, console=console) as live:
        tasks = [asyncio.create_task(simulate_user(i, args.target, pages, args, semaphore)) 
                 for i in range(args.concurrency)]
        
        while active_tasks > 0 or any(not t.done() for t in tasks):
            update_dashboard(layout, live)
            await asyncio.sleep(0.25)
        
        await asyncio.gather(*tasks, return_exceptions=True)

    logging.info("Simulation completed")
    conn.close()

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Advanced Async Traffic Simulation")
    parser.add_argument('--target', default=DEFAULT_TARGET, help="Target URL")
    parser.add_argument('--concurrency', type=int, default=DEFAULT_CONCURRENCY, help="Concurrent tasks")
    parser.add_argument('--delay', type=float, default=DEFAULT_DELAY, help="Base delay (seconds)")
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT, help="Request timeout (seconds)")
    parser.add_argument('--max-requests', type=int, default=DEFAULT_MAX_REQUESTS, help="Max requests per task")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(start_simulation(args))
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Simulation stopped by user[/yellow]")
        logging.info("Simulation stopped by user")
        console.print(f"Final Stats - Requests: {request_counter}, Success: {success_counter}, Errors: {error_counter}")
        console.print("Check 'advanced_traffic_simulation.log' and 'traffic_stats.db' for details.")
