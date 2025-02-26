import argparse
from .core import execute_test
from .profiles import DEFAULT_PROFILES
from .config import load_config

def main():
    parser = argparse.ArgumentParser(description="Network-DDoS: Advanced Network Testing Tool by It Is Unique Official")
    parser.add_argument("--url", help="Target URL to test")
    parser.add_argument("--requests", type=int, default=500, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent connections")
    parser.add_argument("--rate-limit", type=float, default=0.05, help="Delay between requests (seconds)")
    parser.add_argument("--config", help="Path to config JSON file")
    parser.add_argument("--proxies", nargs="*", help="List of proxy URLs (e.g., http://proxy:port)")
    
    args = parser.parse_args()
    
    # Load config from file if provided, override defaults
    if args.config:
        config = load_config(args.config)
        url = config.get("url", args.url)
        requests = config.get("requests", args.requests)
        concurrency = config.get("concurrency", args.concurrency)
        rate_limit = config.get("rate_limit", args.rate_limit)
        proxies = config.get("proxies", args.proxies)
    else:
        url = args.url
        requests = args.requests
        concurrency = args.concurrency
        rate_limit = args.rate_limit
        proxies = args.proxies
    
    if not url:
        parser.error("The --url argument is required unless provided in a config file.")
    
    execute_test(url, requests, concurrency, rate_limit, DEFAULT_PROFILES, proxies)

if __name__ == "__main__":
    main()
