# Network DDoS Simulator

Welcome to the **Network DDoS Simulator**, a Python-based tool designed for educational purposes to simulate realistic web traffic and test network resilience. This repository contains the `ddos.py` script, which mimics user behavior with configurable options and a real-time dashboard.

**GitHub Repository**: [itisuniqueofficial/network-ddos](https://github.com/itisuniqueofficial/network-ddos)

## Features

- **Realistic Traffic**: Simulates browser-like requests with randomized headers, page navigation, and delays.
- **Real-Time Dashboard**: Displays live stats (requests, successes, errors, rate) using a rich CLI interface.
- **CLI Control**: Fully configurable via command-line arguments (e.g., `--target`, `--threads`).
- **Page Discovery**: Dynamically explores target site links for varied traffic patterns.
- **Proxy Support**: Optional IP rotation with proxy list integration (manual setup required).

## Prerequisites

- Python 3.8 or higher
- Git (optional, for cloning the repository)

## Installation

### Clone the Repository:
```bash
git clone https://github.com/itisuniqueofficial/network-ddos.git
cd network-ddos
```

### Install Dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the `ddos.py` script with the required `--target` argument and optional parameters.

### Basic Command:
```bash
python ddos.py --target https://example.com
```

### Custom Options:
```bash
python ddos.py --target https://example.com --threads 20 --max-requests 100 --delay 0.3
```

## Command-Line Arguments

| Argument      | Description                         | Default |
|--------------|-------------------------------------|---------|
| `--target`   | Target URL (required)              | N/A     |
| `--threads`  | Number of concurrent threads       | 10      |
| `--delay`    | Base delay between requests (sec)  | 0.5     |
| `--timeout`  | Request timeout (sec)              | 5       |
| `--max-requests` | Max requests per thread         | 50      |

## Example Output

```
Starting DDoS simulation on https://example.com...
Initial pages: ['https://example.com/', 'https://example.com/about']

Dashboard:
DDoS Simulation - Target: https://example.com    Threads: 10/10    Press Ctrl+C to stop
┌─────────────── Real-Time Stats ───────────────┐
│ Metric        │ Value                          │
├───────────────┼───────────────────────────────┤
│ Total Requests│ 45                             │
│ Successes     │ 42                             │
│ Errors        │ 3                              │
│ Req/Min       │ 180.50                         │
│ Queue Size    │ 5                              │
└───────────────┴───────────────────────────────┘
[SUCCESS] Thread 0 | Visited https://example.com/about | Status: 200
```

## Testing Locally

### Setup a Local Server (e.g., Flask):
```python
from flask import Flask, request
app = Flask(__name__)

@app.route('/<path:path>', methods=['GET'])
@app.route('/', defaults={'path': ''})
def catch_all(path):
    print(f"Request: {request.path}")
    return "<a href='/page1'>Next</a>"

if __name__ == "__main__":
    app.run(port=8000)
```

### Run the Simulation:
```bash
python ddos.py --target http://localhost:8000
```

## Proxy Support

To simulate traffic from multiple IPs:

1. Add proxies to the `PROXY_LIST` variable in `ddos.py`:
```python
PROXY_LIST = [{'http': 'http://proxy_ip:port'}, ...]
```

2. Rerun the script.

## Ethical Use

**Important**: This tool is for educational and testing purposes only. Do not use it against websites or servers without explicit permission. Unauthorized DDoS attacks are illegal and unethical.

## Contributing

Feel free to fork this repository, submit issues, or create pull requests. Contributions are welcome!

1. Fork the repo: `itisuniqueofficial/network-ddos`
2. Create a branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature"`
4. Push: `git push origin feature-name`
5. Open a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For questions or support, open an issue on GitHub or contact **itisuniqueofficial**.

---

## How to Use These Files

1. **Add to Repository**:
   - Place `requirements.txt` and `README.md` in the root of `itisuniqueofficial/network-ddos` alongside `ddos.py`.
   - Commit and push:
     ```bash
     git add requirements.txt README.md ddos.py
     git commit -m "Add requirements and README"
     git push origin main
     ```

2. **Verify on GitHub**:
   - Visit `https://github.com/itisuniqueofficial/network-ddos` to see the rendered `README.md` and files.
