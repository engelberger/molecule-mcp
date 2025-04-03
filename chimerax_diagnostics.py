# chimerax_diagnostics.py
import os
import sys
import glob
import platform
import socket
import subprocess
import logging
import traceback
import winreg

from chimerax_server import log_info, log_error
from chimerax_core import xmlrpc_port, is_chimerax_running, get_chimerax_executable_path

# Configure logging
logger = logging.getLogger('chimerax_server')

def diagnose_chimerax():
    """Run diagnostics for ChimeraX connection issues"""
    try:
        log_info("Starting ChimeraX diagnostics...")
        
        report = ["=== ChimeraX Diagnostic Report ==="]
        
        # Check OS
        current_system = platform.system()
        os_version = platform.version()
        report.append(f"Operating System: {current_system} ({os_version})")
        
        # Check Python
        python_version = sys.version.split('\n')[0]
        report.append(f"Python Version: {python_version}")
        
        # Check ChimeraX running status
        try:
            running = is_chimerax_running()
            report.append(f"ChimeraX Running: {running}")
        except Exception as e:
            report.append(f"Error checking ChimeraX running status: {str(e)}")
        
        # Check XML-RPC port
        try:
            port_check = False
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', xmlrpc_port))
            sock.close()
            
            if result == 0:
                port_check = True
                report.append(f"XML-RPC Port {xmlrpc_port}: OPEN")
            else:
                report.append(f"XML-RPC Port {xmlrpc_port}: CLOSED")
        except Exception as e:
            report.append(f"Error checking XML-RPC port: {str(e)}")
        
        # Get ChimeraX executable path
        try:
            chimerax_path = get_chimerax_executable_path()
            report.append(f"ChimeraX Executable Path: {chimerax_path}")
            
            # Check if the file exists
            if os.path.exists(chimerax_path):
                report.append(f"ChimeraX Executable Exists: Yes")
            else:
                report.append(f"ChimeraX Executable Exists: No")
        except Exception as e:
            report.append(f"Error getting ChimeraX executable path: {str(e)}")
        
        # Platform-specific checks
        if current_system == "Windows":
            report.append("\n=== Windows-Specific Checks ===")
            # Check common Windows install locations
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
            
            # Common locations to check
            locations = [
                f"{program_files}\\ChimeraX*\\bin\\ChimeraX.exe",
                f"{program_files_x86}\\ChimeraX*\\bin\\ChimeraX.exe",
                f"{program_files}\\UCSF ChimeraX\\bin\\ChimeraX.exe",
                f"{program_files_x86}\\UCSF ChimeraX\\bin\\ChimeraX.exe"
            ]
            
            found_locations = []
            for pattern in locations:
                found = glob.glob(pattern)
                if found:
                    found_locations.extend(found)
            
            if found_locations:
                report.append("Found ChimeraX in these locations:")
                for loc in found_locations:
                    report.append(f"  - {loc}")
            else:
                report.append("No ChimeraX installations found in standard locations")
            
            # Check registry
            try:
                registry_paths = check_windows_registry()
                if registry_paths:
                    report.append("\nRegistry entries for ChimeraX:")
                    for key, path in registry_paths.items():
                        report.append(f"  - {key}: {path}")
                else:
                    report.append("No ChimeraX registry entries found")
            except Exception as e:
                report.append(f"Error checking registry: {str(e)}")
                
        elif current_system == "Darwin":  # macOS
            report.append("\n=== macOS-Specific Checks ===")
            # Check Applications folder
            app_paths = glob.glob("/Applications/ChimeraX*.app")
            alt_paths = glob.glob("/Applications/UCSF ChimeraX.app")
            found_apps = app_paths + alt_paths
            
            if found_apps:
                report.append("Found ChimeraX applications:")
                for app in found_apps:
                    report.append(f"  - {app}")
                    
                    # Check for the executable inside the .app bundle
                    bin_path = os.path.join(app, "Contents/bin/ChimeraX")
                    if os.path.exists(bin_path):
                        report.append(f"    Executable found: {bin_path}")
                    else:
                        report.append(f"    Executable NOT found at: {bin_path}")
            else:
                report.append("No ChimeraX applications found in /Applications")
                
            # Check user Applications folder
            home_dir = os.path.expanduser("~")
            user_app_paths = glob.glob(f"{home_dir}/Applications/ChimeraX*.app")
            user_alt_paths = glob.glob(f"{home_dir}/Applications/UCSF ChimeraX.app")
            user_found_apps = user_app_paths + user_alt_paths
            
            if user_found_apps:
                report.append("\nFound ChimeraX in user Applications folder:")
                for app in user_found_apps:
                    report.append(f"  - {app}")
                    
                    # Check for the executable inside the .app bundle
                    bin_path = os.path.join(app, "Contents/bin/ChimeraX")
                    if os.path.exists(bin_path):
                        report.append(f"    Executable found: {bin_path}")
                    else:
                        report.append(f"    Executable NOT found at: {bin_path}")
        
        else:  # Linux
            report.append("\n=== Linux-Specific Checks ===")
            # Check common Linux install locations
            locations = [
                "/opt/UCSF/ChimeraX*/bin/ChimeraX",
                "/usr/local/bin/ChimeraX",
                "/usr/bin/ChimeraX",
                os.path.expanduser("~/UCSF-ChimeraX*/bin/ChimeraX")
            ]
            
            found_locations = []
            for pattern in locations:
                found = glob.glob(pattern)
                if found:
                    found_locations.extend(found)
            
            if found_locations:
                report.append("Found ChimeraX in these locations:")
                for loc in found_locations:
                    report.append(f"  - {loc}")
            else:
                report.append("No ChimeraX installations found in standard locations")
            
            # Try which command
            try:
                which_output = subprocess.check_output(["which", "ChimeraX"], 
                                                     stderr=subprocess.STDOUT, 
                                                     universal_newlines=True)
                report.append(f"\n'which ChimeraX' result: {which_output.strip()}")
            except subprocess.CalledProcessError:
                report.append("\n'which ChimeraX' did not find ChimeraX in PATH")
        
        # Check ChimeraX process if running
        if running:
            report.append("\n=== ChimeraX Process Check ===")
            
            # Try connecting to the running instance
            try:
                import xmlrpc.client
                proxy = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{xmlrpc_port}")
                version = proxy.run_command("version")
                report.append(f"Connected to ChimeraX XML-RPC server")
                report.append(f"ChimeraX version: {version}")
            except Exception as e:
                report.append(f"Failed to connect to running ChimeraX: {str(e)}")
        
        # Join all report items with newlines
        diagnostic_report = "\n".join(report)
        log_info(diagnostic_report)
        
        return diagnostic_report
        
    except Exception as e:
        error_msg = f"Error running diagnostics: {str(e)}"
        log_error(error_msg)
        log_error(traceback.format_exc())
        return error_msg

def debug_mac_path_issue():
    """Debug specifically the macOS path issue causing index errors"""
    
    # Only run on macOS
    if platform.system() != "Darwin":
        return "This debug function is only for macOS"
    
    report = ["=== macOS ChimeraX Path Debug Report ==="]
    report.append(f"Current platform: {platform.system()} {platform.mac_ver()[0]}")
    
    try:
        # Test various glob patterns that might be used to locate ChimeraX
        patterns = [
            "/Applications/ChimeraX-*.app/Contents/bin/ChimeraX",
            "/Applications/ChimeraX*.app/Contents/bin/ChimeraX",
            "/Applications/UCSF ChimeraX.app/Contents/bin/ChimeraX"
        ]
        
        report.append("\nTesting glob patterns:")
        for pattern in patterns:
            try:
                matches = glob.glob(pattern)
                report.append(f"  Pattern: {pattern}")
                if matches:
                    report.append(f"    Found {len(matches)} matches:")
                    for match in matches:
                        report.append(f"    - {match}")
                        # Check if it's executable
                        if os.access(match, os.X_OK):
                            report.append(f"      File is executable")
                        else:
                            report.append(f"      File is NOT executable")
                else:
                    report.append(f"    No matches found")
            except Exception as e:
                report.append(f"    Error with pattern {pattern}: {str(e)}")
        
        # List applications in /Applications to see what's available
        report.append("\nListing applications in /Applications:")
        try:
            entries = os.listdir("/Applications")
            chimerax_apps = [app for app in entries if "himerax" in app]  # Case insensitive match
            
            if chimerax_apps:
                report.append(f"  Found {len(chimerax_apps)} ChimeraX-related applications:")
                for app in chimerax_apps:
                    app_path = f"/Applications/{app}"
                    report.append(f"  - {app_path}")
                    
                    # Check for the bin directory in each found app
                    bin_dir = f"{app_path}/Contents/bin"
                    if os.path.isdir(bin_dir):
                        bin_files = os.listdir(bin_dir)
                        report.append(f"    Contents/bin directory contains:")
                        for file in bin_files:
                            if file == "ChimeraX":
                                report.append(f"    - {file} (EXECUTABLE FOUND)")
                            else:
                                report.append(f"    - {file}")
                    else:
                        report.append(f"    Contents/bin directory not found")
            else:
                report.append("  No ChimeraX applications found")
                
            # List everything in /Applications for more context
            report.append("\nAll entries in /Applications (may help identify naming):")
            for entry in sorted(entries):
                report.append(f"  - {entry}")
                
        except Exception as e:
            report.append(f"  Error listing /Applications: {str(e)}")
        
        # Attempt to simulate the code that would cause the index error
        report.append("\nSimulating problematic code execution:")
        try:
            # This is typically what causes the index error - glob returns empty list
            test_pattern = "/Applications/ChimeraX-*.app/Contents/bin/ChimeraX"
            test_matches = glob.glob(test_pattern)
            report.append(f"  Test pattern: {test_pattern}")
            report.append(f"  Matches found: {len(test_matches)}")
            
            if test_matches:
                # No error would occur since we found matches
                report.append(f"  First match: {test_matches[0]}")
            else:
                # This would cause an index error if we tried to access [0]
                report.append("  No matches found - this would cause 'list index out of range' if code tries to access index 0")
                
                # Check alternate patterns that might work
                alt_pattern = "/Applications/UCSF ChimeraX.app/Contents/bin/ChimeraX"
                alt_matches = glob.glob(alt_pattern)
                if alt_matches:
                    report.append(f"  However, alternate pattern '{alt_pattern}' found matches:")
                    report.append(f"  First alternate match: {alt_matches[0]}")
        except Exception as e:
            report.append(f"  Error in simulation: {str(e)}")
        
        # Detailed diagnostic output
        diagnostic_report = "\n".join(report)
        log_info(diagnostic_report)
        
        return diagnostic_report
        
    except Exception as e:
        error_msg = f"Error debugging macOS path issue: {str(e)}"
        log_error(error_msg)
        log_error(traceback.format_exc())
        return error_msg

def debug_windows_path_issue():
    """Debug specifically the Windows path issue causing errors"""
    
    # Only run on Windows
    if platform.system() != "Windows":
        return "This debug function is only for Windows"
    
    report = ["=== Windows ChimeraX Path Debug Report ==="]
    report.append(f"Current platform: {platform.system()} {platform.version()}")
    
    try:
        # Get Program Files locations
        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
        
        report.append(f"\nProgram Files directory: {program_files}")
        report.append(f"Program Files (x86) directory: {program_files_x86}")
        
        # 1. Check direct paths first (no globbing)
        direct_paths = [
            "C:\\Program Files\\ChimeraX 1.9\\bin\\ChimeraX.exe",
            "C:\\Program Files\\ChimeraX\\bin\\ChimeraX.exe",
            "C:\\Program Files\\UCSF ChimeraX\\bin\\ChimeraX.exe",
            f"{program_files}\\ChimeraX 1.9\\bin\\ChimeraX.exe",
            f"{program_files}\\ChimeraX\\bin\\ChimeraX.exe",
            f"{program_files}\\UCSF ChimeraX\\bin\\ChimeraX.exe",
            f"{program_files_x86}\\ChimeraX 1.9\\bin\\ChimeraX.exe",
            f"{program_files_x86}\\ChimeraX\\bin\\ChimeraX.exe",
            f"{program_files_x86}\\UCSF ChimeraX\\bin\\ChimeraX.exe"
        ]
        
        report.append("\nChecking specific paths:")
        for path in direct_paths:
            if os.path.exists(path):
                report.append(f"  FOUND: {path}")
            else:
                report.append(f"  Not found: {path}")
        
        # 2. Test glob patterns that might cause issues
        patterns = [
            "C:\\Program Files\\ChimeraX*\\bin\\ChimeraX.exe",
            "C:\\Program Files(x86)\\ChimeraX*\\bin\\ChimeraX.exe",
            f"{program_files}\\ChimeraX*\\bin\\ChimeraX.exe",
            f"{program_files_x86}\\ChimeraX*\\bin\\ChimeraX.exe",
            f"{program_files}\\UCSF ChimeraX*\\bin\\ChimeraX.exe",
            f"{program_files_x86}\\UCSF ChimeraX*\\bin\\ChimeraX.exe"
        ]
        
        report.append("\nTesting glob patterns:")
        for pattern in patterns:
            try:
                matches = glob.glob(pattern)
                report.append(f"  Pattern: {pattern}")
                if matches:
                    report.append(f"    Found {len(matches)} matches:")
                    for match in matches:
                        report.append(f"    - {match}")
                else:
                    report.append(f"    No matches found")
            except Exception as e:
                report.append(f"    Error with pattern {pattern}: {str(e)}")
        
        # 3. List Program Files to see what's available
        try:
            report.append(f"\nListing contents of {program_files}:")
            entries = os.listdir(program_files)
            chimerax_dirs = [d for d in entries if "himerax" in d.lower()]
            
            if chimerax_dirs:
                report.append(f"  Found {len(chimerax_dirs)} ChimeraX-related directories:")
                for d in chimerax_dirs:
                    dir_path = os.path.join(program_files, d)
                    report.append(f"  - {dir_path}")
                    
                    # Check for bin directory
                    bin_dir = os.path.join(dir_path, "bin")
                    if os.path.isdir(bin_dir):
                        bin_files = os.listdir(bin_dir)
                        report.append(f"    bin directory contains:")
                        if "ChimeraX.exe" in bin_files:
                            report.append(f"    - ChimeraX.exe (EXECUTABLE FOUND)")
                        else:
                            report.append(f"    - ChimeraX.exe not found in bin directory")
                    else:
                        report.append(f"    bin directory not found")
            else:
                report.append("  No ChimeraX directories found")
        except Exception as e:
            report.append(f"  Error listing {program_files}: {str(e)}")
            
        # Also try Program Files (x86) if it's different
        if program_files_x86 != program_files:
            try:
                report.append(f"\nListing contents of {program_files_x86}:")
                entries = os.listdir(program_files_x86)
                chimerax_dirs = [d for d in entries if "himerax" in d.lower()]
                
                if chimerax_dirs:
                    report.append(f"  Found {len(chimerax_dirs)} ChimeraX-related directories:")
                    for d in chimerax_dirs:
                        dir_path = os.path.join(program_files_x86, d)
                        report.append(f"  - {dir_path}")
                        
                        # Check for bin directory
                        bin_dir = os.path.join(dir_path, "bin")
                        if os.path.isdir(bin_dir):
                            bin_files = os.listdir(bin_dir)
                            report.append(f"    bin directory contains:")
                            if "ChimeraX.exe" in bin_files:
                                report.append(f"    - ChimeraX.exe (EXECUTABLE FOUND)")
                            else:
                                report.append(f"    - ChimeraX.exe not found in bin directory")
                        else:
                            report.append(f"    bin directory not found")
                else:
                    report.append("  No ChimeraX directories found")
            except Exception as e:
                report.append(f"  Error listing {program_files_x86}: {str(e)}")
        
        # 4. Check Windows Registry
        report.append("\nChecking Windows Registry for ChimeraX:")
        try:
            registry_results = check_windows_registry()
            if registry_results:
                for key, value in registry_results.items():
                    report.append(f"  Found registry entry: {key} = {value}")
                    
                    # Check if the path exists
                    if os.path.exists(value):
                        report.append(f"  Path exists: {value}")
                    else:
                        report.append(f"  Path does NOT exist: {value}")
            else:
                report.append("  No ChimeraX registry entries found")
        except Exception as e:
            report.append(f"  Error checking registry: {str(e)}")
        
        # 5. Simulate the problematic code
        report.append("\nSimulating problematic code execution:")
        try:
            # This is typically what causes the index error - glob returns empty list
            test_pattern = f"{program_files}\\ChimeraX*\\bin\\ChimeraX.exe"
            test_matches = glob.glob(test_pattern)
            report.append(f"  Test pattern: {test_pattern}")
            report.append(f"  Matches found: {len(test_matches)}")
            
            if test_matches:
                # No error would occur since we found matches
                report.append(f"  First match: {test_matches[0]}")
            else:
                # This would cause an index error if we tried to access [0]
                report.append("  No matches found - this would cause 'list index out of range' if code tries to access index 0")
                
                # Check alternate patterns that might work
                alt_pattern = f"{program_files}\\UCSF ChimeraX\\bin\\ChimeraX.exe"
                if os.path.exists(alt_pattern):
                    report.append(f"  However, direct path '{alt_pattern}' exists and could be used")
        except Exception as e:
            report.append(f"  Error in simulation: {str(e)}")
        
        # Detailed diagnostic output
        diagnostic_report = "\n".join(report)
        log_info(diagnostic_report)
        
        return diagnostic_report
        
    except Exception as e:
        error_msg = f"Error debugging Windows path issue: {str(e)}"
        log_error(error_msg)
        log_error(traceback.format_exc())
        return error_msg

def check_windows_registry():
    """Check Windows registry for ChimeraX installation paths"""
    if platform.system() != "Windows":
        return {}
    
    registry_paths = {}
    
    # Common registry locations to check
    registry_locations = [
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\UCSF\\ChimeraX"),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Wow6432Node\\UCSF\\ChimeraX"),
        (winreg.HKEY_CURRENT_USER, "SOFTWARE\\UCSF\\ChimeraX")
    ]
    
    for hkey, key_path in registry_locations:
        try:
            with winreg.OpenKey(hkey, key_path) as key:
                try:
                    # Try to get the installation path
                    value, _ = winreg.QueryValueEx(key, "InstallPath")
                    registry_paths[f"{key_path}\\InstallPath"] = value
                except FileNotFoundError:
                    pass
                
                try:
                    # Sometimes it might be in a subkey
                    with winreg.OpenKey(key, "InstallPath") as subkey:
                        value, _ = winreg.QueryValueEx(subkey, "")
                        registry_paths[f"{key_path}\\InstallPath"] = value
                except FileNotFoundError:
                    pass
                
                # Also check for version-specific subkeys
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if "." in subkey_name:  # Likely a version number
                            version_key_path = f"{key_path}\\{subkey_name}"
                            try:
                                with winreg.OpenKey(hkey, version_key_path) as version_key:
                                    try:
                                        value, _ = winreg.QueryValueEx(version_key, "InstallPath")
                                        registry_paths[f"{version_key_path}\\InstallPath"] = value
                                    except FileNotFoundError:
                                        pass
                            except Exception:
                                pass
                        i += 1
                    except WindowsError:
                        break
        except FileNotFoundError:
            # Key doesn't exist, continue to next location
            pass
        except Exception as e:
            logger.error(f"Error accessing registry key {key_path}: {str(e)}")
    
    return registry_paths 