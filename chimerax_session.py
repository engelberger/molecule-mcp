# chimerax_session.py
import os
import time
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger('chimerax_server')

class ChimeraXSession:
    """Class to manage ChimeraX session information"""
    
    def __init__(self):
        self.active = False
        self.start_time = None
        self.port = None
        self.models = []
        self.commands = []
        self.session_file = None
        self.last_activity = None
        self.metadata = {}
    
    def start(self, port=None):
        """Record the start of a ChimeraX session"""
        self.active = True
        self.start_time = datetime.now()
        self.port = port
        self.last_activity = self.start_time
        logger.info(f"ChimeraX session started at {self.start_time}")
        
        # Add system information to metadata
        import platform
        self.metadata = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "start_time": self.start_time.isoformat()
        }
        
        return self
    
    def stop(self):
        """Record the end of a ChimeraX session"""
        if self.active:
            end_time = datetime.now()
            duration = end_time - self.start_time
            logger.info(f"ChimeraX session stopped after {duration}")
            
            self.metadata["end_time"] = end_time.isoformat()
            self.metadata["duration_seconds"] = duration.total_seconds()
            
            # Reset session state
            self.active = False
            self.start_time = None
            self.port = None
            
            # Keep models and commands history for reference
            # but mark session as inactive
    
    def add_model(self, model_info: Dict[str, Any]):
        """Record information about a model added to the session"""
        if not self.active:
            logger.warning("Cannot add model - no active ChimeraX session")
            return
        
        timestamp = datetime.now()
        self.last_activity = timestamp
        
        # Add timestamp to model info
        model_info["timestamp"] = timestamp.isoformat()
        
        self.models.append(model_info)
        logger.debug(f"Added model to session: {model_info}")
    
    def record_command(self, command: str):
        """Record a command executed in the session"""
        if not self.active:
            logger.debug("Command executed but no active session to record it")
            return
        
        timestamp = datetime.now()
        self.last_activity = timestamp
        
        self.commands.append({
            "command": command,
            "timestamp": timestamp.isoformat()
        })
        
        logger.debug(f"Recorded command: {command}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session"""
        duration = None
        if self.active and self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
        
        idle_time = None
        if self.active and self.last_activity:
            idle_time = (datetime.now() - self.last_activity).total_seconds()
        
        return {
            "active": self.active,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration_seconds": duration,
            "port": self.port,
            "model_count": len(self.models),
            "command_count": len(self.commands),
            "session_file": self.session_file,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "idle_seconds": idle_time,
            "metadata": self.metadata
        }
    
    def get_command_history(self, limit=None) -> List[Dict[str, Any]]:
        """Get the command history for the session"""
        if limit:
            return self.commands[-limit:]
        return self.commands
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Get the list of models in the session"""
        return self.models
    
    def clear_history(self):
        """Clear the command history but keep session active"""
        if self.active:
            logger.info("Clearing command history for active session")
            self.commands = []
    
    def save_to_file(self, filename=None):
        """Save session information to a JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chimerax_session_{timestamp}.json"
        
        try:
            session_data = {
                "active": self.active,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "models": self.models,
                "commands": self.commands,
                "session_file": self.session_file,
                "metadata": self.metadata,
                "export_time": datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"Session information saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving session information: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def load_from_file(self, filename):
        """Load session information from a JSON file"""
        try:
            with open(filename, 'r') as f:
                session_data = json.load(f)
            
            # Only load history data, not active session state
            self.models = session_data.get("models", [])
            self.commands = session_data.get("commands", [])
            self.session_file = session_data.get("session_file")
            self.metadata = session_data.get("metadata", {})
            
            logger.info(f"Loaded session information from {filename}")
            return True
        except Exception as e:
            logger.error(f"Error loading session information: {str(e)}")
            logger.error(traceback.format_exc())
            return False

# Create a global session instance
chimerax_session = ChimeraXSession() 