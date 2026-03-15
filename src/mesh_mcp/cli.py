"""Command-line entry point for mesh-mcp."""
import sys


def main():
    """Start the MeSH MCP server."""
    from mesh_mcp.server import start_mcp_server
    port = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    start_mcp_server(port=port)


if __name__ == "__main__":
    main()
