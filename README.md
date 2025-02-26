# Network-DDoS

**Network-DDoS** is an advanced network testing tool developed by **It Is Unique Official** for educational purposes. It allows users to simulate various traffic patterns and analyze server performance under controlled conditions. This tool is designed to help students, developers, and researchers understand network behavior, concurrency, and server resilience in a safe and ethical manner.

## Features
- **Asynchronous Requests**: Powered by `aiohttp` for high-performance, non-blocking HTTP requests.
- **Customizable Profiles**: Predefined attack profiles (Normal Traffic, API Stress, Heavy Load) with configurable methods, headers, and payloads.
- **Proxy Support**: Simulate distributed traffic using a list of proxy servers.
- **Real-Time Progress**: Track request progress with a `tqdm`-powered progress bar.
- **Metrics & Visualization**: Detailed statistics (success rate, response times) with a graphical histogram (`matplotlib`).
- **Flexible Configuration**: Use command-line arguments or a JSON config file for easy customization.

## Installation

### Prerequisites
- **Python**: Version 3.8 or higher.
- **Git**: For cloning the repository.
- A local or remote server for testing (you must have permission to test it).

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/network-ddos.git
   cd network-ddos
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install the Tool**:
   ```bash
   pip install .
   ```

## How to Use

### Command-Line Interface (CLI)
Run the tool directly with command-line arguments:
```bash
network-ddos --url http://localhost:5000 --requests 500 --concurrency 50 --rate-limit 0.05 --proxies http://proxy1:port http://proxy2:port
```
- `--url`: The target server URL (required).
- `--requests`: Number of requests to send (default: 500).
- `--concurrency`: Number of concurrent connections (default: 50).
- `--rate-limit`: Delay between requests in seconds (default: 0.05).
- `--proxies`: Optional list of proxy URLs (e.g., `http://proxy:port`).
- `--config`: Path to a JSON configuration file (optional, overrides CLI args).

### Using a Configuration File
Create a `config.json` file with your settings:
```json
{
    "url": "http://localhost:5000",
    "requests": 1000,
    "concurrency": 100,
    "rate_limit": 0.02,
    "proxies": ["http://proxy1:port", "http://proxy2:port"]
}
```
Run the tool with the config file:
```bash
network-ddos --config config.json
```

## Example Test Server
To test locally, set up a simple Flask server:
```python
from flask import Flask
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST', 'PUT'])
def index():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(port=5000)
```
Start the server in one terminal, then run `network-ddos` in another.

## Output
- **Console**: Displays real-time progress and a summary of results (total requests, success/failure rates, response times).
- **Log File**: Detailed logs saved to `network_ddos.log`.
- **Graph**: A histogram of response times saved as `response_times.png`.

## Advanced Configuration

### Customizing Profiles
Edit `network_ddos/profiles.py` to add or modify attack profiles. Example:
```python
AttackProfile(
    name="Custom Profile",
    methods=["GET", "POST"],
    headers={"User-Agent": lambda: fake.user_agent(), "Custom-Header": "Test"},
    payload_generator=lambda: json.dumps({"key": "value"}),
    delay_variance=0.03
)
```
Add it to `DEFAULT_PROFILES` to use it in tests.

### Proxy Setup
Provide a list of proxies to simulate distributed traffic:
```bash
network-ddos --url http://example.com --proxies http://proxy1:port http://proxy2:port
```
Ensure proxies are functional and support HTTP traffic.

## Requirements

- **Python**: 3.8+
- **Dependencies**:
  - `aiohttp>=3.8.0`
  - `faker>=13.0.0`
  - `matplotlib>=3.5.0`
  - `tqdm>=4.64.0`

## Ethical Use
This tool is for educational purposes only. Use it responsibly:
- Test only servers you own or have explicit permission to test.
- Unauthorized testing of public servers is illegal and unethical.
- Respect network resources and legal boundaries.

## Troubleshooting

- **"ModuleNotFoundError"**: Ensure all dependencies are installed (`pip install -r requirements.txt`).
- **Connection Errors**: Verify the target URL is reachable and the server is running.
- **Proxy Issues**: Check proxy URLs and ensure they’re operational.
- **Permission Denied**: Run with appropriate permissions (e.g., `sudo` on some systems).

## Contributing
We welcome contributions! To contribute:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to your fork (`git push origin feature/your-feature`).
5. Open a pull request.

## License
Distributed under the MIT License. See `LICENSE` for details.

## Authors
Developed by: **It Is Unique Official**
Contact: [contact@itisuniqueofficial.com](mailto:contact@itisuniqueofficial.com)

## Version
Current Version: **1.0.0**

## Acknowledgments
- Built with open-source libraries: `aiohttp`, `faker`, `matplotlib`, `tqdm`.
- Inspired by educational needs in network testing and performance analysis.

---

## Notes
- **Comprehensive Guide**: This `README.md` includes detailed sections on installation, usage (CLI and config file), example server setup, advanced configuration options, troubleshooting, and more.
- **Customization**: Replace `itisuniqueofficial` and `contact@itisuniqueofficial.com` with your actual GitHub username and email.
- **Educational Focus**: Emphasizes ethical use and provides practical examples to ensure it’s beginner-friendly yet powerful for advanced users.

Happy testing with **Network-DDoS**! For support, open an issue on GitHub.

