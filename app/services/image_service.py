import os
import sys
import time
from datetime import datetime
import threading
try:
    import pollinations
except ImportError:
    print("pollinations library not found. Please install it using: pip install pollinations")
    sys.exit(1)

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class ImageGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Image Generator")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Variables
        self.prompt_text = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready")
        self.progress_value = tk.DoubleVar()
        self.image_path = "Database/Image.png"
        self.generated_image = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Prompt label and entry
        ttk.Label(main_frame, text="Prompt:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        prompt_entry = ttk.Entry(main_frame, textvariable=self.prompt_text, width=50)
        prompt_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(5, 0))
        
        # Negative prompt label and entry (with default value)
        ttk.Label(main_frame, text="Negative Prompt:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.negative_prompt = tk.StringVar(value="Anime, cartoony, childish, low quality, blurry, bad anatomy, bad hands, text, watermark")
        negative_entry = ttk.Entry(main_frame, textvariable=self.negative_prompt, width=50)
        negative_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(5, 0))
        
        # Options frame
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(options_frame, text="Width:").grid(row=0, column=0, padx=(0, 5))
        self.width_var = tk.IntVar(value=1024)
        ttk.Spinbox(options_frame, from_=256, to=2048, increment=64, textvariable=self.width_var, width=8).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(options_frame, text="Height:").grid(row=0, column=2, padx=(0, 5))
        self.height_var = tk.IntVar(value=1024)
        ttk.Spinbox(options_frame, from_=256, to=2048, increment=64, textvariable=self.height_var, width=8).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(options_frame, text="Seed:").grid(row=0, column=4, padx=(0, 5))
        self.seed_var = tk.IntVar(value=0)
        ttk.Spinbox(options_frame, from_=0, to=999999, textvariable=self.seed_var, width=8).grid(row=0, column=5, padx=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        generate_btn = ttk.Button(buttons_frame, text="Generate Image", command=self.generate_image)
        generate_btn.grid(row=0, column=0, padx=(0, 5))
        
        open_btn = ttk.Button(buttons_frame, text="Open Image", command=self.open_image)
        open_btn.grid(row=0, column=1, padx=5)
        
        save_btn = ttk.Button(buttons_frame, text="Save As...", command=self.save_image)
        save_btn.grid(row=0, column=2, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, variable=self.progress_value, maximum=100)
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Status label
        status_label = ttk.Label(main_frame, textvariable=self.status_text)
        status_label.grid(row=5, column=0, columnspan=2, sticky=tk.W)
        
        # Image display
        self.image_label = ttk.Label(main_frame, text="Image will be displayed here")
        self.image_label.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        # Bind Enter key to generate image
        prompt_entry.bind('<Return>', lambda e: self.generate_image())
        
    def generate_image(self):
        prompt = self.prompt_text.get().strip()
        if not prompt:
            messagebox.showerror("Error", "Please enter a prompt")
            return
        
        # Start generation in a separate thread to avoid UI freezing
        thread = threading.Thread(target=self._generate_image_thread, args=(prompt,))
        thread.daemon = True
        thread.start()
    
    def _generate_image_thread(self, prompt):
        self.status_text.set("Generating image...")
        self.progress_value.set(10)
        
        try:
            os.makedirs("data/images", exist_ok=True)
            
            # Create a timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.image_path = f"data/images/Image_{timestamp}.png"
            
            image_model = pollinations.image(
                model="flux-cablyai",
                seed=self.seed_var.get(),
                width=self.width_var.get(),
                height=self.height_var.get(),
                enhance=False,
                nologo=False,
                private=False,
            )

            self.progress_value.set(30)
            
            image_model.generate(
                prompt=prompt,
                negative=self.negative_prompt.get(),
                save=True,
                file=self.image_path,
            )
            
            self.progress_value.set(90)
            
            # Update UI in the main thread
            self.root.after(0, self._on_generation_success)
            
        except Exception as e:
            self.root.after(0, lambda: self._on_generation_error(str(e)))
    
    def _on_generation_success(self):
        self.progress_value.set(100)
        self.status_text.set("Image generated successfully")
        self.display_image()
        messagebox.showinfo("Success", "Image generated successfully!")
    
    def _on_generation_error(self, error_msg):
        self.progress_value.set(0)
        self.status_text.set(f"Error: {error_msg}")
        messagebox.showerror("Error", f"Failed to generate image: {error_msg}")
    
    def display_image(self):
        if os.path.exists(self.image_path):
            try:
                image = Image.open(self.image_path)
                # Resize for display while maintaining aspect ratio
                max_size = (400, 400)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(image)
                self.image_label.configure(image=photo)
                self.image_label.image = photo  # Keep a reference
                
                self.generated_image = Image.open(self.image_path)
            except Exception as e:
                self.image_label.configure(text=f"Failed to display image: {e}")
        else:
            self.image_label.configure(text="Image file does not exist")
    
    def open_image(self):
        if os.path.exists(self.image_path):
            try:
                image = Image.open(self.image_path)
                image.show()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open image: {e}")
        else:
            messagebox.showwarning("Warning", "No image has been generated yet")
    
    def save_image(self):
        if self.generated_image:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            if file_path:
                try:
                    self.generated_image.save(file_path)
                    messagebox.showinfo("Success", f"Image saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save image: {e}")
        else:
            messagebox.showwarning("Warning", "No image to save")

def main():
    root = tk.Tk()
    app = ImageGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ultron import main as ultron_main

    sys.exit(ultron_main(["image-ui"]))
