# chimerax_imaging.py
import os
import io
import time
import tempfile
import base64
import logging
import traceback
from pathlib import Path
from datetime import datetime
from PIL import Image

from chimerax_server import log_info, log_error
from chimerax_core import s, is_chimerax_running
from chimerax_tools import open_chimerax, run_chimerax_command

# Configure logging
logger = logging.getLogger('chimerax_server')

def capture_chimerax_image(width=800, height=600, filename=None, return_image=True):
    """Capture the current view in ChimeraX
    
    Args:
        width: Image width in pixels
        height: Image height in pixels  
        filename: Optional path to save the image
        return_image: Whether to return the image as an MCP Image
        
    Returns:
        MCP Image object or path to saved image if return_image is False
    """
    from mcp import Image as MCPImage
    
    logger.info(f"Capturing ChimeraX image ({width}x{height})")
    log_info(f"Capturing ChimeraX image ({width}x{height})")
    
    try:
        # Check if ChimeraX is running
        if not is_chimerax_running():
            error_msg = "Cannot capture image: ChimeraX is not running"
            logger.error(error_msg)
            log_error(error_msg)
            return error_msg
        
        # Generate temp filename if no filename is provided
        if not filename:
            # Use timestamp to create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = tempfile.gettempdir()
            temp_filename = f"chimerax_capture_{timestamp}.png"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            logger.info(f"No filename provided, using temporary file: {temp_path}")
            original_filename = temp_path
        else:
            # Ensure filename has proper extension
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filename += '.png'
            
            # Convert path to use proper separators for the current OS
            filename = os.path.normpath(filename)
            original_filename = filename
            
            logger.info(f"Using provided filename: {filename}")
        
        # Normalize path for ChimeraX command
        # ChimeraX expects forward slashes, even on Windows
        chimerax_path = original_filename.replace('\\', '/')
        
        # Capture the image using ChimeraX command
        command = f"save {chimerax_path} width {width} height {height} supersample 3"
        log_info(f"Running command: {command}")
        
        # Execute the save command
        result = run_chimerax_command(command)
        logger.info(f"Image capture command result: {result}")
        
        # Verify the file was created
        if not os.path.exists(original_filename):
            error_msg = f"Failed to save image at {original_filename}"
            logger.error(error_msg)
            log_error(error_msg)
            return error_msg
        
        # If client doesn't want the image, just return the path
        if not return_image:
            return original_filename
        
        # Read the file into bytes
        try:
            with open(original_filename, 'rb') as f:
                image_bytes = f.read()
            
            # Create an MCP Image object
            mcp_image = MCPImage(
                content=image_bytes,
                mime_type="image/png" if original_filename.lower().endswith('.png') else "image/jpeg"
            )
            
            logger.info(f"Successfully created MCP Image object from {original_filename}")
            
            # Return the MCP Image
            return mcp_image
            
        except Exception as e:
            error_msg = f"Error creating MCP Image from file: {str(e)}"
            logger.error(error_msg)
            log_error(error_msg)
            log_error(traceback.format_exc())
            return error_msg
            
    except Exception as e:
        # Log any errors that occur
        error_msg = f"Error capturing ChimeraX image: {str(e)}"
        logger.error(error_msg)
        log_error(error_msg)
        log_error(traceback.format_exc())
        return error_msg

def view_saved_image(filename):
    """View a previously saved image
    
    Args:
        filename: Path to the image file
        
    Returns:
        MCP Image object
    """
    from mcp import Image as MCPImage
    
    logger.info(f"Viewing saved image: {filename}")
    log_info(f"Viewing saved image: {filename}")
    
    try:
        # Normalize path
        filename = os.path.normpath(filename)
        
        # Check if file exists
        if not os.path.exists(filename):
            error_msg = f"Image file not found: {filename}"
            logger.error(error_msg)
            log_error(error_msg)
            return error_msg
        
        # Check file extension
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            error_msg = f"Unsupported image format: {filename}"
            logger.error(error_msg)
            log_error(error_msg)
            return error_msg
        
        # Read the file into bytes
        try:
            with open(filename, 'rb') as f:
                image_bytes = f.read()
            
            # Determine mime type based on file extension
            if filename.lower().endswith('.png'):
                mime_type = "image/png"
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                mime_type = "image/jpeg"
            elif filename.lower().endswith('.gif'):
                mime_type = "image/gif"
            else:
                mime_type = "application/octet-stream"
            
            # Create an MCP Image object
            mcp_image = MCPImage(
                content=image_bytes,
                mime_type=mime_type
            )
            
            logger.info(f"Successfully created MCP Image object from {filename}")
            
            # Return the MCP Image
            return mcp_image
            
        except Exception as e:
            error_msg = f"Error creating MCP Image from file: {str(e)}"
            logger.error(error_msg)
            log_error(error_msg)
            log_error(traceback.format_exc())
            return error_msg
            
    except Exception as e:
        # Log any errors that occur
        error_msg = f"Error viewing saved image: {str(e)}"
        logger.error(error_msg)
        log_error(error_msg)
        log_error(traceback.format_exc())
        return error_msg

def create_molecular_image(commands=None, preset=None, width=800, height=600, 
                         filename=None, return_image=True, auto_start=True):
    """Create and display an image of the current molecule with optional commands applied
    
    Args:
        commands: Optional list of ChimeraX commands to run before capturing the image
        preset: Optional visualization preset to apply ('protein', 'nucleic', 'hydrophobicity', etc.)
        width: Image width in pixels
        height: Image height in pixels
        filename: Optional filename to save the image
        return_image: Whether to return the image as an MCP Image
        auto_start: Whether to automatically start ChimeraX if not running
        
    Returns:
        MCP Image object or path to saved image if return_image is False
    """
    logger.info(f"Creating molecular image with preset: {preset}")
    log_info(f"Creating molecular image with preset: {preset}")
    
    try:
        # Check if ChimeraX is running
        if not is_chimerax_running():
            if not auto_start:
                error_msg = "Cannot create image: ChimeraX is not running"
                logger.error(error_msg)
                log_error(error_msg)
                return error_msg
            
            # Try to start ChimeraX
            logger.info("ChimeraX not running, attempting to start")
            start_result = open_chimerax()
            if "Error" in start_result:
                error_msg = f"Failed to start ChimeraX: {start_result}"
                logger.error(error_msg)
                log_error(error_msg)
                return error_msg
            
            # Wait for ChimeraX to initialize
            time.sleep(5)
        
        # Apply preset if specified
        if preset:
            preset_cmd = f"preset {preset}"
            logger.info(f"Applying preset: {preset_cmd}")
            preset_result = run_chimerax_command(preset_cmd)
            logger.info(f"Preset result: {preset_result}")
        
        # Run any additional commands
        if commands:
            if isinstance(commands, str):
                commands = [commands]
            
            for cmd in commands:
                logger.info(f"Running command: {cmd}")
                cmd_result = run_chimerax_command(cmd)
                logger.info(f"Command result: {cmd_result}")
        
        # Capture the image
        return capture_chimerax_image(width, height, filename, return_image)
        
    except Exception as e:
        # Log any errors that occur
        error_msg = f"Error creating molecular image: {str(e)}"
        logger.error(error_msg)
        log_error(error_msg)
        log_error(traceback.format_exc())
        return error_msg 