import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import minecraft_launcher_lib
import subprocess
import os
import json
import uuid
import threading

class MinecraftCrackedClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Cracked Client")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Minecraft directory
        self.minecraft_dir = minecraft_launcher_lib.utils.get_minecraft_directory()
        
        # Setup variables
        self.versions = []
        self.selected_version = tk.StringVar()
        self.username = tk.StringVar(value="Player")
        self.setup_done = False
        
        self.setup_ui()
        self.check_setup()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Minecraft Cracked Client", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Username input
        username_frame = ttk.Frame(main_frame)
        username_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(username_frame, text="Username:").pack(side=tk.LEFT)
        username_entry = ttk.Entry(username_frame, textvariable=self.username)
        username_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Version selection
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(version_frame, text="Version:").pack(side=tk.LEFT)
        self.version_combo = ttk.Combobox(version_frame, textvariable=self.selected_version)
        self.version_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        self.setup_btn = ttk.Button(button_frame, text="Setup Minecraft", 
                                   command=self.setup_minecraft)
        self.setup_btn.pack(side=tk.LEFT, padx=5)
        
        self.launch_btn = ttk.Button(button_frame, text="Launch Minecraft", 
                                    command=self.launch_minecraft, state=tk.DISABLED)
        self.launch_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=10)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack()
    
    def check_setup(self):
        # Check if Minecraft is already set up
        if os.path.exists(self.minecraft_dir):
            self.load_versions()
        else:
            self.status_label.config(text="Minecraft directory not found. Click Setup Minecraft.")
    
    def load_versions(self):
        try:
            self.versions = minecraft_launcher_lib.utils.get_available_versions(self.minecraft_dir)
            version_list = [v["id"] for v in self.versions if v["type"] == "release"]
            self.version_combo["values"] = version_list
            if version_list:
                self.selected_version.set(version_list[0])
                self.launch_btn.config(state=tk.NORMAL)
                self.setup_done = True
                self.status_label.config(text="Ready to play!")
        except Exception as e:
            self.status_label.config(text=f"Error loading versions: {str(e)}")
    
    def setup_minecraft(self):
        threading.Thread(target=self._setup_minecraft_thread).start()
    
    def _setup_minecraft_thread(self):
        try:
            self.setup_btn.config(state=tk.DISABLED)
            self.progress.start()
            self.status_label.config(text="Setting up Minecraft...")
            
            # Create Minecraft directory if it doesn't exist
            if not os.path.exists(self.minecraft_dir):
                os.makedirs(self.minecraft_dir)
            
            # Get latest version
            version_list = minecraft_launcher_lib.utils.get_version_list()
            latest_version = None
            
            for version in version_list:
                if version["type"] == "release":
                    latest_version = version["id"]
                    break
            
            if not latest_version:
                raise Exception("No release version found")
            
            self.status_label.config(text=f"Downloading Minecraft {latest_version}...")
            
            # Install Minecraft
            minecraft_launcher_lib.install.install_minecraft_version(
                latest_version, self.minecraft_dir
            )
            
            self.status_label.config(text="Download complete!")
            self.load_versions()
            
        except Exception as e:
            messagebox.showerror("Error", f"Setup failed: {str(e)}")
            self.status_label.config(text=f"Setup failed: {str(e)}")
        finally:
            self.progress.stop()
            self.setup_btn.config(state=tk.NORMAL)
    
    def launch_minecraft(self):
        if not self.setup_done:
            messagebox.showerror("Error", "Please setup Minecraft first")
            return
        
        threading.Thread(target=self._launch_minecraft_thread).start()
    
    def _launch_minecraft_thread(self):
        try:
            self.launch_btn.config(state=tk.DISABLED)
            self.progress.start()
            self.status_label.config(text="Launching Minecraft...")
            
            version = self.selected_version.get()
            username = self.username.get()
            
            # Generate a persistent UUID for cracked mode :cite[1]
            player_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, username))
            
            # Launch options
            options = {
                "username": username,
                "uuid": player_uuid,
                "token": ""
            }
            
            # Get launch command
            command = minecraft_launcher_lib.command.get_minecraft_command(
                version, self.minecraft_dir, options
            )
            
            self.status_label.config(text="Starting game...")
            
            # Launch game
            subprocess.Popen(command)
            
            self.status_label.config(text="Game started!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Launch failed: {str(e)}")
            self.status_label.config(text=f"Launch failed: {str(e)}")
        finally:
            self.progress.stop()
            self.launch_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftCrackedClient(root)
    root.mainloop()
