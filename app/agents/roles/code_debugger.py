import ast
import subprocess
import sys
import os
import tempfile
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from openai import OpenAI
from dotenv import load_dotenv

class MultiLanguageDebugger:
    """
    Advanced multi-language debugger that supports 14+ programming languages
    """
    
    # Language configurations
    LANGUAGE_CONFIGS = {
        'python': {
            'ext': '.py',
            'exec_cmd': [sys.executable, '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_python_syntax(code)
        },
        'javascript': {
            'ext': '.js',
            'exec_cmd': ['node', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_javascript_syntax(code)
        },
        'node.js': {
            'ext': '.js',
            'exec_cmd': ['node', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_javascript_syntax(code)
        },
        'java': {
            'ext': '.java',
            'exec_cmd': ['javac', '{file}', '&&', 'java', '{class_name}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_java_syntax(code)
        },
        'c++': {
            'ext': '.cpp',
            'exec_cmd': ['g++', '{file}', '-o', '{output}', '&&', './{output}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_cpp_syntax(code)
        },
        'c#': {
            'ext': '.cs',
            'exec_cmd': ['csc', '{file}', '&&', '{exe_name}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_csharp_syntax(code)
        },
        'php': {
            'ext': '.php',
            'exec_cmd': ['php', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_php_syntax(code)
        },
        'ruby': {
            'ext': '.rb',
            'exec_cmd': ['ruby', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_ruby_syntax(code)
        },
        'go': {
            'ext': '.go',
            'exec_cmd': ['go', 'run', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_go_syntax(code)
        },
        'rust': {
            'ext': '.rs',
            'exec_cmd': ['rustc', '{file}', '&&', './{output}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_rust_syntax(code)
        },
        'sql': {
            'ext': '.sql',
            'exec_cmd': None,
            'syntax_checker': lambda code: MultiLanguageDebugger._check_sql_syntax(code)
        },
        'html': {
            'ext': '.html',
            'exec_cmd': None,
            'syntax_checker': lambda code: MultiLanguageDebugger._check_html_syntax(code)
        },
        'css': {
            'ext': '.css',
            'exec_cmd': None,
            'syntax_checker': lambda code: MultiLanguageDebugger._check_css_syntax(code)
        },
        'typescript': {
            'ext': '.ts',
            'exec_cmd': ['ts-node', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_typescript_syntax(code)
        },
        'bash': {
            'ext': '.sh',
            'exec_cmd': ['bash', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_bash_syntax(code)
        },
        'shell': {
            'ext': '.sh',
            'exec_cmd': ['bash', '{file}'],
            'syntax_checker': lambda code: MultiLanguageDebugger._check_bash_syntax(code)
        }
    }
    
    SUPPORTED_LANGUAGES = list(LANGUAGE_CONFIGS.keys())
    
    def __init__(self):
        """Initialize the multi-language debugger"""
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
            
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.api_key
        )
    
    @staticmethod
    def detect_language(code: str) -> str:
        """Detect programming language from code snippet"""
        code_lower = code.lower()
        
        patterns = {
            'python': [r'^import\s', r'^from\s', r'def\s\w+\(', r'print\(', r'class\s\w+'],
            'javascript': [r'function\s\w+\(', r'console\.log\(', r'const\s|let\s|var\s', r'=>'],
            'java': [r'public\sclass', r'System\.out\.print', r'import\sjava\.'],
            'c++': [r'#include\s<', r'using\snamespace', r'std::cout', r'int\smain\(\)'],
            'c#': [r'using\sSystem;', r'Console\.WriteLine', r'class\s\w+\s*{'],
            'php': [r'<\?php', r'\$\w+\s*=', r'echo\s'],
            'ruby': [r'def\s\w+', r'puts\s', r'class\s\w+'],
            'go': [r'package\smain', r'import\s"', r'func\smain\(\)'],
            'rust': [r'fn\smain\(\)', r'println!\(', r'use\s'],
            'sql': [r'SELECT\s', r'INSERT\sINTO', r'CREATE\sTABLE'],
            'html': [r'<!DOCTYPE html>', r'<html>', r'<head>', r'<body>'],
            'css': [r'\{.*:.*\}', r'@media', r'\.\w+\s*{'],
            'typescript': [r'interface\s', r'type\s', r':\s*[^{]'],
            'bash': [r'#!/bin/bash', r'echo\s', r'if\s\[\s', r'for\s.*in']
        }
        
        for lang, lang_patterns in patterns.items():
            for pattern in lang_patterns:
                if re.search(pattern, code_lower):
                    return lang
        
        return 'python'
    
    @staticmethod
    def _check_python_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            ast.parse(code)
            return True, []
        except SyntaxError as e:
            return False, [f"Python Syntax Error: {e.msg} at line {e.lineno}"]
    
    @staticmethod
    def _check_javascript_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['node', '--check', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"JavaScript Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate JavaScript syntax (node.js required)"]
    
    @staticmethod
    def _check_java_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            class_match = re.search(r'class\s+(\w+)', code)
            if not class_match:
                return False, ["No class definition found"]
                
            with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['javac', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"Java Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate Java syntax (JDK required)"]
    
    @staticmethod
    def _check_cpp_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['g++', '-fsyntax-only', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"C++ Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate C++ syntax (g++ required)"]
    
    @staticmethod
    def _check_csharp_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cs', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['csc', '/target:library', '/nologo', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"C# Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate C# syntax (csc required)"]
    
    @staticmethod
    def _check_php_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.php', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['php', '-l', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"PHP Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate PHP syntax (PHP required)"]
    
    @staticmethod
    def _check_ruby_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.rb', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['ruby', '-c', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"Ruby Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate Ruby syntax (Ruby required)"]
    
    @staticmethod
    def _check_go_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.go', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['go', 'build', '-o', os.devnull, temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"Go Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate Go syntax (Go required)"]
    
    @staticmethod
    def _check_rust_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['rustc', '--emit', 'metadata', '-o', os.devnull, temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"Rust Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate Rust syntax (Rust required)"]
    
    @staticmethod
    def _check_sql_syntax(code: str) -> Tuple[bool, List[str]]:
        # Basic SQL syntax validation using regex patterns
        sql_patterns = [
            r'SELECT\s+.*\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+\w+\s+SET',
            r'DELETE\s+FROM',
            r'CREATE\s+TABLE',
            r'ALTER\s+TABLE'
        ]
        
        code_upper = code.upper()
        has_valid_pattern = any(re.search(pattern, code_upper) for pattern in sql_patterns)
        
        if has_valid_pattern:
            return True, []
        else:
            return False, ["No valid SQL statement pattern found"]
    
    @staticmethod
    def _check_html_syntax(code: str) -> Tuple[bool, List[str]]:
        # Basic HTML validation
        if re.search(r'<html.*>.*</html>', code, re.DOTALL | re.IGNORECASE):
            return True, []
        elif re.search(r'<[^>]+>', code):
            return True, []  # Has some HTML tags
        else:
            return False, ["No valid HTML structure found"]
    
    @staticmethod
    def _check_css_syntax(code: str) -> Tuple[bool, List[str]]:
        # Basic CSS validation
        if re.search(r'\{.*:.*\}', code):
            return True, []
        else:
            return False, ["No valid CSS rules found"]
    
    @staticmethod
    def _check_typescript_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['tsc', '--noEmit', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"TypeScript Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate TypeScript syntax (TypeScript required)"]
    
    @staticmethod
    def _check_bash_syntax(code: str) -> Tuple[bool, List[str]]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            result = subprocess.run(
                ['bash', '-n', temp_file],
                capture_output=True,
                text=True
            )
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return True, []
            else:
                return False, [f"Bash Syntax Error: {result.stderr}"]
        except:
            return False, ["Could not validate Bash syntax"]
    
    def analyze_syntax(self, code: str, language: str = None) -> Tuple[bool, List[str]]:
        """Analyze code syntax for the detected language"""
        if not language:
            language = self.detect_language(code)
        
        if language not in self.SUPPORTED_LANGUAGES:
            return False, [f"Unsupported language: {language}"]
        
        config = self.LANGUAGE_CONFIGS[language]
        if 'syntax_checker' in config and config['syntax_checker']:
            return config['syntax_checker'](code)
        
        return True, []
    
    def execute_code(self, code: str, language: str = None) -> Tuple[bool, str]:
        """Execute code and capture output/errors"""
        if not language:
            language = self.detect_language(code)
        
        if language not in self.SUPPORTED_LANGUAGES:
            return False, f"Unsupported language: {language}"
        
        config = self.LANGUAGE_CONFIGS[language]
        if not config['exec_cmd']:
            return False, f"Language {language} is not executable"
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=config['ext'], delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            cmd = []
            for part in config['exec_cmd']:
                if '{file}' in part:
                    part = part.replace('{file}', temp_file)
                if '{output}' in part:
                    base_name = os.path.splitext(temp_file)[0]
                    part = part.replace('{output}', base_name)
                if '{class_name}' in part:
                    class_match = re.search(r'class\s+(\w+)', code)
                    if class_match:
                        part = part.replace('{class_name}', class_match.group(1))
                    else:
                        return False, "No class name found in Java code"
                if '{exe_name}' in part:
                    base_name = os.path.splitext(temp_file)[0]
                    part = part.replace('{exe_name}', base_name + '.exe' if os.name == 'nt' else base_name)
                cmd.append(part)
            
            # Flatten command list and remove empty parts
            flat_cmd = []
            for item in cmd:
                if isinstance(item, list):
                    flat_cmd.extend(item)
                elif item:
                    flat_cmd.append(item)
            
            # Execute the command
            if '&&' in flat_cmd:
                # Handle multiple commands with shell=True
                cmd_str = ' '.join(flat_cmd)
                result = subprocess.run(
                    cmd_str,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                # Single command
                result = subprocess.run(
                    flat_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            # Cleanup
            try:
                os.unlink(temp_file)
                # Clean up compiled files
                if language == 'java':
                    class_file = temp_file.replace('.java', '.class')
                    if os.path.exists(class_file):
                        os.unlink(class_file)
                elif language in ['c++', 'rust']:
                    exe_file = os.path.splitext(temp_file)[0]
                    if os.path.exists(exe_file):
                        os.unlink(exe_file)
                    if os.path.exists(exe_file + '.exe'):
                        os.unlink(exe_file + '.exe')
            except:
                pass
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "Execution timed out (30 seconds)"
        except Exception as e:
            return False, f"Execution failed: {str(e)}"
    
    def get_ai_debug_suggestions(self, code: str, error_output: str, language: str) -> str:
        """Get AI-powered debugging suggestions for any language"""
        prompt = f"""
        Analyze this {language.upper()} code and fix the errors:

        ORIGINAL CODE:
        ```{language}
        {code}
        ```

        ERROR OUTPUT:
        {error_output}

        Please:
        1. Identify all errors in the code
        2. Explain what's wrong with each error
        3. Provide the fixed code
        4. Keep the same functionality and style
        5. Return only the fixed code in a code block

        Fixed code:
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": f"You are an expert {language} debugger. Fix code errors and provide clear explanations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3,
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"AI Debugging failed: {str(e)}"
    
    def extract_fixed_code(self, ai_response: str, language: str) -> str:
        """Extract fixed code from AI response"""
        patterns = [
            rf'```{language}\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'`([^`]+)`'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, ai_response, re.DOTALL)
            if matches:
                return matches[0].strip()
        
        return ai_response
    
    def debug_code(self, code: str, language: str = None) -> Dict[str, any]:
        """Main debugging function for any language"""
        if not language:
            language = self.detect_language(code)
        
        results = {
            'language': language,
            'original_code': code,
            'syntax_valid': False,
            'syntax_errors': [],
            'execution_success': False,
            'execution_output': '',
            'ai_suggestions': '',
            'fixed_code': '',
            'fixed_code_valid': False
        }
        
        # Syntax analysis
        syntax_valid, syntax_errors = self.analyze_syntax(code, language)
        results['syntax_valid'] = syntax_valid
        results['syntax_errors'] = syntax_errors
        
        # Execution test (if executable language)
        config = self.LANGUAGE_CONFIGS.get(language, {})
        if config.get('exec_cmd'):
            exec_success, exec_output = self.execute_code(code, language)
            results['execution_success'] = exec_success
            results['execution_output'] = exec_output
        
        # Get AI suggestions if there are errors
        if (not results.get('execution_success', True) or 
            not syntax_valid or 
            (not config.get('exec_cmd') and not syntax_valid)):
            
            error_output = results.get('execution_output', '') or '\n'.join(syntax_errors)
            ai_response = self.get_ai_debug_suggestions(code, error_output, language)
            results['ai_suggestions'] = ai_response
            
            # Extract fixed code
            fixed_code = self.extract_fixed_code(ai_response, language)
            results['fixed_code'] = fixed_code
            
            # Validate fixed code
            if fixed_code and fixed_code != code:
                fixed_valid, _ = self.analyze_syntax(fixed_code, language)
                results['fixed_code_valid'] = fixed_valid
        
        return results
    
    def list_supported_languages(self) -> List[str]:
        """Get list of all supported languages"""
        return self.SUPPORTED_LANGUAGES
    
    def interactive_debug(self):
        """Interactive debugging mode for any language"""
        print("🐛 JARVIS Multi-Language Debugger")
        print("Supported languages:", ", ".join(self.SUPPORTED_LANGUAGES))
        print("Paste your code (press Ctrl+D or Ctrl+Z when done):")
        
        try:
            lines = []
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    break
            
            code = '\n'.join(lines)
            if not code.strip():
                print("No code provided.")
                return
            
            print("\n🔍 Detecting language...")
            language = self.detect_language(code)
            print(f"Detected language: {language}")
            
            results = self.debug_code(code, language)
            self._print_debug_results(results)
            
        except Exception as e:
            print(f"Debugging failed: {str(e)}")
    
    def _print_debug_results(self, results: Dict[str, any]):
        """Print debug results in readable format"""
        print(f"\n📊 Debug Results for {results['language'].upper()}:")
        print(f"Syntax Valid: {'✅' if results['syntax_valid'] else '❌'}")
        
        if errors := results.get('syntax_errors', []):
            for error in errors:
                print(f"Syntax Error: {error}")
        
        if 'execution_success' in results:
            print(f"Execution Success: {'✅' if results['execution_success'] else '❌'}")
        
        if output := results.get('execution_output'):
            print(f"Output: {output}")
        
        if fixed := results.get('fixed_code'):
            print(f"\n🛠️  Fixed Code:")
            print(f"```{results['language']}")
            print(fixed)
            print("```")
            
            if results.get('fixed_code_valid'):
                print("✅ Fixed code syntax is valid")
            else:
                print("❌ Fixed code may still have issues")

# Standalone functions for easy import
def debug_code(code: str, language: str = None) -> Dict[str, any]:
    """Quick debug function for external use"""
    debugger = MultiLanguageDebugger()
    return debugger.debug_code(code, language)

def interactive_debugger():
    """Start interactive debugger"""
    debugger = MultiLanguageDebugger()
    debugger.interactive_debug()

def list_supported_debug_languages() -> List[str]:
    """List all supported debugging languages"""
    debugger = MultiLanguageDebugger()
    return debugger.list_supported_languages()

if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ultron import main as ultron_main

    sys.exit(ultron_main(["debugger"]))