import json
import os

from src.api.main import app

# PUBLIC_INTERFACE
def generate_openapi_to_file(path: str = "interfaces/openapi.json") -> None:
    """Generate current OpenAPI schema from the FastAPI app and write to a file."""
    schema = app.openapi()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(schema, f, indent=2)

if __name__ == "__main__":
    # Write to default location
    generate_openapi_to_file()
