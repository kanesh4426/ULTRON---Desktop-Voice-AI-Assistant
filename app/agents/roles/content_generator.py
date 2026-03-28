# ContentGenerator.py
import os
import re
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

class ContentGenerator:
    def __init__(self, api_key=None):
        """
        Initialize the Enhanced Content Generator
        
        Args:
            api_key (str, optional): Gemini API key. If None, loads from .env
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("No API key found. Please set GEMINI_API_KEY in .env or pass it directly")
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = self._initialize_model()
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Gemini API: {e}")
        
        # Enhanced generation configurations for different content types
        self.configurations = {
            "blog": {
                "temperature": 0.8,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 8192,
            },
            "article": {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 4096,
            },
            "technical": {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 20,
                "max_output_tokens": 6144,
            },
            "creative": {
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 4096,
            }
        }
        
        # Create output directory
        self.output_dir = self._create_output_directory()
        
        # Content quality guidelines
        self.quality_guidelines = """
        You are JARVIS, an advanced AI content creator. Follow these guidelines:
        1. Create well-structured, engaging content with proper headings
        2. Use appropriate emojis to enhance readability (not too many)
        3. Include relevant examples and practical insights
        4. Ensure factual accuracy and provide sources when possible
        5. Maintain consistent tone and style throughout
        6. Use proper formatting with sections, bullet points, and paragraphs
        7. Optimize for readability and user engagement
        8. Include a summary or key takeaways section
        """

    def _initialize_model(self):
        """Initialize the Gemini model with enhanced capabilities"""
        try:
            return genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                generation_config={
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                    "response_mime_type": "text/plain",
                }
            )
        except Exception as e:
            raise RuntimeError(f"Model initialization failed: {e}")

    def _create_output_directory(self):
        """Create content directory with organized subfolders"""
        base_dir = os.path.join("data", "content")
        subdirs = ["blogs", "articles", "technical", "creative", "other"]
        
        os.makedirs(base_dir, exist_ok=True)
        for subdir in subdirs:
            os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
        
        return base_dir

    def _generate_filename(self, prompt, content_type="article"):
        """Generate a unique, descriptive filename"""
        # Clean the prompt to create filename
        clean_name = re.sub(r'[^\w\s-]', '', prompt[:50])
        clean_name = clean_name.strip().replace(' ', '_')
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{content_type}_{clean_name}_{timestamp}.txt"

    def _validate_content_quality(self, content, min_length=200):
        """
        Basic content quality validation
        
        Args:
            content (str): Generated content to validate
            min_length (int): Minimum acceptable content length
            
        Returns:
            tuple: (is_valid, issues)
        """
        issues = []
        
        # Check length
        if len(content.strip()) < min_length:
            issues.append(f"Content too short ({len(content)} characters)")
        
        # Check structure (basic heuristics)
        lines = content.split('\n')
        heading_count = sum(1 for line in lines if line.strip().startswith('#') or 
                          (len(line.strip()) > 0 and line.strip()[0].isupper() and 
                           len(line.strip()) < 100 and not line.strip().endswith('.') and 
                           not line.strip().endswith(':')))
        
        if heading_count < 2:
            issues.append("Insufficient structure (few headings/sections)")
        
        # Check for excessive emojis
        emoji_count = sum(1 for char in content if char in "😀😃😄😁😆😅😂🤣☺️😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😶😱😨😰😥😓🤑🤠")
        if emoji_count > 20:  # Arbitrary threshold
            issues.append("Too many emojis")
        
        return len(issues) == 0, issues

    def _enhance_prompt(self, prompt, content_type="article"):
        """Enhance the user prompt with specific instructions"""
        enhanced_prompt = f"""
        CONTENT TYPE: {content_type.upper()}
        USER REQUEST: {prompt}
        
        {self.quality_guidelines}
        
        Please create comprehensive, well-structured content that addresses the user's request.
        Include appropriate sections, examples, and ensure the content is engaging and informative.
        """
        
        return enhanced_prompt

    def generate_content(self, prompt, content_type="article", custom_config=None, 
                       min_quality_standard=True, retry_count=2):
        """
        Generate high-quality content with validation and retry mechanism
        
        Args:
            prompt (str): Content generation prompt
            content_type (str): Type of content (blog, article, technical, creative)
            custom_config (dict, optional): Custom generation configuration
            min_quality_standard (bool): Whether to enforce quality standards
            retry_count (int): Number of retries if quality check fails
            
        Returns:
            dict: Result with content, metadata, and quality info
        """
        # Validate content type
        if content_type not in self.configurations:
            content_type = "article"
            print(f"Warning: Unknown content type. Using 'article' instead.")
        
        # Merge configurations
        config = {**self.configurations[content_type], **(custom_config or {})}
        
        # Enhance prompt
        enhanced_prompt = self._enhance_prompt(prompt, content_type)
        
        for attempt in range(retry_count + 1):
            try:
                # Initialize model with current config
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash-exp",
                    generation_config=config,
                    system_instruction=self.quality_guidelines
                )

                # Generate content
                response = model.generate_content(enhanced_prompt)
                content = response.text
                
                # Validate quality if required
                if min_quality_standard:
                    is_valid, issues = self._validate_content_quality(content)
                    if not is_valid and attempt < retry_count:
                        print(f"Quality check failed (attempt {attempt + 1}/{retry_count + 1}): {issues}")
                        continue
                
                # Generate filename and save
                filename = self._generate_filename(prompt, content_type)
                folder_map = {
                    "blog": "blogs",
                    "article": "articles",
                    "technical": "technical",
                    "creative": "creative",
                }
                subfolder = folder_map.get(content_type, "other")
                filepath = os.path.join(self.output_dir, subfolder, filename)
                
                # Save with metadata
                metadata = f"Generated: {datetime.now().isoformat()}\nPrompt: {prompt}\nType: {content_type}\n\n"
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(metadata)
                    file.write(content)
                
                # Open file if desired
                self._open_file(filepath)
                
                return {
                    "success": True,
                    "content": content,
                    "filepath": filepath,
                    "content_type": content_type,
                    "quality_issues": issues if min_quality_standard else [],
                    "attempts": attempt + 1
                }
                
            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == retry_count:
                    return {
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1
                    }

    def batch_generate(self, prompts, content_type="article", **kwargs):
        """Generate multiple pieces of content"""
        results = []
        for i, prompt in enumerate(prompts):
            print(f"Generating content {i+1}/{len(prompts)}: {prompt[:50]}...")
            result = self.generate_content(prompt, content_type, **kwargs)
            results.append(result)
        return results

    def _open_file(self, filepath):
        """Open file in default text editor with cross-platform support"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            elif os.name == 'posix':  # macOS and Linux
                if sys.platform == 'darwin':  # macOS
                    subprocess.call(('open', filepath))
                else:  # Linux
                    subprocess.call(('xdg-open', filepath))
        except Exception as e:
            print(f"Note: Could not open file automatically: {e}")
            print(f"Content saved to: {filepath}")

# Helper function for easy usage
def generate_content(topic, content_type="article"):
    """Convenience function for content generation"""
    try:
        generator = ContentGenerator()
        result = generator.generate_content(
            topic, 
            content_type=content_type,
            min_quality_standard=True,
            retry_count=2
        )
        
        if result['success']:
            print("✅ Content generated successfully!")
            print(f"📁 Saved to: {result['filepath']}")
            if result['quality_issues']:
                print("⚠️  Quality notes:", result['quality_issues'])
            return result['content']
        else:
            print("❌ Content generation failed:", result['error'])
            return None
    except Exception as e:
        print(f"❌ Content generator initialization failed: {e}")
        return None
