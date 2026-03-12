import fastmcp
print(dir(fastmcp))
try:
    from fastmcp import streamable_http_client
    print("streamable_http_client found")
except ImportError:
    print("streamable_http_client not found")
