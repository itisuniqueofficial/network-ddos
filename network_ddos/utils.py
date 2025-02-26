import asyncio
import matplotlib.pyplot as plt
from typing import Dict

class Metrics:
    def __init__(self):
        self.success = 0
        self.failure = 0
        self.response_times = []
        self.lock = asyncio.Lock()

    async def record(self, success: bool, response_time: float):
        async with self.lock:
            if success:
                self.success += 1
            else:
                self.failure += 1
            self.response_times.append(response_time)

    def summary(self) -> Dict:
        total = self.success + self.failure
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            "total": total,
            "success": self.success,
            "failure": self.failure,
            "success_rate": (self.success / total) * 100 if total > 0 else 0,
            "avg_response_time": avg_time,
            "min_response_time": min(self.response_times or [0]),
            "max_response_time": max(self.response_times or [0])
        }

def plot_metrics(metrics_summary: Dict):
    plt.figure(figsize=(12, 7))
    plt.hist(metrics_summary["response_times"], bins=30, color='green', alpha=0.7)
    plt.title("Network-DDoS Response Time Distribution")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    plt.savefig("response_times.png")
    print("Response time distribution saved as 'response_times.png'")
