# chimerax_core.py
import os
import sys
import glob
import socket
import platform
import subprocess
import time
import random
import logging
import traceback
import xmlrpc.client

# Configure logging
logger = logging.getLogger('chimerax_server')

# Global variables for ChimeraX communication
xmlrpc_port = 42184  # Default XML-RPC port for ChimeraX
s = None  # XML-RPC server proxy

# Platform-specific paths for ChimeraX
CHIMERAX_PATH_WINDOWS = None
CHIMERAX_PATH_MACOS = None
CHIMERAX_PATH_LINUX = None

# Custom path that overrides other paths if set
custom_chimerax_path = None

def set_xmlrpc_port(port):
    """Set the XML-RPC port for ChimeraX communication"""
    global xmlrpc_port
    logger.info(f"Setting XML-RPC port to {port}")
    xmlrpc_port = port
    
    # Reinitialize the server proxy if it exists
    if s is not None:
        initialize_server_proxy(port)
    
    return f"XML-RPC port set to {port}"

def initialize_server_proxy(port=None):
    """Initialize the XML-RPC server proxy for ChimeraX communication"""
    global s, xmlrpc_port
    
    if port is not None:
        xmlrpc_port = port
    
    logger.info(f"Initializing XML-RPC server proxy with port {xmlrpc_port}")
    s = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{xmlrpc_port}")
    return f"XML-RPC server proxy initialized with port {xmlrpc_port}"

def wait_for_port(port, host='127.0.0.1', timeout=30, check_interval=0.5):
    """Wait for a port to become available"""
    logger.info(f"Waiting for port {port} to become available (timeout: {timeout}s)")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(check_interval)
                result = sock.connect_ex((host, port))
                if result == 0:
                    logger.info(f"Port {port} is now available")
                    return True
                logger.debug(f"Port {port} not available yet, waiting...")
        except socket.error as e:
            logger.debug(f"Socket error while checking port: {str(e)}")
        
        # Wait before checking again
        time.sleep(check_interval)
    
    logger.warning(f"Timeout waiting for port {port} to become available")
    return False

def is_chimerax_running():
    """Check if ChimeraX is running with XML-RPC enabled"""
    logger.debug("Checking if ChimeraX is running with XML-RPC enabled")
    
    try:
        # Try to connect to the XML-RPC server
        global s
        if s is None:
            initialize_server_proxy()
        
        # Simple test command
        s.run_command("version")
        logger.debug("ChimeraX is running")
        return True
    except Exception as e:
        logger.debug(f"ChimeraX is not running: {str(e)}")
        return False

def set_chimerax_path(path):
    """Set a custom path for the ChimeraX executable"""
    global custom_chimerax_path
    
    if not path:
        logger.warning("Empty path provided, ignoring")
        return "Error: Empty path provided"
    
    # Normalize path for OS
    path = os.path.normpath(path)
    
    # Verify the path exists
    if not os.path.exists(path):
        logger.warning(f"ChimeraX path does not exist: {path}")
        return f"Error: Path does not exist: {path}"
    
    # Set the custom path
    custom_chimerax_path = path
    logger.info(f"Custom ChimeraX path set to: {custom_chimerax_path}")
    
    return f"ChimeraX path set to: {custom_chimerax_path}"

def get_chimerax_executable_path():
    """Get the path to the ChimeraX executable"""
    logger.debug("Getting ChimeraX executable path")
    
    # If custom path is set, use it
    if custom_chimerax_path:
        logger.info(f"Using custom ChimeraX path: {custom_chimerax_path}")
        return custom_chimerax_path
    
    # Get system-specific path
    system = platform.system()
    
    if system == "Windows":
        return get_windows_chimerax_path()
    elif system == "Darwin":  # macOS
        return get_macos_chimerax_path()
    elif system == "Linux":
        return get_linux_chimerax_path()
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")

def get_windows_chimerax_path():
    """Get the path to ChimeraX on Windows"""
    global CHIMERAX_PATH_WINDOWS
    
    # Return cached path if available
    if CHIMERAX_PATH_WINDOWS:
        return CHIMERAX_PATH_WINDOWS
    
    logger.debug("Finding ChimeraX path on Windows")
    
    # Get Program Files path
    program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
    
    # Try different possible locations
    paths_to_check = [
        # Direct paths (most reliable)
        f"{program_files}\\ChimeraX\\bin\\ChimeraX.exe",
        f"{program_files}\\UCSF ChimeraX\\bin\\ChimeraX.exe",
        f"{program_files_x86}\\ChimeraX\\bin\\ChimeraX.exe",
        f"{program_files_x86}\\UCSF ChimeraX\\bin\\ChimeraX.exe",
        f"{program_files}\\ChimeraX 1.9\\bin\\ChimeraX.exe",
        f"{program_files_x86}\\ChimeraX 1.9\\bin\\ChimeraX.exe",
        
        # Glob patterns (less reliable)
        f"{program_files}\\ChimeraX*\\bin\\ChimeraX.exe",
        f"{program_files_x86}\\ChimeraX*\\bin\\ChimeraX.exe"
    ]
    
    # Try each path
    for path in paths_to_check:
        logger.debug(f"Checking path: {path}")
        
        # Handle direct paths vs glob patterns
        if '*' in path:
            # Glob pattern
            found_paths = glob.glob(path)
            if found_paths:
                CHIMERAX_PATH_WINDOWS = found_paths[0]
                logger.info(f"Found ChimeraX at: {CHIMERAX_PATH_WINDOWS}")
                return CHIMERAX_PATH_WINDOWS
        else:
            # Direct path
            if os.path.exists(path):
                CHIMERAX_PATH_WINDOWS = path
                logger.info(f"Found ChimeraX at: {CHIMERAX_PATH_WINDOWS}")
                return CHIMERAX_PATH_WINDOWS
    
    # If not found, try registry
    try:
        import winreg
        from chimerax_diagnostics import check_windows_registry
        
        registry_paths = check_windows_registry()
        
        if registry_paths:
            for reg_key, install_path in registry_paths.items():
                # Check for bin/ChimeraX.exe
                exe_path = os.path.join(install_path, "bin", "ChimeraX.exe")
                if os.path.exists(exe_path):
                    CHIMERAX_PATH_WINDOWS = exe_path
                    logger.info(f"Found ChimeraX in registry at: {CHIMERAX_PATH_WINDOWS}")
                    return CHIMERAX_PATH_WINDOWS
    except Exception as e:
        logger.warning(f"Error checking registry: {str(e)}")
    
    # If still not found, raise error
    logger.error("ChimeraX executable not found on Windows")
    raise FileNotFoundError("ChimeraX executable not found. Please install ChimeraX or set the path manually with set_chimerax_path()")

def get_macos_chimerax_path():
    """Get the path to ChimeraX on macOS"""
    global CHIMERAX_PATH_MACOS
    
    # Return cached path if available
    if CHIMERAX_PATH_MACOS:
        return CHIMERAX_PATH_MACOS
    
    logger.debug("Finding ChimeraX path on macOS")
    
    # Try different possible locations
    paths = [
        # App bundle with version
        "/Applications/ChimeraX-*.app/Contents/bin/ChimeraX",
        # App bundle without version
        "/Applications/ChimeraX.app/Contents/bin/ChimeraX",
        # App bundle with UCSF prefix
        "/Applications/UCSF ChimeraX.app/Contents/bin/ChimeraX",
        # User Applications folder
        os.path.expanduser("~/Applications/ChimeraX*.app/Contents/bin/ChimeraX"),
        os.path.expanduser("~/Applications/UCSF ChimeraX.app/Contents/bin/ChimeraX")
    ]
    
    # Try each path
    for path_pattern in paths:
        logger.debug(f"Checking path pattern: {path_pattern}")
        matching_paths = glob.glob(path_pattern)
        
        if matching_paths:
            CHIMERAX_PATH_MACOS = matching_paths[0]
            logger.info(f"Found ChimeraX at: {CHIMERAX_PATH_MACOS}")
            return CHIMERAX_PATH_MACOS
    
    # If no path worked, check all applications to find any with ChimeraX in the name
    try:
        apps_dir = "/Applications"
        for app in os.listdir(apps_dir):
            if "himerax" in app.lower():  # Case-insensitive check
                potential_path = os.path.join(apps_dir, app, "Contents/bin/ChimeraX")
                if os.path.exists(potential_path):
                    CHIMERAX_PATH_MACOS = potential_path
                    logger.info(f"Found ChimeraX at: {CHIMERAX_PATH_MACOS}")
                    return CHIMERAX_PATH_MACOS
    except Exception as e:
        logger.warning(f"Error checking Applications directory: {str(e)}")
    
    # If still not found, raise error
    logger.error("ChimeraX executable not found on macOS")
    raise FileNotFoundError("ChimeraX executable not found. Please install ChimeraX or set the path manually with set_chimerax_path()")

def get_linux_chimerax_path():
    """Get the path to ChimeraX on Linux"""
    global CHIMERAX_PATH_LINUX
    
    # Return cached path if available
    if CHIMERAX_PATH_LINUX:
        return CHIMERAX_PATH_LINUX
    
    logger.debug("Finding ChimeraX path on Linux")
    
    # Try different possible locations
    paths = [
        # Common install locations
        "/opt/UCSF/ChimeraX*/bin/ChimeraX",
        "/usr/local/bin/ChimeraX",
        "/usr/bin/ChimeraX",
        # User local installation
        os.path.expanduser("~/UCSF-ChimeraX*/bin/ChimeraX"),
        os.path.expanduser("~/.local/bin/ChimeraX")
    ]
    
    # Try each path
    for path_pattern in paths:
        logger.debug(f"Checking path pattern: {path_pattern}")
        matching_paths = glob.glob(path_pattern)
        
        if matching_paths:
            CHIMERAX_PATH_LINUX = matching_paths[0]
            logger.info(f"Found ChimeraX at: {CHIMERAX_PATH_LINUX}")
            return CHIMERAX_PATH_LINUX
    
    # Try using 'which' command
    try:
        which_output = subprocess.check_output(["which", "ChimeraX"], 
                                              stderr=subprocess.DEVNULL, 
                                              universal_newlines=True).strip()
        if which_output:
            CHIMERAX_PATH_LINUX = which_output
            logger.info(f"Found ChimeraX using 'which' at: {CHIMERAX_PATH_LINUX}")
            return CHIMERAX_PATH_LINUX
    except Exception:
        pass
    
    # If still not found, raise error
    logger.error("ChimeraX executable not found on Linux")
    raise FileNotFoundError("ChimeraX executable not found. Please install ChimeraX or set the path manually with set_chimerax_path()")

# Initialize the XML-RPC server proxy
try:
    initialize_server_proxy()
except Exception as e:
    logger.info(f"Initial XML-RPC server proxy initialization failed (expected): {str(e)}") 