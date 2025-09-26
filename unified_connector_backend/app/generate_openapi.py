# PUBLIC_INTERFACE
def export_openapi(output_path: str = "interfaces/openapi.json") -> str:
    """
    Export the live OpenAPI schema from the FastAPI application to a JSON file.

    Parameters:
        output_path (str): The relative or absolute path where the OpenAPI JSON
            should be saved. Defaults to "interfaces/openapi.json" at the backend
            container root.

    Returns:
        str: The absolute path to the written OpenAPI JSON file.

    Notes:
        - This module is designed to be executed via: `python -m app.generate_openapi`
          as specified in .project_manifest.yaml under generateOpenapiCommand.
        - It imports the FastAPI `app` from the compatibility layer app.main, which
          ultimately resolves to the instance in src/unified_connector_backend/app.py.
        - No secrets are read; environment variables are not required for exporting
          the schema.
    """
    import json
    import os
    from pathlib import Path

    # Defer import to avoid side effects if this module is imported for introspection.
    try:
        # app.main re-exports the FastAPI app from the src/ package
        from app.main import app  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to import FastAPI app (app.main): {e}")

    # Resolve output path and ensure directory exists
    output_path_abs = Path(output_path).resolve()
    output_path_abs.parent.mkdir(parents=True, exist_ok=True)

    # Generate OpenAPI spec from the running application instance
    schema = app.openapi()

    # Write to disk with pretty formatting for easier diffing
    with output_path_abs.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False, sort_keys=False)

    print(f"[generate_openapi] OpenAPI schema written to: {output_path_abs}")
    return str(output_path_abs)


# PUBLIC_INTERFACE
def main() -> None:
    """
    CLI entrypoint to export the FastAPI OpenAPI schema as JSON.

    Usage:
        python -m app.generate_openapi
        python -m app.generate_openapi --out interfaces/openapi.json
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Export OpenAPI schema to JSON from the Unified Connector Backend."
    )
    parser.add_argument(
        "--out",
        "-o",
        dest="out",
        default="interfaces/openapi.json",
        help="Output path for the OpenAPI JSON (default: interfaces/openapi.json)",
    )
    args = parser.parse_args()
    export_openapi(args.out)


if __name__ == "__main__":
    main()
