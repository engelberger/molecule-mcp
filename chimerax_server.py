# server.py
from mcp.server.fastmcp import FastMCP, Image
import subprocess
from xmlrpc.client import ServerProxy
from glob import glob

# Create an MCP server
mcp = FastMCP("chimerax")
xmlrpc_port = 42184
s = ServerProxy(uri="http://127.0.0.1:%d/RPC2" % xmlrpc_port)

@mcp.tool()
def open_chimerax():
    """open chimerax with remote control enabled"""
    chimerax_bin = "/Applications/ChimeraX-*.app/Contents/bin/ChimeraX"
    chimerax_bin = glob(chimerax_bin)[0]
    cmds = [
        chimerax_bin,
        "--cmd", 
        "'remotecontrol xmlrpc true'"
    ]
    subprocess.Popen(
            " ".join(cmds),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            bufsize=1,  # Line-buffered
            universal_newlines=True
        )
    return subprocess.STDOUT

@mcp.tool()
def run_chimerax_command(command: str):
    """run chimerax command"""
    return s.run_command(command)
