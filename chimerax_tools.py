# chimerax_tools.py
import os
import time
import platform
import subprocess
import tempfile
import logging
import traceback

# Import from other modules
from chimerax_server import log_info, log_error
from chimerax_core import (
    s, xmlrpc_port, wait_for_port, is_chimerax_running, get_chimerax_executable_path,
    set_xmlrpc_port  # Import directly from core instead of creating a proxy function
)
from chimerax_session import chimerax_session

# Configure logging
logger = logging.getLogger('chimerax_server')

def open_chimerax(port=None):
    """open chimerax with remote control enabled"""
    global chimerax_process

    log_info("Starting open_chimerax function...")
    
    try:
        current_system = platform.system()
        logger.info(f"Starting open_chimerax function in {current_system} environment")
        log_info(f"OS detected: {current_system}")
        
        # Check if ChimeraX is already running
        logger.info("Checking if ChimeraX is already running")
        is_running = False
        try:
            is_running = is_chimerax_running()
            logger.info(f"ChimeraX running status: {is_running}")
            log_info(f"ChimeraX running status: {is_running}")
        except Exception as e:
            logger.error(f"Error checking if ChimeraX is running: {str(e)}")
            log_error(f"Error checking if ChimeraX is running: {str(e)}")
            
        if is_running:
            # Record session if not already recorded
            logger.info("ChimeraX is already running, updating session info")
            if not chimerax_session.active:
                chimerax_session.start(port)
            return "ChimeraX is already running with remote control enabled"
        
        # If port is specified, update it
        if port:
            from chimerax_core import initialize_server_proxy
            logger.info(f"Custom port specified: {port}, updating server proxy")
            initialize_server_proxy(port)
        
        try:
            # Get the ChimeraX executable path
            chimerax_bin = get_chimerax_executable_path()
            
            # Now launch ChimeraX with the found executable path
            # Use different strategy to prevent the server from crashing
            # after launching ChimeraX
            
            # Common command to enable remote control
            remote_cmd = "remotecontrol xmlrpc true"
            
            if current_system == "Windows":
                # Use a different approach for Windows - start in a detached process
                log_info("Launching ChimeraX on Windows with detached process")
                
                # Using CREATE_NO_WINDOW flag instead of start command for reliability
                try:
                    # Direct command approach with specific flags
                    cmd_args = [
                        chimerax_bin,
                        "--cmd",
                        "remotecontrol xmlrpc true"
                    ]
                    
                    log_info(f"Launching ChimeraX with args: {cmd_args}")
                    
                    # Use CREATE_NO_WINDOW to avoid console window
                    # And DETACHED_PROCESS to detach from parent process
                    process_flags = 0x08000000  # CREATE_NO_WINDOW
                    process_flags |= 0x00000008  # DETACHED_PROCESS
                    
                    subprocess.Popen(
                        cmd_args,
                        creationflags=process_flags,
                        shell=False,
                        close_fds=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    logger.info("ChimeraX process started with direct command approach")
                    log_info("ChimeraX process started with direct command approach")
                except Exception as e:
                    log_error(f"Error launching with direct approach: {str(e)}")
                    
                    # Fall back to alternate method if direct approach fails
                    log_info("Falling back to start command method")
                    
                    # Use the full command with proper quotes
                    start_cmd = f'start "" /b "{chimerax_bin}" --cmd "remotecontrol xmlrpc true"'
                    
                    log_info(f"Fallback command: {start_cmd}")
                    
                    # Launch with shell=True to use the start command
                    subprocess.Popen(
                        start_cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    logger.info("ChimeraX process started with fallback method")
                    log_info("ChimeraX process started with fallback method")
                
            elif current_system == "Darwin":  # macOS
                # For macOS, use open command to detach
                log_info("Launching ChimeraX on macOS with open command")
                
                # Get the app path from the binary path
                # Typical path: /Applications/ChimeraX.app/Contents/bin/ChimeraX
                app_path = os.path.dirname(os.path.dirname(os.path.dirname(chimerax_bin)))
                
                # Use the open command to launch the app
                subprocess.Popen([
                    "open", 
                    app_path, 
                    "--args", 
                    "--cmd", 
                    remote_cmd
                ])
                
                logger.info(f"ChimeraX app opened from {app_path}")
                log_info(f"ChimeraX app opened from {app_path}")
                
            else:  # Linux
                # For Linux, launch in background with nohup
                log_info("Launching ChimeraX on Linux with nohup")
                
                cmd = f'nohup {chimerax_bin} --cmd "{remote_cmd}" > /dev/null 2>&1 &'
                subprocess.Popen(cmd, shell=True)
                
                logger.info("ChimeraX process started in background")
                log_info("ChimeraX process started in background")
            
            # Wait for the port to be available
            logger.info(f"Waiting for XML-RPC port {xmlrpc_port} to become available...")
            log_info(f"Waiting for XML-RPC port {xmlrpc_port} to become available...")
            
            if wait_for_port(xmlrpc_port, timeout=30):
                # Additional verification - wait and try a simple command
                logger.info("Port is open, waiting additional time for server initialization")
                log_info("Port is open, waiting additional time for server initialization")
                time.sleep(5)
                try:
                    logger.info("Testing XML-RPC connection with 'version' command...")
                    log_info("Testing XML-RPC connection with 'version' command...")
                    version_result = s.run_command("version")
                    logger.info(f"Version command result: {version_result}")
                    log_info(f"Version command result: {version_result}")
                    
                    # When ChimeraX starts successfully, record the session
                    chimerax_session.start(port)
                    log_info("ChimeraX session started successfully")
                    
                    return "ChimeraX started with remote control enabled"
                except Exception as e:
                    error_msg = f"Error testing ChimeraX connection: {str(e)}"
                    logger.error(error_msg)
                    log_error(error_msg)
                    return f"ChimeraX started, but not yet responsive. Wait a few seconds before sending commands. Error: {str(e)}"
            else:
                error_msg = f"Port {xmlrpc_port} never became available"
                logger.error(error_msg)
                log_error(error_msg)
                return "ChimeraX started, but the XML-RPC server is not responding. Try again or start ChimeraX manually."
                
        except Exception as e:
            error_msg = f"Error launching ChimeraX: {str(e)}"
            logger.error(error_msg)
            log_error(error_msg)
            log_error(traceback.format_exc())
            return f"Error starting ChimeraX: {str(e)}"
    
    except Exception as e:
        # Capture any uncaught exceptions in the main function
        error_msg = f"Unhandled exception in open_chimerax: {str(e)}"
        logger.error(error_msg)
        log_error(error_msg)
        log_error(traceback.format_exc())
        return f"Critical error in open_chimerax: {str(e)}. See logs for details."

def run_chimerax_command(command, auto_start=False, capture_log=False):
    """Run a ChimeraX command via the XML-RPC interface
    
    Args:
        command: The ChimeraX command to execute
        auto_start: If True, attempt to start ChimeraX if it's not running
        capture_log: If True, capture and return the log output along with the command result
        
    Returns:
        Result of the command execution or error message. If capture_log is True, returns a dict
        with both 'result' and 'log' keys.
    """
    if not command or not isinstance(command, str):
        return "Error: Command must be a non-empty string"
    
    # Check if ChimeraX is running
    if not is_chimerax_running():
        if auto_start:
            logger.info("ChimeraX not running, attempting to start automatically")
            start_result = open_chimerax()
            if "Error" in start_result:
                return f"Failed to auto-start ChimeraX: {start_result}"
            
            # Wait a bit more for ChimeraX to fully initialize
            time.sleep(2)
            
            # Check again if ChimeraX is running
            if not is_chimerax_running():
                return "Error: ChimeraX failed to start properly. Please start it manually with open_chimerax() first."
        else:
            return "Error: ChimeraX is not running. Please start it with open_chimerax() first or set auto_start=True."
    
    try:
        # If capturing logs, clear the log first
        if capture_log:
            # Save current log to avoid losing it completely
            temp_dir = tempfile.gettempdir()
            prev_log_file = os.path.join(temp_dir, "chimerax_prev_log.txt")
            s.run_command(f"log save {prev_log_file}")
            
            # Clear the log to start fresh
            s.run_command("log clear")
        
        # Record the command in our session
        chimerax_session.record_command(command)
        
        # Execute the command
        logger.debug(f"Executing ChimeraX command: {command}")
        result = s.run_command(command)
        
        # If capturing logs, get the log content
        if capture_log:
            # Save the current log to a file
            log_file = os.path.join(temp_dir, "chimerax_cmd_log.txt")
            s.run_command(f"log save {log_file}")
            
            # Read the log file
            log_content = ""
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    log_content = f.read()
                
                # Clean up
                try:
                    os.remove(log_file)
                except:
                    pass
            
            # Restore the previous log
            if os.path.exists(prev_log_file):
                # We can't directly restore, but we can append it
                s.run_command("log clear")
                # Read the previous log
                with open(prev_log_file, "r", encoding="utf-8") as f:
                    prev_log = f.read()
                
                # Create a text file with the previous log
                prev_log_file_temp = os.path.join(temp_dir, "chimerax_prev_log_temp.txt")
                with open(prev_log_file_temp, "w", encoding="utf-8") as f:
                    f.write(prev_log)
                
                # Append it to the current log
                s.run_command(f"log open {prev_log_file_temp}")
                
                # Clean up
                try:
                    os.remove(prev_log_file)
                    os.remove(prev_log_file_temp)
                except:
                    pass
            
            # Return both the result and log
            return {"result": result, "log": log_content}
        
        return result
    except ConnectionError as e:
        logger.error(f"Connection error while executing command: {str(e)}")
        return f"Connection error: {str(e)}. ChimeraX may have closed unexpectedly."
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        return f"Error executing command: {str(e)}"

def get_chimerax_logs(command=None, log_lines=20, auto_start=False):
    """Retrieve logs from ChimeraX command execution
    
    Args:
        command: Optional command to execute and get logs for
        log_lines: Number of log lines to retrieve
        auto_start: Whether to automatically start ChimeraX if not running
        
    Returns:
        Log output from ChimeraX
    """
    if not is_chimerax_running():
        if auto_start:
            open_result = open_chimerax()
            if "Error" in open_result:
                return f"Failed to start ChimeraX: {open_result}"
            time.sleep(2)  # Give ChimeraX time to start
        else:
            return "Error: ChimeraX is not running. Please start it with open_chimerax() first."
    
    try:
        # If a command is provided, execute it first
        if command:
            logger.info(f"Executing command before getting logs: {command}")
            run_chimerax_command(command, auto_start=False)
        
        # Use the ChimeraX 'log' command to get the log content
        # First, try to save the log to a temporary file
        temp_dir = tempfile.gettempdir()
        log_file = os.path.join(temp_dir, "chimerax_log_temp.txt")
        
        # Use the log save command to save the log
        save_result = run_chimerax_command(f"log save {log_file}", auto_start=False)
        
        # Read the log file
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.readlines()
            
            # Get the last N lines
            if log_lines > 0:
                log_content = log_content[-log_lines:]
            
            # Clean up
            try:
                os.remove(log_file)
            except:
                pass
            
            return "".join(log_content)
        else:
            # If saving to file didn't work, try an alternative approach
            # Execute a command that should generate some log output
            if not command:
                test_result = run_chimerax_command("version", auto_start=False)
            
            # Try to use log clear after capturing to get the current log buffer
            # Note: This is more of a hack, as ChimeraX doesn't have a direct XML-RPC method
            # to retrieve the log contents
            return f"Log retrieval via file failed. Command output: {save_result}"
    
    except Exception as e:
        logger.error(f"Error retrieving ChimeraX logs: {str(e)}")
        return f"Error retrieving ChimeraX logs: {str(e)}"

def close_chimerax(save_session_file=None):
    """Close ChimeraX
    
    Args:
        save_session_file: Optional filename to save the session before closing
        
    Returns:
        Result message
    """
    try:
        if is_chimerax_running():
            # Save session if requested
            if save_session_file:
                if not save_session_file.endswith(".cxs"):
                    save_session_file += ".cxs"
                logger.info(f"Saving ChimeraX session to {save_session_file} before closing")
                s.run_command(f"save {save_session_file} format session")
                chimerax_session.session_file = save_session_file
            
            # Close ChimeraX
            s.run_command("exit")
        
        # Update session state
        if chimerax_session.active:
            chimerax_session.stop()
        
        return "ChimeraX closed" + (f" and session saved to {save_session_file}" if save_session_file else "")
    except Exception as e:
        logger.error(f"Error closing ChimeraX: {str(e)}")
        return f"Error closing ChimeraX: {str(e)}"

def fetch_structure(pdb_id, format=None, auto_display=True, 
                  auto_start=True, capture_log=False):
    """Fetch a structure from the Protein Data Bank
    
    Args:
        pdb_id: The PDB ID to fetch (e.g., '1hwi')
        format: Optional file format (e.g., 'pdb', 'mmcif')
        auto_display: Whether to automatically display the structure
        auto_start: Whether to automatically start ChimeraX if not running
        capture_log: Whether to capture and return the log output
        
    Returns:
        Result message or dictionary with result and log if capture_log is True
    """
    if not pdb_id or not isinstance(pdb_id, str):
        return "Error: PDB ID must be a non-empty string"
    
    # Build the command
    command = f"open {pdb_id}"
    if format:
        command += f" format {format}"
    
    # Run the command
    result = run_chimerax_command(command, auto_start=auto_start, capture_log=capture_log)
    
    # Apply display settings if requested
    if auto_display and (not capture_log or "Error" not in str(result)):
        display_command = "view"
        display_result = run_chimerax_command(display_command, auto_start=False, 
                                           capture_log=capture_log)
        
        if capture_log:
            # Combine the logs from both commands
            combined_result = {
                "result": f"Fetched structure {pdb_id}. {result['result']}",
                "log": result["log"] + "\n" + display_result["log"]
            }
            return combined_result
        else:
            return f"Fetched structure {pdb_id}. {result}"
    
    if capture_log:
        result["result"] = f"Fetched structure {pdb_id}. {result['result']}"
    
    return result

def save_session(filename, auto_start=False):
    """Save the current ChimeraX session to a file
    
    Args:
        filename: Name of the file to save (should end with .cxs)
        auto_start: Whether to automatically start ChimeraX if not running
        
    Returns:
        Result message
    """
    if not filename.endswith('.cxs'):
        filename += '.cxs'
    
    command = f"save {filename} format session"
    return run_chimerax_command(command, auto_start=auto_start)

def set_visualization(representation="cartoon", color_scheme=None, 
                     target="protein", auto_start=False):
    """Set visualization parameters for the displayed molecules
    
    Args:
        representation: Molecular representation (cartoon, stick, sphere, ribbon, etc.)
        color_scheme: Color scheme to apply (e.g., 'rainbow', 'bfactor', or color name)
        target: Target specification for the molecules to modify
        auto_start: Whether to automatically start ChimeraX if not running
        
    Returns:
        Result message
    """
    commands = []
    
    # Set representation
    if representation:
        commands.append(f"style {target} {representation}")
    
    # Set coloring
    if color_scheme:
        if color_scheme.lower() == "rainbow":
            commands.append(f"rainbow {target}")
        else:
            commands.append(f"color {target} {color_scheme}")
    
    # Execute commands
    results = []
    for cmd in commands:
        result = run_chimerax_command(cmd, auto_start=auto_start)
        results.append(result)
    
    return "; ".join(results) if results else "No visualization changes applied"

def measure_distance(atom1, atom2, auto_start=False):
    """Measure the distance between two atoms
    
    Args:
        atom1: Specification for the first atom
        atom2: Specification for the second atom
        auto_start: Whether to automatically start ChimeraX if not running
        
    Returns:
        Distance measurement result
    """
    command = f"distance {atom1} {atom2}"
    return run_chimerax_command(command, auto_start=auto_start)

def get_session_status():
    """Get the current ChimeraX session status
    
    Returns:
        Dictionary with session information
    """
    # First check if ChimeraX is running
    is_running = is_chimerax_running()
    
    # If it's running but we don't have it recorded, record it
    if is_running and not chimerax_session.active:
        chimerax_session.start(xmlrpc_port)
    
    # If it's not running but we have it recorded as active, update it
    if not is_running and chimerax_session.active:
        chimerax_session.stop()
    
    # Return session info
    return chimerax_session.get_session_info()

def run_script(script_file, auto_start=False):
    """Run a ChimeraX script file (.cxc)
    
    Args:
        script_file: Path to the ChimeraX script file
        auto_start: Whether to automatically start ChimeraX if not running
        
    Returns:
        Result of script execution
    """
    if not script_file.endswith('.cxc'):
        return "Error: Script file must have .cxc extension"
    
    if not os.path.exists(script_file):
        return f"Error: Script file '{script_file}' not found"
    
    command = f"open {script_file}"
    result = run_chimerax_command(command, auto_start=auto_start)
    
    return result

def analyze_protein_ligand(protein_spec="protein", ligand_spec=None, 
                         h_bond_cutoff=3.5, contact_cutoff=4.0,
                         auto_start=False, capture_log=False):
    """Analyze interactions between a protein and ligand
    
    Args:
        protein_spec: Specification for the protein part
        ligand_spec: Specification for the ligand part
        h_bond_cutoff: Distance cutoff for hydrogen bonds (Å)
        contact_cutoff: Distance cutoff for contacts (Å)
        auto_start: Whether to automatically start ChimeraX if not running
        capture_log: Whether to capture and return the log output
        
    Returns:
        Dictionary with analysis results and optional logs
    """
    if not ligand_spec:
        return "Error: Ligand specification required"
    
    # Prepare results dictionary
    results = {}
    all_logs = ""
    
    # First make sure the protein and ligand are properly shown
    try:
        # Setup commands
        setup_commands = [
            f"show {protein_spec}",
            f"show {ligand_spec}",
            f"style {ligand_spec} stick"
        ]
        
        # Execute setup commands
        for cmd in setup_commands:
            cmd_result = run_chimerax_command(cmd, auto_start=auto_start, capture_log=capture_log)
            if capture_log:
                all_logs += cmd_result["log"] + "\n"
        
        # Find hydrogen bonds
        h_bonds_cmd = f"hbonds {protein_spec} restrict {ligand_spec} reveal true log true distance {h_bond_cutoff}"
        h_bonds_result = run_chimerax_command(h_bonds_cmd, auto_start=False, capture_log=capture_log)
        
        if capture_log:
            results["hydrogen_bonds"] = h_bonds_result["result"]
            all_logs += h_bonds_result["log"] + "\n"
        else:
            results["hydrogen_bonds"] = h_bonds_result
        
        # Find contacts
        contacts_cmd = f"contacts {protein_spec} restrict {ligand_spec} distance {contact_cutoff} reveal true log true"
        contacts_result = run_chimerax_command(contacts_cmd, auto_start=False, capture_log=capture_log)
        
        if capture_log:
            results["contacts"] = contacts_result["result"]
            all_logs += contacts_result["log"] + "\n"
        else:
            results["contacts"] = contacts_result
        
        # Highlight interacting residues
        highlight_cmd = f"select {protein_spec} & within {contact_cutoff} of {ligand_spec}"
        highlight_result = run_chimerax_command(highlight_cmd, auto_start=False, capture_log=capture_log)
        
        if capture_log:
            results["selection"] = highlight_result["result"]
            all_logs += highlight_result["log"] + "\n"
        
        # Style the selected residues
        style_cmd = "style sel stick"
        style_result = run_chimerax_command(style_cmd, auto_start=False, capture_log=capture_log)
        
        if capture_log:
            all_logs += style_result["log"] + "\n"
        
        # Record the analysis in the session
        chimerax_session.add_model({
            "protein": protein_spec,
            "ligand": ligand_spec,
            "analysis": "protein-ligand interaction"
        })
        
        # Add the logs if requested
        if capture_log:
            results["logs"] = all_logs
        
        return results
    
    except Exception as e:
        logger.error(f"Error analyzing protein-ligand interaction: {str(e)}")
        error_msg = f"Error analyzing protein-ligand interaction: {str(e)}"
        
        if capture_log:
            return {"error": error_msg, "logs": all_logs}
        else:
            return error_msg

def test_log_capture():
    """Test function to demonstrate log capture
    
    Returns:
        Captured log content
    """
    if not is_chimerax_running():
        open_chimerax()
        time.sleep(2)  # Give ChimeraX time to start
    
    # Clear the log first
    run_chimerax_command("log clear")
    
    # Run a sequence of commands that will generate log output
    commands = [
        "version",  # Show ChimeraX version
        "open 1zik",  # Open a PDB file
        "show protein",  # Show protein
        "style protein cartoon",  # Set style
        "color protein blue"  # Color protein
    ]
    
    for cmd in commands:
        run_chimerax_command(cmd)
        time.sleep(0.5)  # Small delay between commands
    
    # Get the logs
    return get_chimerax_logs()

def run_command_with_logs(command, auto_start=False):
    """Run a ChimeraX command and return both the result and logs
    
    Args:
        command: The ChimeraX command to execute
        auto_start: If True, attempt to start ChimeraX if it's not running
        
    Returns:
        Dictionary containing both command result and log output
    """
    return run_chimerax_command(command, auto_start=auto_start, capture_log=True)

def demo_command_logs():
    """Demonstrate running commands with log capture
    
    Returns:
        Example of captured logs from several commands
    """
    # Make sure ChimeraX is running
    if not is_chimerax_running():
        open_chimerax()
        time.sleep(2)  # Give ChimeraX time to start
    
    # Simple command first
    version_result = run_command_with_logs("version")
    print("Version command result:", version_result)
    
    # More complex example - open a structure and analyze it
    results = []
    
    # Open a structure
    open_result = run_command_with_logs("open 1hwi")
    results.append({"command": "open 1hwi", "output": open_result})
    
    # Show the protein
    show_result = run_command_with_logs("show protein")
    results.append({"command": "show protein", "output": show_result})
    
    # Color by element
    color_result = run_command_with_logs("color byatom")
    results.append({"command": "color byatom", "output": color_result})
    
    # Find hydrogen bonds
    hbonds_result = run_command_with_logs("hbonds protein reveal true log true")
    results.append({"command": "hbonds protein", "output": hbonds_result})
    
    return results 