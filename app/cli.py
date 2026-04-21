import os
import sys

from app.services.automation_service import UltronAI

try:
    from content_generation import generate_content
    CONTENT_GEN_AVAILABLE = True
except ImportError:
    CONTENT_GEN_AVAILABLE = False

try:
    from app.agents.roles.code_debugger import interactive_debugger
    DEBUGGER_AVAILABLE = True
except ImportError:
    DEBUGGER_AVAILABLE = False


def create_env_template():
    """Create a template .env file if it doesn't exist"""
    env_file = '.env'
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write("# Ultron AI Configuration\n")
            f.write("GROQ_API_KEY=your_groq_api_key_here\n")
            f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")


def run_interactive_mode(ultron: UltronAI):
    """Run Ultron AI in interactive mode"""
    print("ULTRON AI Interactive Mode")
    print("commands:")
    print("  - 'generate code [language]: [prompt]' - Generate code")
    print("  - 'generate content [type]: [prompt]' - Generate content (blog, article, technical, creative)")
    print("  - 'execute: [task]' - Execute system task")

    if getattr(ultron, 'file_accessor', None):
        print("  - 'file [operation] [args]' - File operations")
        print("    Operations: create, read, delete, mkdir, rmdir, rename, move, copy, list, info, search, exists")
    if getattr(ultron, 'app_controller', None):
        print("  - 'app [operation] [args]' - Application control")
        print("    Operations: open, close, status, list")
    if DEBUGGER_AVAILABLE:
        print("  - 'debug: [language] [code]' - Debug code")
        print("  - 'debug interactive' - Start interactive debugger")
        print("  - 'debug languages' - List supported debug languages")
    print("  - 'exit' - Quit")

    while True:
        try:
            user_input = input("\nULTRON> ").strip()
                
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                break

            if user_input.startswith('generate code'):
                parts = user_input.split(':', 1)
                if len(parts) > 1:
                    language_prompt = parts[0].replace('generate code', '').strip()
                    prompt = parts[1].strip()
                    language = language_prompt if language_prompt else None
                    result = ultron.generate_code(prompt, language, save_to_file=True)
                    print(f"Generated {result['language'].upper()} code:")
                    print(result['code'])
                    if 'filepath' in result:
                        print(f"Saved to: {result['filepath']}")

            elif user_input.startswith('generate content'):
                if not CONTENT_GEN_AVAILABLE:
                    print("❌ Content generation not available.")
                    continue
                parts = user_input.split(':', 1)
                if len(parts) > 1:
                    type_prompt = parts[0].replace('generate content', '').strip()
                    prompt = parts[1].strip()
                    content_type = type_prompt if type_prompt else "article"
                    if content_type not in ["blog", "article", "technical", "creative"]:
                        print(f"❌ Invalid content type.")
                        continue
                    try:
                        result = generate_content(prompt, content_type=content_type)
                        if result and result.get("success"):
                            print(f"✅ Content generated successfully!\n📁 Saved to: {result['filepath']}")
                        else:
                            print("❌ Content generation failed.")
                    except Exception as e:
                        print(f"❌ Error generating content: {e}")

            elif user_input.startswith('debug'):
                if not DEBUGGER_AVAILABLE:
                    print("❌ Debugger not available.")
                    continue
                if user_input == 'debug interactive':
                    interactive_debugger()
                elif user_input == 'debug languages':
                    print("Supported debug languages:\n" + "\n".join(f"  - {l}" for l in ultron.list_debug_languages()))
                elif user_input.startswith('debug:'):
                    debug_parts = user_input.replace('debug:', '').strip().split(' ', 1)
                    if len(debug_parts) >= 2:
                        res = ultron.debug_code(debug_parts[1].strip(), debug_parts[0].strip())
                        print(f"Syntax Valid: {'✅' if res.get('syntax_valid', False) else '❌'}")
                        if res.get('fixed_code'):
                            print(f"\n🛠️  Fixed Code:\n```{res.get('language', '')}\n{res['fixed_code']}\n```")
                    else:
                        print("❌ Usage: debug: [language] [code]")

            elif user_input.startswith('execute:'):
                ultron.run_task(user_input.replace('execute:', '').strip())
                print("Task executed")

            elif user_input.startswith('file '):
                print(ultron.handle_file_command(user_input))

            elif user_input.startswith('app '):
                print(ultron.handle_app_command(user_input))

            else:
                print("Unknown command. Use 'generate code:', 'execute:', 'file', 'app', or 'debug'.")
            
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main entry point for ULTRON CLI"""
    create_env_template()
    try:
        ultron = UltronAI()
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            if mode == "execute" and len(sys.argv) > 2:
                ultron.run_task(' '.join(sys.argv[2:]))
                print("Task executed")
            elif mode == "generate" and len(sys.argv) > 2:
                res = ultron.generate_code(' '.join(sys.argv[2:]), save_to_file=True)
                print(f"Generated {res['language'].upper()} code:\n{res['code']}")
            elif mode == "languages":
                print("Supported programming Languages:\n" + "\n".join(f" - {l}" for l in ultron.list_supported_languages()))
            elif mode == "generate-content" and len(sys.argv) > 2:
                if CONTENT_GEN_AVAILABLE:
                    res = generate_content(' '.join(sys.argv[2:]))
                    if res and res.get("success"):
                        print(f"Content generated successfully.\n📁 File: {res['filepath']}")
            elif mode == "file" and len(sys.argv) > 2:
                print(ultron.handle_file_command(f"file {sys.argv[2]} {' '.join(sys.argv[3:])}"))
            elif mode == "app" and len(sys.argv) > 2:
                print(ultron.handle_app_command(f"app {sys.argv[2]} {' '.join(sys.argv[3:])}"))
            else:
                print("Usage:")
                print("  python -m app.cli execute 'your task'")
                print("  python -m app.cli generate 'your prompt'")
                print("  python -m app.cli generate-content 'your topic'")
                print("  python -m app.cli file [operation] [arguments...]")
                print("  python -m app.cli app [operation] [arguments...]")
        else:
            run_interactive_mode(ultron)
    except Exception as e:
        print(f"❌ Failed to initialize ULTRON AI: {e}")


if __name__ == "__main__":
    main()