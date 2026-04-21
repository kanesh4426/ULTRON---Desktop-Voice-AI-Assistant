﻿import os
import re
import sys
import subprocess
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import google.generativeai as genai
from app.models.generation_request import GenerationRequest
from app.orchestration.app_controller import AppController
from app.orchestration.workflow_runner import AssistantEngine
from app.services.app_service import close_app, open_app
from app.utils.config import AssistantConfig

# Add debugger imports
try:
    from app.agents.roles.code_debugger import (
        debug_code,
        interactive_debugger,
        list_supported_debug_languages,
    )
    DEBUGGER_AVAILABLE = True
except ImportError:
    print("âš ï¸  Code debugger module not found. Debugging features disabled.")
    DEBUGGER_AVAILABLE = False

# Import ContentGenerator module
try:
    from content_generation import generate_content
    CONTENT_GEN_AVAILABLE = True
except ImportError:
    print("âš ï¸  Content generator module not found. Content generation features disabled.")
    CONTENT_GEN_AVAILABLE = False

# Import local_file_access module
try:
    from local_file_access import FileManager, FileManagerConfig
    FILE_ACCESSOR_AVAILABLE = True

    class LocalFileAccessor:
        def __init__(self, workspace_root: str | None = None):
            root = workspace_root or os.getcwd()
            cfg = FileManagerConfig(workspace_root=root, require_delete_confirmation=True)
            self.manager = FileManager(cfg)

        def create_file(self, file_path: str, content: str = "", overwrite: bool = False):
            return self.manager.create_file(file_path=file_path, content=content, overwrite=overwrite)

        def read_file(self, file_path: str, encoding: str = "utf-8"):
            return self.manager.read_file(file_path=file_path, encoding=encoding)

        def write_file(self, file_path: str, content: str, mode: str = "w", encoding: str = "utf-8"):
            if mode == "a":
                return self.manager.append_file(file_path=file_path, content=content, encoding=encoding)
            return self.manager.write_file(file_path=file_path, content=content, encoding=encoding)

        def append_file(self, file_path: str, content: str, encoding: str = "utf-8"):
            return self.manager.append_file(file_path=file_path, content=content, encoding=encoding)

        def delete_file(self, file_path: str, confirm: bool = False):
            return self.manager.delete_file(file_path=file_path, confirm=confirm)

        def rename(self, source_path: str, new_name: str):
            return self.manager.rename_file(source_path=source_path, new_name=new_name)

        def move(self, source_path: str, destination_path: str):
            return self.manager.move_file(source_path=source_path, destination_path=destination_path)

        def copy(self, source_path: str, destination_path: str):
            return self.manager.copy_file(source_path=source_path, destination_path=destination_path)

        def list_directory(
            self,
            directory_path: str = ".",
            show_hidden: bool = False,
            recursive: bool = False,
            extension_filter=None,
        ):
            return self.manager.list_directory(
                directory_path=directory_path,
                show_hidden=show_hidden,
                recursive=recursive,
                extension_filter=extension_filter,
            )

        def create_folder(self, folder_path: str, exist_ok: bool = True):
            return self.manager.create_folder(folder_path=folder_path, exist_ok=exist_ok)

        def delete_folder(self, folder_path: str, recursive: bool = False, confirm: bool = False):
            return self.manager.delete_folder(
                folder_path=folder_path,
                recursive=recursive,
                confirm=confirm,
            )

        def search_files(
            self,
            pattern: str,
            search_path: str = ".",
            recursive: bool = True,
            extension_filter=None,
        ):
            return self.manager.search_files(
                pattern=pattern,
                search_path=search_path,
                recursive=recursive,
                extension_filter=extension_filter,
            )

        def get_file_info(self, file_path: str):
            result = self.manager.get_file_metadata(file_path)
            if not result.get("success"):
                return result
            metadata = result.get("metadata", {})
            return {"success": True, **metadata, "message": result.get("message")}

        def file_exists(self, path: str):
            return self.manager.file_exists(path)

        def is_file(self, path: str):
            return self.manager.is_file(path)

        def is_dir(self, path: str):
            return self.manager.is_dir(path)

except ImportError:
    print("âš ï¸  local_file_access module not found. File operations disabled.")
    FILE_ACCESSOR_AVAILABLE = False

# Import AppManager module for application control
try:
    from app_access.manager import AppManager
    APP_CONTROLLER_AVAILABLE = True
    print("✅ AppManager imported successfully")
except ImportError as e:
    print(f"⚠️  AppManager import failed: {e}")
    # Create fallback dummy functions
    class DummyAppManager:
        def open_application(self, app_name): 
            return {'success': False, 'error': 'AppManager not available'}
        def close_application(self, app_name): 
            return {'success': False, 'error': 'AppManager not available'}
        def process_command(self, command): 
            return {'success': False, 'error': 'AppManager not available'}
        def is_application_running(self, app_name): 
            return {'success': False, 'error': 'AppManager not available'}
        def list_running_apps(self): 
            return {'success': False, 'error': 'AppManager not available'}
        def open_website(self, target): 
            return {'success': False, 'error': 'AppManager not available'}
    
    AppManager = DummyAppManager
    APP_CONTROLLER_AVAILABLE = False
class UltronAI:
    """
    ULTRON AI Assistant - Advanced Task Executor
    A powerful AI assistant that can execute system tasks safely and efficiently.
    """
    
    def __init__(self, groq_api_key: str = None):
        """Initialize ULTRON AI Assistant
         Args:
             groq_api_key (str): Groq API key for code generation
         """
        self.groq_api_key = groq_api_key
        self.load_environment()
        
        config = AssistantConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            groq_api_key=self.api_key,
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.engine = AssistantEngine(config)
        
        self.setup_conversation_context()

        # Initialize CodeGenerator with API key
        try:
            from app.agents.roles.code_generator import CodeGenerator
            self.codegen = CodeGenerator(engine=self.engine)
        except ImportError:
            print("âŒ CodeGenerator module not found. Code generation features disabled.")
            self.codegen = None

        # Initialize file accessor if available
        if FILE_ACCESSOR_AVAILABLE:
            self.file_accessor = LocalFileAccessor()
        else:
            self.file_accessor = None

        # Initialize app controller if available
        if APP_CONTROLLER_AVAILABLE:
            self.app_controller = AppManager()
        else:
            self.app_controller = None

    def load_environment(self):
        """Load environment variables safely"""
        try:
            load_dotenv()
            self.api_key = self.groq_api_key or os.getenv("GROQ_API_KEY")
        except Exception as e:
            print(f"âŒ Failed to load environment: {e}")
            sys.exit(1)
            
    def setup_conversation_context(self):
        """Setup the conversation context for ULTRON AI"""
        self.system_prompt = """You are ULTRON, an advanced AI assistant. You are designed to be helpful, safe, and efficient.
You are a task executor that can perform system operations safely. Always prioritize user safety and system security.

### 1. **Automating YouTube Video Search & Google Search**
**User:** "Write a Python script to search YouTube and Google automatically."

**ULTRON:**
```python
import pywhatkit

def play_song(song: str) -> None:
    pywhatkit.playonyt(song)

def google_search(query: str) -> None:
    pywhatkit.search(query)

# Example usage
play_song("Imagine Dragons Believer")
google_search("Latest AI advancements")
```

Available modules: webbrowser, pyautogui, time, pyperclip, random, datetime, tkinter, os, subprocess (use carefully), psutil for process management.
IMPORTANT: For opening applications and websites, use the built-in AppController module instead of writing raw Python code.
Application control examples:
- 'open chrome' → Uses AppController
- 'open https://google.com' → Uses AppController
- 'close chrome' → Uses AppController

Examples for better context:
User: open Google Chrome
Assistant: 
```python
import webbrowser
import time

# Open Chrome with Google homepage
webbrowser.register('chrome', None, webbrowser.BackgroundBrowser('chrome'))
webbrowser.get('chrome').open('https://www.google.com')
time.sleep(1)  # Brief pause for application to load
print('Google Chrome opened successfully')
```

User: close Google Chrome
Assistant: 
```python
import psutil
import os
import time

try:
    # Find and terminate Chrome processes
    for proc in psutil.process_iter(['pid', 'name']):
        if 'chrome' in proc.info['name'].lower():
            proc.terminate()
    time.sleep(2)
    print('Google Chrome closed successfully')
except Exception as e:
    # Fallback method
    if os.name == 'nt':  # Windows
        os.system('taskkill /im chrome.exe /f')
    else:  # Unix/Linux/Mac
        os.system('pkill -f chrome')
    print('Chrome closed using fallback method')
```"""
        
    def execute_task(self, task: str) -> Optional[str]:
        """
        Execute a task using the Groq API
        
        Args:
            task (str): The task to be executed
            
        Returns:
            Optional[str]: The response from the API or None if failed
        """
        try:
            full_prompt = f"{self.system_prompt}\n\nUser: {task}"
            req = GenerationRequest(
                user_input=full_prompt,
                task_type="coding"
            )
            result = self.engine.generate(req)
            if result.get("success"):
                return result.get("response", "").strip()
            return None
            
        except Exception as e:
            return None
    
    def extract_code_from_response(self, response: str) -> Optional[str]:
        """
        Extract Python code from the API response
        
        Args:
            response (str): The response containing Python code
            
        Returns:
            Optional[str]: Extracted Python code or None if not found
        """
        if not response:
            return None
            
        # Multiple patterns to catch different code block formats
        patterns = [
            r'```python\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'`([^`]+)`'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                code = matches[0].strip()
                return code
                
        return None
    
    def validate_code_safety(self, code: str) -> bool:
        """
        Basic safety validation for code execution
        
        Args:
            code (str): Python code to validate
            
        Returns:
            bool: True if code appears safe, False otherwise
        """
        dangerous_patterns = [
            r'rm\s+-rf',
            r'del\s+/[fFsS]',
            r'format\s+[cC]:',
            r'__import__\s*\(\s*["\']os["\']',
            r'eval\s*\(',
            r'exec\s*\(',
            r'open\s*\([^)]*["\'][wWaA]'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False
                
        return True
    
    def execute_python_code(self, code: str) -> str:
        """
        Safely execute Python code with error handling
        """
        if not code:
            return ""
            
        if not self.validate_code_safety(code):
            return ""
            
        try:
            # Create a controlled execution environment with AppController support
            exec_globals = {
                '__builtins__': __builtins__,
                'print': print,
                # Add safe modules
                'os': os,
                'time': __import__('time'),
                'webbrowser': __import__('webbrowser'),
                'psutil': __import__('psutil') if self._module_available('psutil') else None,
                'subprocess': __import__('subprocess'),
                # Add AppController if available
                'AppController': AppController if APP_CONTROLLER_AVAILABLE else None,
                'open_app': open_app if APP_CONTROLLER_AVAILABLE else None,
                'close_app': close_app if APP_CONTROLLER_AVAILABLE else None,
            }
            
            # Execute the code
            exec(code, exec_globals)
            
            return ""
            
        except ImportError as e:
            return f"Import error: {e}"
            
        except Exception as e:
            return f"Execution error: {e}"
        
    def _module_available(self, module_name: str) -> bool:
        """Check if a module is available for import"""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def run_task(self, task: str) -> str:
        """
        Complete task execution pipeline with AppController integration
        
        """
        if not task.strip():
            return ""

        #Check if this is an app-related command that should use AppController
        app_commands = ['open', 'close', 'start', 'launch', 'run']
        app_targets = ['chrome', 'firefox', 'browser', 'whatsapp', 'discord', 'telegram', 'spotify']
        
        task_lower = task.lower()
        should_use_app_controller = any(cmd in task_lower for cmd in app_commands) and \
                                any(target in task_lower for target in app_targets)
    
        if should_use_app_controller and APP_CONTROLLER_AVAILABLE:
            return self._handle_app_task(task)
        
        # Original AI-based execution
        response = self.execute_task(task)
        if not response:
            return ""
            
        code = self.extract_code_from_response(response)
        if not code:
            return ""
            
        result = self.execute_python_code(code)
        return result
    def _handle_app_task(self, task: str) -> str:
        """
        Handle application-related tasks using AppController
        """
        task_lower = task.lower()
        
        if 'open' in task_lower or 'start' in task_lower or 'launch' in task_lower:
            if 'chrome' in task_lower or 'browser' in task_lower:
                # Check if it's a website or browser
                if any(proto in task_lower for proto in ['http', 'https', 'www.', '.com', '.org']):
                    # Extract URL
                    import re
                    url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+)', task)
                    if url_match:
                        url = url_match.group(0)
                        result = self.app_control('open_website', url)
                        return result['message'] if result['success'] else f"Error: {result['error']}"
                else:
                    # Open Chrome browser
                    result = self.app_control('open_application', 'chrome')
                    return result['message'] if result['success'] else f"Error: {result['error']}"
            
            elif 'whatsapp' in task_lower:
                result = self.app_control('open_application', 'whatsapp')
                return result['message'] if result['success'] else f"Error: {result['error']}"
                
            elif 'discord' in task_lower:
                result = self.app_control('open_application', 'discord')
                return result['message'] if result['success'] else f"Error: {result['error']}"
                
            elif 'telegram' in task_lower:
                result = self.app_control('open_application', 'telegram')
                return result['message'] if result['success'] else f"Error: {result['error']}"
        
        elif 'close' in task_lower or 'quit' in task_lower or 'exit' in task_lower:
            if 'chrome' in task_lower:
                result = self.app_control('close_application', 'chrome')
                return result['message'] if result['success'] else f"Error: {result['error']}"
            # Add other apps similarly
        #Fallback to AI if not handled by AppController
        response = self.execute_task(task)
        if not response:
            return ""        
        
        code = self.extract_code_from_response(response)
        if not code:
            return ""
            
        result = self.execute_python_code(code)
        return result
    
    # New Code Generation Methods
    def generate_code(self, prompt: str, language: str = None, save_to_file: bool = False) -> Dict[str, str]:
        """
        Generate code using the CodeGenerator module
        
        Args:
            prompt (str): Code generation prompt
            language (str, optional): Specific programming language
            save_to_file (bool): Whether to save code to file
            
        Returns:
            Dict: Code generation results
        """
        if not self.codegen:
            return {
            'code': "CodeGenerator not available",
            'language': 'text',
            'full_response': "CodeGenerator module not initialized"
        }
        result = self.codegen.generate_code(prompt, language)
        
        if save_to_file and result['language'] != 'text':
            filepath = self.codegen.save_code_to_file(
                result['code'], 
                result['language']
            )
            result['filepath'] = filepath
        
        return result
    
    def write_python_script(self, description: str, save: bool = True) -> Dict[str, str]:
        """Generate Python code for a given task description"""
        return self.generate_code(description, 'python', save)
    
    def write_javascript_code(self, description: str, save: bool = True) -> Dict[str, str]:
        """Generate JavaScript code"""
        return self.generate_code(description, 'javascript', save)
    
    def write_sql_query(self, description: str, save: bool = True) -> Dict[str, str]:
        """Generate SQL queries"""
        return self.generate_code(description, 'sql', save)
    
    def write_html_page(self, description: str, save: bool = True) -> Dict[str, str]:
        """Generate HTML code"""
        return self.generate_code(description, 'html', save)
    
    def list_supported_languages(self) -> List[str]:
        """Get list of supported programming languages"""
        return self.codegen.list_supported_languages()
    
    # Debugger Methods
    def debug_code(self, code: str, language: str = None) -> Dict[str, any]:
        """
        Debug code in any supported language
        
        Args:
            code (str): Code with errors
            language (str, optional): Specific language
            
        Returns:
            Dict: Debugging results
        """
        if not DEBUGGER_AVAILABLE:
            return {"error": "Debugger not available"}
        
        from app.agents.roles.code_debugger import MultiLanguageDebugger
        debugger = MultiLanguageDebugger(engine=self.engine)
        return debugger.debug_code(code, language)

    def list_debug_languages(self) -> List[str]:
        """List all supported debugging languages"""
        if not DEBUGGER_AVAILABLE:
            return ["Debugger not available"]
        
        return list_supported_debug_languages()
    def app_control(self, operation: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Control applications and websites
    
        Args:
            operation (str): Operation to perform
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
        
        Returns:
            Dict: Operation result
        """
        if not APP_CONTROLLER_AVAILABLE or not self.app_controller:
            return {
                "success": False,
                "error": "App controller not available"
            }
    
        try:
            operation_methods = {
                'open_website': self.app_controller.open_website,
                'open_application': self.app_controller.open_application,
                'close_application': self.app_controller.close_application,
                'is_running': self.app_controller.is_application_running,
                'list_apps': self.app_controller.list_running_applications
            }
            
            if operation not in operation_methods:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
            
            method = operation_methods[operation]
            return method(*args, **kwargs)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"App control operation failed: {str(e)}"
            }

    def handle_app_command(self, command: str) -> str:
        """
        Handle application control commands
        
        Args:
            command (str): Application control command
            
        Returns:
            str: Result message
        """
        if not APP_CONTROLLER_AVAILABLE:
            return "âŒ Application control not available. Install AppController module."
        
        parts = command.split()
        if len(parts) < 2:
            return "âŒ Usage: app [operation] [arguments...]"
        
        operation = parts[1].lower()
        args = parts[2:]
        
        try:
            if operation == 'open':
                if len(args) < 1:
                    return "âŒ Usage: app open [app_name/url] [browser?]"
                
                target = args[0]
                browser = args[1] if len(args) > 1 else 'default'
                
                # Check if it's a URL
                if target.startswith(('http://', 'https://', 'www.')):
                    result = self.app_control('open_website', target, browser)
                else:
                    result = self.app_control('open_application', target)
                    
            elif operation == 'close':
                if len(args) < 1:
                    return "âŒ Usage: app close [app_name]"
                result = self.app_control('close_application', args[0])
                
            elif operation == 'status':
                if len(args) < 1:
                    return "âŒ Usage: app status [app_name]"
                result = self.app_control('is_running', args[0])
                
            elif operation == 'list':
                result = self.app_control('list_apps')
                
            else:
                return f"âŒ Unknown app operation: {operation}"
            
            # Format result
            if result['success']:   
                if operation == 'status':
                    status = "âœ… Running" if result['running'] else "âŒ Not running"
                    return f"{status} - {result['app']} ({result['process_count']} processes)"
                elif operation == 'list':
                    apps = result['applications']
                    output = f"ðŸ“± Running applications ({result['count']}):\n"
                    for app in apps[:10]:  # Show first 10
                        output += f"â€¢ {app['name']} (PID: {app['pid']})\n"
                    if result['count'] > 10:
                        output += f"... and {result['count'] - 10} more"
                    return output
                else:
                    return f"âœ… {result['message']}"
            else:
                return f"âŒ {result['error']}"
                
        except Exception as e:
            return f"âŒ Error executing app command: {str(e)}"
    
    # File Operations Methods
    def file_operations(self, operation: str, *args, **kwargs) -> Dict[str, Any]:
            """
            Perform file operations using LocalFileAccessor

            Args:
                operation (str): File operation to perform
                *args: Arguments for the operation
                **kwargs: Keyword arguments for the operation

            Returns:
                Dict: Operation result
            """
            if not FILE_ACCESSOR_AVAILABLE or not self.file_accessor:
                return {
                    "success": False,
                    "error": "File accessor not available"
                }
            try:
                # Map operation names to methods
                operation_methods = {
                    'create_file': self.file_accessor.create_file,
                    'create_folder': self.file_accessor.create_folder,
                    'delete_file': self.file_accessor.delete_file,
                    'delete_folder': self.file_accessor.delete_folder,
                    'rename': self.file_accessor.rename,
                    'move': self.file_accessor.move,
                    'copy': self.file_accessor.copy,
                    'read_file': self.file_accessor.read_file,
                    'write_file': self.file_accessor.write_file,
                    'list_directory': self.file_accessor.list_directory,
                    'get_file_info': self.file_accessor.get_file_info,
                    'search_files': self.file_accessor.search_files,
                    'file_exists': self.file_accessor.file_exists,
                    'is_file': self.file_accessor.is_file,
                    'is_dir': self.file_accessor.is_dir
                }

                if operation not in operation_methods:
                    return {
                        "success": False,
                        "error": f"Unknown operation: {operation}"
                    }

                method = operation_methods[operation]
                return method(*args, **kwargs)

            except Exception as e:
                return {
                    "success": False,
                    "error": f"File operation failed: {str(e)}"
                }

    def handle_file_command(self, command: str) -> str:
        """
        Handle file operation commands from interactive mode
        
        Args:
            command (str): File operation command
            
        Returns:
            str: Result message
        """
        if not FILE_ACCESSOR_AVAILABLE:
            return "âŒ File operations not available. Install LocalFileAccessor module."
        
        parts = command.split()
        if len(parts) < 2:
            return "âŒ Usage: file [operation] [arguments...]"
        
        operation = parts[1].lower()
        args = parts[2:]
        
        try:
            if operation == 'create':
                if len(args) < 1:
                    return "âŒ Usage: file create [filename] [content?]"
                content = ' '.join(args[1:]) if len(args) > 1 else ""
                result = self.file_operations('create_file', args[0], content)
                
            elif operation == 'read':
                if len(args) < 1:
                    return "âŒ Usage: file read [filename]"
                result = self.file_operations('read_file', args[0])
                
            elif operation == 'delete':
                if len(args) < 1:
                    return "âŒ Usage: file delete [filename]"
                result = self.file_operations('delete_file', args[0])
                
            elif operation == 'mkdir':
                if len(args) < 1:
                    return "âŒ Usage: file mkdir [foldername]"
                result = self.file_operations('create_folder', args[0])
                
            elif operation == 'rmdir':
                if len(args) < 1:
                    return "âŒ Usage: file rmdir [foldername]"
                recursive = '--recursive' in args or '-r' in args
                result = self.file_operations('delete_folder', args[0], recursive)
                
            elif operation == 'rename':
                if len(args) < 2:
                    return "âŒ Usage: file rename [oldname] [newname]"
                result = self.file_operations('rename', args[0], args[1])
                
            elif operation == 'move':
                if len(args) < 2:
                    return "âŒ Usage: file move [source] [destination]"
                result = self.file_operations('move', args[0], args[1])
                
            elif operation == 'copy':
                if len(args) < 2:
                    return "âŒ Usage: file copy [source] [destination]"
                result = self.file_operations('copy', args[0], args[1])
                
            elif operation == 'list':
                path = args[0] if len(args) > 0 else "."
                show_hidden = '--hidden' in args or '-h' in args
                result = self.file_operations('list_directory', path, show_hidden)
                
            elif operation == 'info':
                if len(args) < 1:
                    return "âŒ Usage: file info [path]"
                result = self.file_operations('get_file_info', args[0])
                
            elif operation == 'search':
                if len(args) < 1:
                    return "âŒ Usage: file search [pattern] [path?]"
                pattern = args[0]
                path = args[1] if len(args) > 1 else "."
                recursive = not ('--no-recursive' in args or '-n' in args)
                result = self.file_operations('search_files', pattern, path, recursive)
                
            elif operation == 'exists':
                if len(args) < 1:
                    return "âŒ Usage: file exists [path]"
                result = self.file_accessor.file_exists(args[0])
                return f"âœ… Path exists: {result}"
                
            else:
                return f"âŒ Unknown file operation: {operation}"
            
            # Format the result
            if result['success']:
                if operation == 'read':
                    return f"âœ… File content:\n{result['content']}"
                elif operation == 'list':
                    items = result['items']
                    output = f"ðŸ“ Directory listing ({result['count']} items):\n"
                    for item in items:
                        icon = "ðŸ“„" if item['is_file'] else "ðŸ“"
                        output += f"{icon} {item['name']} ({item['size']} bytes)\n"
                    return output
                elif operation == 'info':
                    info = result
                    return f"ðŸ“‹ File info:\nName: {info['name']}\nPath: {info['path']}\nSize: {info['size']} bytes\nType: {'File' if info['is_file'] else 'Directory'}\nModified: {info['modified']}"
                elif operation == 'search':
                    matches = result['matches']
                    output = f"ðŸ” Search results ({result['count']} matches):\n"
                    for match in matches:
                        output += f"â€¢ {match}\n"
                    return output
                else:
                    return f"âœ… {result['message']}"
            else:
                return f"âŒ {result['error']}"
                
        except Exception as e:
            return f"âŒ Error executing file operation: {str(e)}"
