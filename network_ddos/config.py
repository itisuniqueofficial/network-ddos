import json

def load_config(file_path: str) -> dict:
    """Load configuration from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load config file {file_path}: {e}")
