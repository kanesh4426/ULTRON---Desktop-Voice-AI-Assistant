import os
import re
import sys
import subprocess
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv
import google.generativeai as genai

# Add debugger imports
try:
    from app.agents.roles.code_debugger import (
        debug_code,
        interactive_debugger,
        list_supported_debug_languages,
    )
    DEBUGGER_AVAILABLE = True
except ImportError:
    print("⚠️  Code debugger module not found. Debugging features disabled.")
    DEBUGGER_AVAILABLE = False

# Import ContentGenerator module
try:
    from app.agents.roles.content_generator import generate_content
    CONTENT_GEN_AVAILABLE = True
except ImportError:
    print("⚠️  Content generator module not found. Content generation features disabled.")
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
    print("⚠️  local_file_access module not found. File operations disabled.")
    FILE_ACCESSOR_AVAILABLE = False

# Import AppController module for application control
try:
    from app.services.app_service import AppController, open_app, close_app, process_command, is_app_running
    APP_CONTROLLER_AVAILABLE = True
    print("✅ AppController imported successfully")
except ImportError as e:
    print(f"⚠️  AppController import failed: {e}")
    # Create fallback dummy functions
    class DummyAppController:
        def open_application(self, app_name): 
            return {'success': False, 'error': 'AppController not available'}
        def close_application(self, app_name): 
            return {'success': False, 'error': 'AppController not available'}
        def process_command(self, command): 
            return {'success': False, 'error': 'AppController not available'}
        def is_app_running(self, app_name): 
            return {'success': False, 'error': 'AppController not available'}
        def list_running_apps(self): 
            return {'success': False, 'error': 'AppController not available'}
    
    AppController = DummyAppController
    open_app = lambda app_name: {'success': False, 'error': 'AppController not available'}
    close_app = lambda app_name: {'success': False, 'error': 'AppController not available'}
    process_command = lambda command: {'success': False, 'error': 'AppController not available'}
    is_app_running = lambda app_name: {'success': False, 'error': 'AppController not available'}
    APP_CONTROLLER_AVAILABLE = False
class JARVISAI:
    """
    JARVIS AI Assistant - Advanced Task Executor
    A powerful AI assistant that can execute system tasks safely and efficiently.
    """
    
    def __init__(self, groq_api_key: str = None):
        """Initialize JARVIS AI Assistant
         Args:
             groq_api_key (str): Groq API key for code generation
         """
        self.groq_api_key = groq_api_key
        self.load_environment()
        self.initialize_client()
        self.setup_conversation_context()

        # Initialize CodeGenerator with API key
        try:
            from CodeGenerator import CodeGenerator
            api_key = self.groq_api_key or os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("No API key found for CodeGenerator")
            self.codegen = CodeGenerator(api_key=api_key)
        except ImportError:
            print("❌ CodeGenerator module not found. Code generation features disabled.")
            self.codegen = None

        # Initialize file accessor if available
        if FILE_ACCESSOR_AVAILABLE:
            self.file_accessor = LocalFileAccessor()
        else:
            self.file_accessor = None

        # Initialize app controller if available
        if APP_CONTROLLER_AVAILABLE:
            self.app_controller = AppController()
        else:
            self.app_controller = None

    def load_environment(self):
        """Load environment variables safely"""
        try:
            load_dotenv()
            #Use provided API key or fall back to environment variable
            self.api_key = self.groq_api_key or os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY not found in environment variables or provided parameter")
        except Exception as e:
            print(f"❌ Failed to load environment: {e}")
            sys.exit(1)
            
    def initialize_client(self):
        """Initialize the Groq API client"""
        try:
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self.api_key
            )
        except Exception as e:
            print(f"❌ Failed to initialize API client: {e}")
            sys.exit(1)
            
    def setup_conversation_context(self):
        """Setup the conversation context for JARVIS AI"""
        self.messages = [
            {
                "role": "system", 
                "content": "You are JARVIS, an advanced AI assistant created by Kanesh. You are designed to be helpful, safe, and efficient."
            },
            {
                "role": "system", 
                "content": """You are a task executor that can perform system operations safely. Always prioritize user safety and system security.

                ### 1. **Automating YouTube Video Search & Google Search**
                **User:** "Write a Python script to search YouTube and Google automatically."

                **JARVIS:**
                ```python
                import pywhatkit

                def play_song(song: str) -> None:
                    pywhatkit.playonyt(song)

                def google_search(query: str) -> None:
                    pywhatkit.search(query)

                # Example usage
                play_song("Imagine Dragons Believer")
                google_search("Latest AI advancements")

                """
            },
            {
                "role": "system", 
                "content": "Available modules: webbrowser, pyautogui, time, pyperclip, random, datetime, tkinter, os, subprocess (use carefully), psutil for process management."
            },
            {
                "role": "system", 
                "content": "IMPORTANT: For opening applications and websites, use the built-in AppController module instead of writing raw Python code."
            },
            {
                "role": "system", 
                "content": "Application control examples:\n- 'open chrome' → Uses AppController\n- 'open https://google.com' → Uses AppController\n- 'close chrome' → Uses AppController"
            },
            # Examples for better context
            {
                "role": "user", 
                "content": "open Google Chrome"
            },
            {
                "role": "assistant", 
                "content": "\n```python\nimport webbrowser\nimport time\n\n# Open Chrome with Google homepage\nwebbrowser.register('chrome', None, webbrowser.BackgroundBrowser('chrome'))\nwebbrowser.get('chrome').open('https://www.google.com')\ntime.sleep(1)  # Brief pause for application to load\nprint('Google Chrome opened successfully')\n```"
            },
            {
                "role": "user", 
                "content": "close Google Chrome"
            },
            {
                "role": "assistant", 
                "content": "\n```python\nimport psutil\nimport os\nimport time\n\ntry:\n    # Find and terminate Chrome processes\n    for proc in psutil.process_iter(['pid', 'name']):\n        if 'chrome' in proc.info['name'].lower():\n            proc.terminate()\n    time.sleep(2)\n    print('Google Chrome closed successfully')\nexcept Exception as e:\n    # Fallback method\n    if os.name == 'nt':  # Windows\n        os.system('taskkill /im chrome.exe /f')\n    else:  # Unix/Linux/Mac\n        os.system('pkill -f chrome')\n    print('Chrome closed using fallback method')\n```"
            }
        ]
        
    def execute_task(self, task: str) -> Optional[str]:
        """
        Execute a task using the Groq API
        
        Args:
            task (str): The task to be executed
            
        Returns:
            Optional[str]: The response from the API or None if failed
        """
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.messages + [{"role": "user", "content": task}],
                max_tokens=1500,
                temperature=0.7,
                top_p=0.9
            )
            
            result = response.choices[0].message.content.strip()
            return result
            
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
        
        return debug_code(code, language)

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
            return "❌ Application control not available. Install AppController module."
        
        parts = command.split()
        if len(parts) < 2:
            return "❌ Usage: app [operation] [arguments...]"
        
        operation = parts[1].lower()
        args = parts[2:]
        
        try:
            if operation == 'open':
                if len(args) < 1:
                    return "❌ Usage: app open [app_name/url] [browser?]"
                
                target = args[0]
                browser = args[1] if len(args) > 1 else 'default'
                
                # Check if it's a URL
                if target.startswith(('http://', 'https://', 'www.')):
                    result = self.app_control('open_website', target, browser)
                else:
                    result = self.app_control('open_application', target)
                    
            elif operation == 'close':
                if len(args) < 1:
                    return "❌ Usage: app close [app_name]"
                result = self.app_control('close_application', args[0])
                
            elif operation == 'status':
                if len(args) < 1:
                    return "❌ Usage: app status [app_name]"
                result = self.app_control('is_running', args[0])
                
            elif operation == 'list':
                result = self.app_control('list_apps')
                
            else:
                return f"❌ Unknown app operation: {operation}"
            
            # Format result
            if result['success']:   
                if operation == 'status':
                    status = "✅ Running" if result['running'] else "❌ Not running"
                    return f"{status} - {result['app']} ({result['process_count']} processes)"
                elif operation == 'list':
                    apps = result['applications']
                    output = f"📱 Running applications ({result['count']}):\n"
                    for app in apps[:10]:  # Show first 10
                        output += f"• {app['name']} (PID: {app['pid']})\n"
                    if result['count'] > 10:
                        output += f"... and {result['count'] - 10} more"
                    return output
                else:
                    return f"✅ {result['message']}"
            else:
                return f"❌ {result['error']}"
                
        except Exception as e:
            return f"❌ Error executing app command: {str(e)}"
    
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
            return "❌ File operations not available. Install LocalFileAccessor module."
        
        parts = command.split()
        if len(parts) < 2:
            return "❌ Usage: file [operation] [arguments...]"
        
        operation = parts[1].lower()
        args = parts[2:]
        
        try:
            if operation == 'create':
                if len(args) < 1:
                    return "❌ Usage: file create [filename] [content?]"
                content = ' '.join(args[1:]) if len(args) > 1 else ""
                result = self.file_operations('create_file', args[0], content)
                
            elif operation == 'read':
                if len(args) < 1:
                    return "❌ Usage: file read [filename]"
                result = self.file_operations('read_file', args[0])
                
            elif operation == 'delete':
                if len(args) < 1:
                    return "❌ Usage: file delete [filename]"
                result = self.file_operations('delete_file', args[0])
                
            elif operation == 'mkdir':
                if len(args) < 1:
                    return "❌ Usage: file mkdir [foldername]"
                result = self.file_operations('create_folder', args[0])
                
            elif operation == 'rmdir':
                if len(args) < 1:
                    return "❌ Usage: file rmdir [foldername]"
                recursive = '--recursive' in args or '-r' in args
                result = self.file_operations('delete_folder', args[0], recursive)
                
            elif operation == 'rename':
                if len(args) < 2:
                    return "❌ Usage: file rename [oldname] [newname]"
                result = self.file_operations('rename', args[0], args[1])
                
            elif operation == 'move':
                if len(args) < 2:
                    return "❌ Usage: file move [source] [destination]"
                result = self.file_operations('move', args[0], args[1])
                
            elif operation == 'copy':
                if len(args) < 2:
                    return "❌ Usage: file copy [source] [destination]"
                result = self.file_operations('copy', args[0], args[1])
                
            elif operation == 'list':
                path = args[0] if len(args) > 0 else "."
                show_hidden = '--hidden' in args or '-h' in args
                result = self.file_operations('list_directory', path, show_hidden)
                
            elif operation == 'info':
                if len(args) < 1:
                    return "❌ Usage: file info [path]"
                result = self.file_operations('get_file_info', args[0])
                
            elif operation == 'search':
                if len(args) < 1:
                    return "❌ Usage: file search [pattern] [path?]"
                pattern = args[0]
                path = args[1] if len(args) > 1 else "."
                recursive = not ('--no-recursive' in args or '-n' in args)
                result = self.file_operations('search_files', pattern, path, recursive)
                
            elif operation == 'exists':
                if len(args) < 1:
                    return "❌ Usage: file exists [path]"
                result = self.file_accessor.file_exists(args[0])
                return f"✅ Path exists: {result}"
                
            else:
                return f"❌ Unknown file operation: {operation}"
            
            # Format the result
            if result['success']:
                if operation == 'read':
                    return f"✅ File content:\n{result['content']}"
                elif operation == 'list':
                    items = result['items']
                    output = f"📁 Directory listing ({result['count']} items):\n"
                    for item in items:
                        icon = "📄" if item['is_file'] else "📁"
                        output += f"{icon} {item['name']} ({item['size']} bytes)\n"
                    return output
                elif operation == 'info':
                    info = result
                    return f"📋 File info:\nName: {info['name']}\nPath: {info['path']}\nSize: {info['size']} bytes\nType: {'File' if info['is_file'] else 'Directory'}\nModified: {info['modified']}"
                elif operation == 'search':
                    matches = result['matches']
                    output = f"🔍 Search results ({result['count']} matches):\n"
                    for match in matches:
                        output += f"• {match}\n"
                    return output
                else:
                    return f"✅ {result['message']}"
            else:
                return f"❌ {result['error']}"
                
        except Exception as e:
            return f"❌ Error executing file operation: {str(e)}"
    
    def interactive_mode(self):
        """Run Jarvis AI in interactive mode"""
        print("JARVIS AI Interactive Mode")
        print("commands:")
        print("  - 'generate code [language]: [prompt]' - Generate code")
        print("  - 'generate content [type]: [prompt]' - Generate content (blog, article, technical, creative)")
        print("  - 'execute: [task]' - Execute system task")

        if FILE_ACCESSOR_AVAILABLE:
            print("  - 'file [operation] [args]' - File operations")
            print("    Operations: create, read, delete, mkdir, rmdir, rename, move, copy, list, info, search, exists")
        if APP_CONTROLLER_AVAILABLE:
            print("  - 'app [operation] [args]' - Application control")
            print("    Operations: open, close, status, list")
        if DEBUGGER_AVAILABLE:
            print("  - 'debug: [language] [code]' - Debug code")
            print("  - 'debug interactive' - Start interactive debugger")
            print("  - 'debug languages' - List supported debug languages")
        print("  - 'exit' - Quit")

        while True:
            try:
                user_input = input("\nJARVIS>").strip()
                    
                if user_input.lower() in ['exit', 'quit','bye']:
                    print("Goodbye!")
                    break

                # Handle code generation commands
                if user_input.startswith('generate code'):
                    parts = user_input.split(':', 1)
                    if len(parts) > 1:
                        language_prompt = parts[0].replace('generate code', '').strip()
                        prompt = parts[1].strip()
                            
                        # Extract language if specified
                        language = None
                        if language_prompt:
                            language = language_prompt
                            
                        result = self.generate_code(prompt, language, save_to_file=True)
                        print(f"Generated {result['language'].upper()} code:")
                        print(result['code'])
                        if 'filepath' in result:
                            print(f"Saved to: {result['filepath']}")

                # Handle content generation commands
                elif user_input.startswith('generate content'):
                    if not CONTENT_GEN_AVAILABLE:
                        print("❌ Content generation not available. Install required modules.")
                        continue

                    parts = user_input.split(':', 1)
                    if len(parts) > 1:
                        type_prompt = parts[0].replace('generate content', '').strip()
                        prompt = parts[1].strip()
                            
                    # Extract content type if specified
                    content_type = "article"  # Default
                    if type_prompt:
                        content_type = type_prompt
                            
                    # Validate content type
                    valid_types = ["blog", "article", "technical", "creative"]
                    if content_type not in valid_types:
                        print(f"❌ Invalid content type. Choose from: {', '.join(valid_types)}")
                        continue

                    # Generate content
                    try:
                        from ContentGenerator import generate_content
                        result = generate_content(prompt, content_type=content_type)
                            
                        if result:
                            print("✅ Content generated successfully!")
                            print(f"📁 Saved to: {result['filepath']}")
                            if result.get('quality_issues'):
                                print("⚠️  Quality notes:", result['quality_issues'])
                        else:
                            print("❌ Content generation failed.")
                        
                    except Exception as e:
                        print(f"❌ Error generating content: {e}")

                # Handle debugger commands
                elif user_input.startswith('debug'):
                    if not DEBUGGER_AVAILABLE:
                         print("❌ Debugger not available. Install MultiLanguageDebugger module.")
                         continue
                    
                    if user_input == 'debug interactive':
                        print("Starting interactive debugger...")
                        interactive_debugger()
                    
                    elif user_input == 'debug languages':
                        languages = self.list_debug_languages()
                        print("Supported debug languages:")
                        for lang in languages:
                            print(f"  - {lang}")

                    elif user_input.startswith('debug:'):
                        debug_parts = user_input.replace('debug:', '').strip().split(' ', 1)
                        if len(debug_parts) >= 2:
                            language = debug_parts[0].strip()
                            code = debug_parts[1].strip()
                            
                            result = self.debug_code(code, language)
                            print(f"Debug results for {language}:")
                            print(f"Syntax Valid: {'✅' if result.get('syntax_valid', False) else '❌'}")  

                            if result.get('syntax_errors'):
                                for error in result['syntax_errors']:
                                    print(f"Error: {error}")
                            
                            if result.get('execution_output'):
                                print(f"Output: {result['execution_output']}")
                            
                            if result.get('fixed_code'):
                                print(f"\n🛠️  Fixed Code:")
                                print(f"```{result.get('language', '')}")
                                print(result['fixed_code'])
                                print("```")    
                        else:
                            print("❌ Usage: debug: [language] [code]")   
                    else:
                        print("❌ Unknown debug command. Use 'debug:', 'debug interactive', or 'debug languages'")               
                # Handle task execution commands
                elif user_input.startswith('execute:'):
                    task = user_input.replace('execute:', '').strip()
                    self.run_task(task)
                    print("Task executed")

                # Handle file operations
                elif user_input.startswith('file '):
                    result = self.handle_file_command(user_input)
                    print(result)
                 # Handle app control commands
                elif user_input.startswith('app '):
                    result = self.handle_app_command(user_input)
                    print(result)
                else:
                    print("Unknown command. Use 'generate code:' or 'execute:' or 'file' or 'debug'.")
                
            except Exception as e:
                print(f"Error: {e}")

def create_env_template():
    """Create a template .env file if it doesn't exist"""
    env_file = '.env'
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write("# Jarvis AI Configuration\n")
            f.write("GROQ_API_KEY=your_groq_api_key_here\n")
            f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")

def main():
    """Main function to run JARVIS AI"""
    create_env_template()
    
    try:
        jarvis = JARVISAI()
        
        # Check if running with command line argument
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()

            if mode == "execute" and len(sys.argv) > 2:
                #Task execution mode
                task = ' '.join(sys.argv[2:])
                jarvis.run_task(task)
                print("Task executed")

            elif mode == "generate" and len(sys.argv) > 2:
                # Code generation mode
                prompt = ' '.join(sys.argv[2:])
                result = jarvis.generate_code(prompt, save_to_file=True)
                print(f"Generated {result['language'].upper()} code:")
                print(result['code'])
                if 'filepath' in result:
                    print(f"Saved to: {result['filepath']}")    

            elif mode == "languages":
                # List supported languages
                languages = jarvis.list_supported_languages()
                print("Supported programming Languages:")
                for lang in languages:
                    print(f" - {lang}")

            # Debug mode
            elif mode == "debug" and len(sys.argv) > 2:
                code = ' '.join(sys.argv[2:])
                results = jarvis.debug_code(code)
                print(f"Debug results:")
                print(f"Syntax Valid: {'✅' if results.get('syntax_valid', False) else '❌'}")
                if results.get('syntax_errors'):
                    for error in results['syntax_errors']:
                        print(f"Error: {error}")
                if results.get('execution_output'):
                    print(f"Output: {results['execution_output']}")
            
            # Debug specific language mode
            elif mode == "debug-lang" and len(sys.argv) > 3:
                language = sys.argv[2]
                code = ' '.join(sys.argv[3:])
                results = jarvis.debug_code(code, language)
                print(f"Debug results for {language}:")
                print(f"Syntax Valid: {'✅' if results.get('syntax_valid', False) else '❌'}")
                if results.get('syntax_errors'):
                    for error in results['syntax_errors']:
                        print(f"Error: {error}")
                if results.get('execution_output'):
                    print(f"Output: {results['execution_output']}")
            
            # List debug languages
            elif mode == "debug-languages":
                languages = jarvis.list_debug_languages()
                print("Supported debugging languages:")
                for lang in languages:
                    print(f"  - {lang}")

            elif mode == "generate-content" and len(sys.argv) > 2:
                # Content generation mode
                topic = ' '.join(sys.argv[2:])
                result = generate_content(topic)
                if result:
                    print("Content generated and saved successfully.") 
                    print(f"📁 File: {result['filepath']}")       
                else:
                    print("❌ Content generation failed.")

            elif mode == "file" and len(sys.argv) > 2:
                # File operation mode
                operation = sys.argv[2]
                args = sys.argv[3:]
                command = f"file {operation} {' '.join(args)}"
                result = jarvis.handle_file_command(command)
                print(result)

            elif mode == "app" and len(sys.argv) > 2:
                # App control mode
                operation = sys.argv[2]
                args = sys.argv[3:]
                command = f"app {operation} {' '.join(args)}"
                result = jarvis.handle_app_command(command)
                print(result)
            else:
                print("usage:")
                print("  python Automation.py execute 'your task'")
                print("  python Automation.py generate 'your prompt'")
                print("  python Automation.py debug 'your code'")
                print("  python Automation.py debug-lang [language] 'your code'")
                print("  python Automation.py debug-languages")
                print("  python Automation.py generate-content 'your topic'")
                print("  python Automation.py file [operation] [arguments...]")
                print("  python Automation.py languages")
                
        else:
            # Interactive mode
            jarvis.interactive_mode()        
         
    except Exception as e:
        print(f"❌ Failed to initialize JARVIS AI: {e}")

if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ultron import main as ultron_main

    sys.exit(ultron_main(["automation"] + sys.argv[1:]))
