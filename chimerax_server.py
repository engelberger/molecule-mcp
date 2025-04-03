# chimerax_server.py
import os
import sys
import logging
import traceback
import threading
import time
from mcp.server.fastmcp import FastMCP
from typing import Any, List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('chimerax_server.log')
    ]
)

logger = logging.getLogger('chimerax_server')

# Logging to stderr for server output
def log_info(message):
    """Log info message to stderr for process communication"""
    print(f"INFO: {message}", file=sys.stderr, flush=True)

def log_error(message):
    """Log error message to stderr for process communication"""
    print(f"ERROR: {message}", file=sys.stderr, flush=True)

# Server class
class ChimeraXServer(FastMCP):
    # No __init__ needed anymore for handler registration
    # FastMCP handles registration via decorators on the instance
    pass # Keep the class definition

# Create the server instance at the module level
server = ChimeraXServer(name="ChimeraX") # Provide name here
log_info("Global ChimeraXServer instance created")

# Register the dispatcher function as a tool using the instance
@server.tool()
def execute_command(executable_name: str, args: List[Any] = None, named_args: Dict[str, Any] = None) -> Any:
    """Executes a specific ChimeraX command by name with arguments.
    
    This function can run either:
    1. Built-in Python helper functions (open_chimerax, run_chimerax_command, etc.)
    2. Direct ChimeraX commands (open, view, style, etc.)
    """
    # Ensure defaults if None
    args = args if args is not None else []
    kwargs = named_args if named_args is not None else {}
    
    try:
        logger.info(f"Received execute_command tool call: {executable_name} with args: {args}, kwargs: {kwargs}")
        log_info(f"Executing: {executable_name}")
        
        # Lazy import inside the handler
        # (Keep the imports as they were)
        from chimerax_core import (
            initialize_server_proxy, set_xmlrpc_port, is_chimerax_running, 
            get_chimerax_executable_path, set_chimerax_path
        )
        from chimerax_tools import (
            open_chimerax, run_chimerax_command, close_chimerax,
            fetch_structure, save_session, set_visualization,
            measure_distance, get_session_status, run_script,
            analyze_protein_ligand, get_chimerax_logs
        )
        from chimerax_imaging import (
            capture_chimerax_image, view_saved_image, create_molecular_image
        )
        from chimerax_diagnostics import (
            diagnose_chimerax, debug_mac_path_issue, debug_windows_path_issue
        )
        
        # Map command names to functions
        # (Keep the command_map as it was)
        command_map = {
            "initialize_server_proxy": initialize_server_proxy,
            "set_xmlrpc_port": set_xmlrpc_port,
            "is_chimerax_running": is_chimerax_running,
            "get_chimerax_executable_path": get_chimerax_executable_path,
            "set_chimerax_path": set_chimerax_path,
            "open_chimerax": open_chimerax,
            "run_chimerax_command": run_chimerax_command,
            "close_chimerax": close_chimerax,
            "fetch_structure": fetch_structure,
            "save_session": save_session,
            "set_visualization": set_visualization,
            "measure_distance": measure_distance,
            "get_session_status": get_session_status,
            "run_script": run_script,
            "analyze_protein_ligand": analyze_protein_ligand,
            "get_chimerax_logs": get_chimerax_logs,
            "capture_chimerax_image": capture_chimerax_image,
            "view_saved_image": view_saved_image,
            "create_molecular_image": create_molecular_image,
            "diagnose_chimerax": diagnose_chimerax,
            "debug_mac_path_issue": debug_mac_path_issue,
            "debug_windows_path_issue": debug_windows_path_issue,
        }
        
        if executable_name in command_map:
            try:
                # Execute a Python function from our predefined map
                logger.info(f"Executing Python function: {executable_name} with args {args} and kwargs {kwargs}")
                args_tuple = tuple(args) if isinstance(args, list) else args 
                result = command_map[executable_name](*args_tuple, **kwargs)
                logger.info(f"Python function {executable_name} executed successfully")
                return result
            except Exception as e:
                error_msg = f"Error executing Python function {executable_name}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                return error_msg
        else:
            # Not a Python function - try passing the command directly to ChimeraX
            try:
                # Create a ChimeraX command string by joining the command name with its arguments
                chimerax_cmd = executable_name
                
                # Add any positional arguments
                if args:
                    arg_strings = []
                    for arg in args:
                        if isinstance(arg, str):
                            # Quote strings that contain spaces
                            if ' ' in arg:
                                arg_strings.append(f'"{arg}"')
                            else:
                                arg_strings.append(arg)
                        else:
                            # Convert other types to string
                            arg_strings.append(str(arg))
                    
                    chimerax_cmd += " " + " ".join(arg_strings)
                
                # Add any keyword arguments
                if kwargs:
                    for key, value in kwargs.items():
                        if isinstance(value, str):
                            # Quote string values that contain spaces
                            if ' ' in value:
                                chimerax_cmd += f' {key} "{value}"'
                            else:
                                chimerax_cmd += f' {key} {value}'
                        else:
                            # Convert other types to string
                            chimerax_cmd += f' {key} {value}'
                
                logger.info(f"Passing direct ChimeraX command: {chimerax_cmd}")
                
                # Make sure ChimeraX is running before sending the command
                if not is_chimerax_running():
                    logger.info("ChimeraX is not running, starting it first")
                    open_result = open_chimerax()
                    if "Error" in open_result:
                        return f"Failed to start ChimeraX: {open_result}"
                    # Give it time to start
                    time.sleep(2) 
                
                # Execute the command using run_chimerax_command
                result = run_chimerax_command(chimerax_cmd)
                logger.info(f"Direct ChimeraX command executed with result: {result}")
                return result
            except Exception as e:
                error_msg = f"Error executing direct ChimeraX command: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                return error_msg
            
    except Exception as e:
        error_msg = f"Error handling execute_command tool call: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return error_msg

# We remove handle_view, handle_resource, handle_completion as they weren't implemented
# and we don't have register_handler for them.
# If specific resources or prompts are needed later, they should be added 
# using @server.resource() or @server.prompt() decorators.

def main():
    """Main entry point for running the ChimeraX MCP server directly"""
    try:
        log_info("Starting ChimeraX MCP server using main()")
        # Use the global server instance
        # FastMCP's run() method will start the server with registered tools/resources
        server.run() 
    except Exception as e:
        log_error(f"Critical error in main(): {str(e)}")
        log_error(traceback.format_exc())
        logger.error(f"Critical error in main(): {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
