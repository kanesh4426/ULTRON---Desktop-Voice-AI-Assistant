import os
import re
import datetime
from typing import Optional, Dict, Any
from openai import OpenAI

class CodeGenerator:
    """
    AI-Powered Multi-Language Code Generator
    Handles code generation for various programming languages using Groq API.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Code Generator
        
        Args:
            api_key (str): Groq API key for code generation
        """
        self.code_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        self.setup_code_generation_context()
        
    def setup_code_generation_context(self):
        """Setup the conversation context for code generation"""
        self.messages = [
            {
                "role": "system", 
                "content": """You are an expert code generator that writes high-quality code in multiple programming languages.

SUPPORTED LANGUAGES:
- Python (primary for automation)
- JavaScript/Node.js
- Java
- C++
- C#
- PHP
- Ruby
- Go
- Rust
- SQL
- HTML/CSS
- TypeScript
- Bash/Shell scripting

GUIDELINES:
1. Always use the appropriate code block markers (```python, ```javascript, ```java, etc.)
2. Include necessary imports/requires/dependencies
3. Add brief comments for clarity and documentation
4. Ensure the code is functional, efficient, and follows best practices
5. For system automation tasks, prefer Python
6. Include example usage when appropriate
7. Validate input parameters and handle errors
"""
            },
            {
                "role": "system", 
                "content": "IMPORTANT: When asked to write code, always specify the programming language using correct code block format. If no language is specified, default to Python."
            },
            # Examples for different languages
            {
                "role": "user", 
                "content": "Write a Python function to calculate factorial"
            },
            {
                "role": "assistant", 
                "content": "```python\ndef factorial(n):\n    \"\"\"Calculate factorial of a number\"\"\"\n    if n == 0 or n == 1:\n        return 1\n    return n * factorial(n - 1)\n\n# Example usage\nprint(factorial(5))  # Output: 120\n```"
            },
            {
                "role": "user", 
                "content": "Create a JavaScript class for a Car with make, model, and year"
            },
            {
                "role": "assistant", 
                "content": "```javascript\nclass Car {\n    constructor(make, model, year) {\n        this.make = make;\n        this.model = model;\n        this.year = year;\n    }\n    \n    getInfo() {\n        return `${this.year} ${this.make} ${this.model}`;\n    }\n    \n    // Example usage\n    // const myCar = new Car('Toyota', 'Camry', 2023);\n    // console.log(myCar.getInfo());\n}\n```"
            }
        ]
    
    def generate_code(self, prompt: str, language: str = None) -> Dict[str, str]:
        """
        Generate code based on the given prompt
        
        Args:
            prompt (str): Code generation prompt
            language (str, optional): Specific language to generate code for
            
        Returns:
            Dict: Contains 'code', 'language', and 'full_response'
        """
        try:
            # Add language hint if specified
            user_prompt = prompt
            if language:
                user_prompt = f"Write {language} code for: {prompt}"
            
            response = self.code_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.messages + [{"role": "user", "content": user_prompt}],
                max_tokens=2000,
                temperature=0.7,
                top_p=0.9
            )
            
            full_response = response.choices[0].message.content.strip()
            code_info = self.extract_code_from_response(full_response)
            
            return {
                'code': code_info['code'] if code_info else full_response,
                'language': code_info['language'] if code_info else 'text',
                'full_response': full_response
            }
            
        except Exception as e:
            return {
                'code': f"// Error generating code: {str(e)}",
                'language': 'text',
                'full_response': f"Error: {str(e)}"
            }
    
    def extract_code_from_response(self, response: str) -> Optional[Dict[str, str]]:
        """
        Extract code and language from API response
        
        Args:
            response (str): API response containing code blocks
            
        Returns:
            Optional[Dict]: Dictionary with 'code' and 'language'
        """
        if not response:
            return None
            
        # Pattern to match code blocks with language specification
        code_block_pattern = r'```(\w+)\n(.*?)\n```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            language, code = matches[0]
            return {
                'language': language.lower().strip(),
                'code': code.strip()
            }
        
        # Fallback for generic code blocks
        generic_pattern = r'```\n(.*?)\n```'
        generic_matches = re.findall(generic_pattern, response, re.DOTALL)
        
        if generic_matches:
            return {
                'language': 'python',
                'code': generic_matches[0].strip()
            }
                
        return None
    
    def save_code_to_file(self, code: str, language: str, filename: str = None) -> str:
        """
        Save generated code to appropriate file with proper extension
        
        Args:
            code (str): The generated code
            language (str): Programming language
            filename (str, optional): Custom filename
            
        Returns:
            str: Path to the saved file
        """
        # Map languages to file extensions
        extensions = {
            'python': '.py',
            'javascript': '.js',
            'java': '.java',
            'cpp': '.cpp',
            'c++': '.cpp',
            'csharp': '.cs',
            'c#': '.cs',
            'php': '.php',
            'ruby': '.rb',
            'go': '.go',
            'rust': '.rs',
            'sql': '.sql',
            'html': '.html',
            'css': '.css',
            'typescript': '.ts',
            'bash': '.sh',
            'shell': '.sh'
        }
        
        extension = extensions.get(language, '.txt')
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_code_{timestamp}{extension}"
        
        os.makedirs("data/generated_code", exist_ok=True)
        filepath = os.path.join("data/generated_code", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return filepath

    def list_supported_languages(self) -> list:
        """Get list of supported programming languages"""
        return ['python', 'javascript', 'java', 'cpp', 'csharp', 'php', 
                'ruby', 'go', 'rust', 'sql', 'html', 'css', 'typescript', 
                'bash', 'shell']
