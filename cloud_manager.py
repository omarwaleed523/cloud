#!/usr/bin/env python3
import os
import subprocess
import sys
import platform
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class CloudManager:
    def __init__(self):
        self.disks_dir = "virtual_disks"
        self.iso_dir = "iso_images"
        self.vms_file = "virtual_machines.json"
        self.virtual_machines = []
        
        # Create virtual disks and ISO directory if they don't exist
        if not os.path.exists(self.disks_dir):
            os.makedirs(self.disks_dir)
        if not os.path.exists(self.iso_dir):
            os.makedirs(self.iso_dir)
            
        # Load existing VMs if any
        if os.path.exists(self.vms_file):
            try:
                with open(self.vms_file, 'r') as f:
                    self.virtual_machines = json.load(f)
            except json.JSONDecodeError:
                self.virtual_machines = []
    
    def create_virtual_disk(self, disk_name, disk_format, disk_size):
        """Create a virtual disk with user-specified parameters"""
        # Create the disk
        disk_path = os.path.join(self.disks_dir, f"{disk_name}.{disk_format}")
        
        try:
            # Make sure the disk size has the right format
            if not disk_size[-1].upper() in ['G', 'M', 'K']:
                disk_size += 'G'  # Default to gigabytes
            
            # Ensure directory exists
            if not os.path.exists(self.disks_dir):
                os.makedirs(self.disks_dir)
                
            # Use absolute path
            disk_path_abs = os.path.abspath(disk_path)
            
            # Build command
            command = ["qemu-img", "create", "-f", disk_format, disk_path_abs, disk_size]
            print(f"Running command: {' '.join(command)}")
            
            # Execute command
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            return True, f"Success! Virtual disk created at: {disk_path}\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Error creating disk: {e}\nCommand output: {e.stderr}"
    
    def list_virtual_disks(self):
        """List all created virtual disks"""
        disks = []
        for i, filename in enumerate(os.listdir(self.disks_dir), 1):
            if os.path.isfile(os.path.join(self.disks_dir, filename)):
                disk_path = os.path.join(self.disks_dir, filename)
                size_bytes = os.path.getsize(disk_path)
                size_mb = size_bytes / (1024 * 1024)
                
                # Get actual disk info using qemu-img
                try:
                    result = subprocess.run(
                        ["qemu-img", "info", disk_path], 
                        check=True, 
                        capture_output=True, 
                        text=True
                    )
                    info = result.stdout
                    
                    # Extract format and virtual size information
                    format_info = "Unknown"
                    size_info = f"{size_mb:.2f} MB (physical)"
                    
                    for line in info.splitlines():
                        if "file format:" in line:
                            format_info = line.split("file format:")[1].strip()
                        if "virtual size:" in line:
                            size_info = line.split("virtual size:")[1].strip()
                    
                    disk_info = {
                        "index": i,
                        "name": filename,
                        "path": disk_path,
                        "format": format_info,
                        "size": size_info
                    }
                    disks.append(disk_info)
                    
                except subprocess.CalledProcessError:
                    disk_info = {
                        "index": i,
                        "name": filename,
                        "path": disk_path,
                        "format": "Unknown",
                        "size": f"{size_mb:.2f} MB"
                    }
                    disks.append(disk_info)
        
        return disks
    
    def create_virtual_machine(self, vm_name, cpu_cores, memory_size, disk_path, iso_path=None):
        """Create a virtual machine with user-specified parameters"""
        # Create VM configuration
        vm_config = {
            "name": vm_name,
            "cpu_cores": cpu_cores,
            "memory": memory_size,
            "disk": disk_path,
            "iso": iso_path
        }
        
        # Add the VM to our list and save it
        self.virtual_machines.append(vm_config)
        with open(self.vms_file, 'w') as f:
            json.dump(self.virtual_machines, f, indent=4)
        
        return True, f"Virtual Machine '{vm_name}' created successfully!"
    
    def start_virtual_machine(self, vm_index):
        """Start a virtual machine"""
        vm = self.virtual_machines[vm_index]
        
        # Convert memory size to MB for QEMU
        memory = vm['memory']
        if memory[-1].upper() == 'G':
            memory_mb = int(float(memory[:-1]) * 1024)
        else:  # Assume MB
            memory_mb = int(memory[:-1])
        
        # Ensure paths are absolute and use proper slashes for Windows
        disk_path = os.path.abspath(vm['disk']).replace('\\', '/')
        
        # Display the command that's about to be executed (for debugging)
        debug_info = f"Starting VM '{vm['name']}' with:\n"
        debug_info += f"- CPU: {vm['cpu_cores']} cores\n"
        debug_info += f"- Memory: {memory_mb}MB\n"
        debug_info += f"- Disk: {disk_path}\n"
        
        # Build the QEMU command with simpler parameters to avoid syntax issues
        qemu_cmd = [
            "qemu-system-x86_64",
            "-name", vm['name'],
            "-m", str(memory_mb),
            "-smp", str(vm['cpu_cores']),
        ]
        
        # Add the disk
        qemu_cmd.extend(["-hda", disk_path])
        
        # Add ISO if specified
        if vm.get('iso') and os.path.exists(vm['iso']):
            iso_path = os.path.abspath(vm['iso']).replace('\\', '/')
            qemu_cmd.extend(["-cdrom", iso_path])
            qemu_cmd.extend(["-boot", "d"])  # Boot from CDROM
            debug_info += f"- ISO: {iso_path}\n"
            debug_info += "- Boot order: CD-ROM, then Hard Disk\n"
        else:
            qemu_cmd.extend(["-boot", "c"])  # Boot from hard disk
            debug_info += "- Boot order: Hard Disk only\n"
        
        # Add some basic network settings
        qemu_cmd.extend([
            "-device", "e1000,netdev=net0",
            "-netdev", "user,id=net0"
        ])
        
        # Use software acceleration
        qemu_cmd.extend(["-accel", "tcg"])
        
        # Use SDL for display as it's more compatible
        qemu_cmd.append("-display")
        qemu_cmd.append("sdl")
        
        debug_info += f"Full command: {' '.join(qemu_cmd)}\n"
        print(debug_info)  # Print for debugging
        
        try:
            # Run QEMU in a new process without waiting
            if platform.system() == "Windows":
                # On Windows, create a new process with a new console window
                process = subprocess.Popen(
                    qemu_cmd, 
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Let's check if there's an immediate error
                try:
                    returncode = process.wait(timeout=1)
                    if returncode != 0:
                        stderr = process.stderr.read().decode('utf-8', errors='ignore')
                        return False, f"QEMU process exited with code {returncode}: {stderr}"
                except subprocess.TimeoutExpired:
                    # This is actually good - it means the process is still running
                    pass
            else:
                # On Unix-like systems, just create a new process
                process = subprocess.Popen(qemu_cmd)
            
            return True, f"VM '{vm['name']}' started successfully!\n{debug_info}"
        except Exception as e:
            return False, f"Error starting VM: {e}\n{debug_info}"

    def list_iso_files(self):
        """List all ISO files in the ISO directory"""
        iso_files = []
        
        # First check if there are any files in the iso_dir
        if os.path.exists(self.iso_dir):
            for filename in os.listdir(self.iso_dir):
                if filename.lower().endswith('.iso') and os.path.isfile(os.path.join(self.iso_dir, filename)):
                    file_path = os.path.join(self.iso_dir, filename)
                    size_bytes = os.path.getsize(file_path)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    iso_files.append({
                        "name": filename,
                        "path": file_path,
                        "size": f"{size_mb:.2f} MB"
                    })
        
        return iso_files
        
    def import_iso_file(self, source_path, dest_name=None):
        """Import an ISO file into the ISO directory"""
        if not os.path.exists(source_path):
            return False, f"File not found: {source_path}"
            
        if dest_name is None:
            dest_name = os.path.basename(source_path)
            
        dest_path = os.path.join(self.iso_dir, dest_name)
        
        try:
            # If source and destination are on the same filesystem, we can use os.rename which is faster
            # Otherwise, we need to copy and then delete
            try:
                os.rename(source_path, dest_path)
            except OSError:
                import shutil
                shutil.copy2(source_path, dest_path)
            
            return True, f"ISO file imported successfully to {dest_path}"
        except Exception as e:
            return False, f"Error importing ISO file: {e}"


class CloudManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cloud Management System")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # Create cloud manager backend
        self.cloud_manager = CloudManager()
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.disks_tab = ttk.Frame(self.notebook)
        self.vms_tab = ttk.Frame(self.notebook)
        self.iso_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.disks_tab, text="Virtual Disks")
        self.notebook.add(self.vms_tab, text="Virtual Machines")
        self.notebook.add(self.iso_tab, text="ISO Images")
        
        # Set up the disk tab
        self.setup_disks_tab()
        
        # Set up the VM tab
        self.setup_vms_tab()
        
        # Set up the ISO tab
        self.setup_iso_tab()
        
        # Status bar at the bottom
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Refresh the lists
        self.refresh_disk_list()
        self.refresh_vm_list()
        self.refresh_iso_list()
    
    def setup_disks_tab(self):
        # Split into left and right panes
        paned_window = ttk.PanedWindow(self.disks_tab, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left pane - disk list
        left_frame = ttk.LabelFrame(paned_window, text="Available Disks")
        paned_window.add(left_frame, weight=1)
        
        # Disk listbox with scrollbar
        self.disk_listbox_frame = ttk.Frame(left_frame)
        self.disk_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.disk_listbox = tk.Listbox(self.disk_listbox_frame, selectmode=tk.SINGLE)
        self.disk_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        disk_scrollbar = ttk.Scrollbar(self.disk_listbox_frame, orient=tk.VERTICAL, command=self.disk_listbox.yview)
        disk_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.disk_listbox.config(yscrollcommand=disk_scrollbar.set)
        
        # Button to refresh disk list
        refresh_button = ttk.Button(left_frame, text="Refresh List", command=self.refresh_disk_list)
        refresh_button.pack(fill=tk.X, padx=5, pady=5)
        
        # Right pane - create disk form
        right_frame = ttk.LabelFrame(paned_window, text="Create Virtual Disk")
        paned_window.add(right_frame, weight=1)
        
        # Form for creating a new disk
        ttk.Label(right_frame, text="Disk Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.disk_name_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.disk_name_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(right_frame, text="Disk Format:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.disk_format_var = tk.StringVar(value="qcow2")
        disk_format_combo = ttk.Combobox(right_frame, textvariable=self.disk_format_var, 
                                         values=["qcow2", "raw", "vdi", "vmdk"])
        disk_format_combo.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(right_frame, text="Disk Size:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        size_frame = ttk.Frame(right_frame)
        size_frame.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        self.disk_size_var = tk.StringVar(value="10")
        ttk.Entry(size_frame, textvariable=self.disk_size_var, width=10).pack(side=tk.LEFT)
        
        self.disk_size_unit_var = tk.StringVar(value="G")
        ttk.Combobox(size_frame, textvariable=self.disk_size_unit_var, values=["G", "M", "K"], width=3).pack(side=tk.LEFT, padx=5)
        
        # Create button
        create_disk_button = ttk.Button(right_frame, text="Create Disk", command=self.create_disk)
        create_disk_button.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # Configure the grid to expand properly
        right_frame.columnconfigure(1, weight=1)
    
    def setup_vms_tab(self):
        # Split into left and right panes
        paned_window = ttk.PanedWindow(self.vms_tab, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left pane - VM list
        left_frame = ttk.LabelFrame(paned_window, text="Available Virtual Machines")
        paned_window.add(left_frame, weight=1)
        
        # VM listbox with scrollbar
        self.vm_listbox_frame = ttk.Frame(left_frame)
        self.vm_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.vm_listbox = tk.Listbox(self.vm_listbox_frame, selectmode=tk.SINGLE)
        self.vm_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        vm_scrollbar = ttk.Scrollbar(self.vm_listbox_frame, orient=tk.VERTICAL, command=self.vm_listbox.yview)
        vm_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.vm_listbox.config(yscrollcommand=vm_scrollbar.set)
        
        # Buttons for VM actions
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        refresh_button = ttk.Button(button_frame, text="Refresh List", command=self.refresh_vm_list)
        refresh_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=5)
        
        start_button = ttk.Button(button_frame, text="Start VM", command=self.start_vm)
        start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=5)
        
        # Right pane - create VM form
        right_frame = ttk.LabelFrame(paned_window, text="Create Virtual Machine")
        paned_window.add(right_frame, weight=1)
        
        # Form for creating a new VM
        ttk.Label(right_frame, text="VM Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.vm_name_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.vm_name_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(right_frame, text="CPU Cores:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.cpu_cores_var = tk.StringVar(value="1")
        ttk.Spinbox(right_frame, from_=1, to=32, textvariable=self.cpu_cores_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(right_frame, text="Memory:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        memory_frame = ttk.Frame(right_frame)
        memory_frame.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        self.memory_size_var = tk.StringVar(value="1")
        ttk.Entry(memory_frame, textvariable=self.memory_size_var, width=10).pack(side=tk.LEFT)
        
        self.memory_unit_var = tk.StringVar(value="G")
        ttk.Combobox(memory_frame, textvariable=self.memory_unit_var, values=["G", "M"], width=3).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(right_frame, text="Virtual Disk:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.vm_disk_var = tk.StringVar()
        self.disk_combo = ttk.Combobox(right_frame, textvariable=self.vm_disk_var)
        self.disk_combo.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(right_frame, text="Boot ISO (optional):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.vm_iso_var = tk.StringVar()
        self.iso_combo = ttk.Combobox(right_frame, textvariable=self.vm_iso_var)
        self.iso_combo.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        self.iso_combo['values'] = ["[No ISO (Boot from disk)]"]
        
        # Create button
        create_vm_button = ttk.Button(right_frame, text="Create Virtual Machine", command=self.create_vm)
        create_vm_button.grid(row=5, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # Configure the grid to expand properly
        right_frame.columnconfigure(1, weight=1)
    
    def setup_iso_tab(self):
        """Set up the ISO tab interface"""
        # Split into left and right panes
        paned_window = ttk.PanedWindow(self.iso_tab, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left pane - ISO list
        left_frame = ttk.LabelFrame(paned_window, text="Available ISO Images")
        paned_window.add(left_frame, weight=1)
        
        # ISO listbox with scrollbar
        self.iso_listbox_frame = ttk.Frame(left_frame)
        self.iso_listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.iso_listbox = tk.Listbox(self.iso_listbox_frame, selectmode=tk.SINGLE)
        self.iso_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        iso_scrollbar = ttk.Scrollbar(self.iso_listbox_frame, orient=tk.VERTICAL, command=self.iso_listbox.yview)
        iso_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.iso_listbox.config(yscrollcommand=iso_scrollbar.set)
        
        # Button to refresh ISO list
        refresh_button = ttk.Button(left_frame, text="Refresh List", command=self.refresh_iso_list)
        refresh_button.pack(fill=tk.X, padx=5, pady=5)
        
        # Right pane - import ISO form
        right_frame = ttk.LabelFrame(paned_window, text="Import ISO Image")
        paned_window.add(right_frame, weight=1)
        
        # Form for importing an ISO file
        ttk.Label(right_frame, text="ISO Path:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        path_frame = ttk.Frame(right_frame)
        path_frame.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        self.iso_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.iso_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_button = ttk.Button(path_frame, text="Browse...", command=self.browse_iso)
        browse_button.pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(right_frame, text="Destination Name (optional):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.iso_dest_name_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.iso_dest_name_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Import button
        import_iso_button = ttk.Button(right_frame, text="Import ISO", command=self.import_iso)
        import_iso_button.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # Configure the grid to expand properly
        right_frame.columnconfigure(1, weight=1)
    
    def refresh_disk_list(self):
        # Clear the listbox
        self.disk_listbox.delete(0, tk.END)
        
        # Get the list of disks
        disks = self.cloud_manager.list_virtual_disks()
        
        # Update the disks combobox in VM tab
        disk_paths = [disk["path"] for disk in disks]
        disk_display = [f"{disk['name']} ({disk['format']}, {disk['size']})" for disk in disks]
        self.disk_combo['values'] = disk_display
        
        # Store disk paths for later use
        self.disk_paths = disk_paths
        
        # Add disks to the listbox
        for disk in disks:
            self.disk_listbox.insert(tk.END, f"{disk['name']} ({disk['format']}, {disk['size']})")
        
        # Update status
        if disks:
            self.status_var.set(f"Found {len(disks)} virtual disk(s)")
        else:
            self.status_var.set("No virtual disks found. Create one first.")
    
    def refresh_vm_list(self):
        # Clear the listbox
        self.vm_listbox.delete(0, tk.END)
        
        # Add VMs to the listbox
        for i, vm in enumerate(self.cloud_manager.virtual_machines):
            disk_name = os.path.basename(vm['disk'])
            self.vm_listbox.insert(tk.END, f"{vm['name']} (CPU: {vm['cpu_cores']} cores, Memory: {vm['memory']}, Disk: {disk_name})")
        
        # Update status
        if self.cloud_manager.virtual_machines:
            self.status_var.set(f"Found {len(self.cloud_manager.virtual_machines)} virtual machine(s)")
        else:
            self.status_var.set("No virtual machines found. Create one first.")
    
    def refresh_iso_list(self):
        """Refresh the list of ISO files"""
        # Clear the listbox
        self.iso_listbox.delete(0, tk.END)
        
        # Get the list of ISOs
        isos = self.cloud_manager.list_iso_files()
        
        # Update the ISO combobox in VM tab
        iso_paths = []
        iso_display = []
        
        for iso in isos:
            iso_paths.append(iso["path"])
            iso_display.append(f"{iso['name']} ({iso['size']})")
        
        if hasattr(self, 'iso_combo'):
            self.iso_combo['values'] = iso_display
            # Add an empty option
            if iso_display:
                self.iso_combo['values'] = ["[No ISO (Boot from disk)]"] + iso_display
            else:
                self.iso_combo['values'] = ["[No ISO (Boot from disk)]"]
        
        # Store ISO paths for later use
        self.iso_paths = iso_paths
        
        # Add ISOs to the listbox
        for iso in isos:
            self.iso_listbox.insert(tk.END, f"{iso['name']} ({iso['size']})")
        
        # Update status
        if isos:
            self.status_var.set(f"Found {len(isos)} ISO image(s)")
        else:
            self.status_var.set("No ISO images found. Import one first.")
    
    def create_disk(self):
        # Get values from form
        disk_name = self.disk_name_var.get().strip()
        disk_format = self.disk_format_var.get()
        disk_size = self.disk_size_var.get() + self.disk_size_unit_var.get()
        
        # Validate input
        if not disk_name:
            messagebox.showerror("Error", "Disk name cannot be empty")
            return
        
        # Create the disk
        success, message = self.cloud_manager.create_virtual_disk(disk_name, disk_format, disk_size)
        
        if success:
            messagebox.showinfo("Success", message)
            # Clear form
            self.disk_name_var.set("")
            # Refresh disk list
            self.refresh_disk_list()
        else:
            messagebox.showerror("Error", message)
    
    def create_vm(self):
        # Get values from form
        vm_name = self.vm_name_var.get().strip()
        try:
            cpu_cores = int(self.cpu_cores_var.get())
        except ValueError:
            messagebox.showerror("Error", "CPU cores must be a valid number")
            return
        
        memory_size = self.memory_size_var.get() + self.memory_unit_var.get()
        
        # Get selected disk
        try:
            disk_index = self.disk_combo.current()
            if disk_index < 0:
                messagebox.showerror("Error", "Please select a virtual disk")
                return
            disk_path = self.disk_paths[disk_index]
        except (IndexError, AttributeError):
            messagebox.showerror("Error", "No virtual disks available. Create one first.")
            return
        
        # Get selected ISO (optional)
        iso_path = None
        try:
            iso_index = self.iso_combo.current()
            if iso_index > 0:  # Skip the "No ISO" option (index 0)
                iso_path = self.iso_paths[iso_index - 1]
        except (IndexError, AttributeError):
            iso_path = None
            
        # Validate input
        if not vm_name:
            messagebox.showerror("Error", "VM name cannot be empty")
            return
            
        # Check if disk exists
        if not os.path.exists(disk_path):
            messagebox.showerror("Error", f"Disk file not found: {disk_path}\nPlease refresh the disk list and try again.")
            return
            
        # Check if ISO exists if specified
        if iso_path and not os.path.exists(iso_path):
            messagebox.showerror("Error", f"ISO file not found: {iso_path}\nPlease refresh the ISO list and try again.")
            return
        
        # Create the VM
        success, message = self.cloud_manager.create_virtual_machine(vm_name, cpu_cores, memory_size, disk_path, iso_path)
        
        if success:
            messagebox.showinfo("Success", message)
            # Clear form
            self.vm_name_var.set("")
            # Refresh VM list
            self.refresh_vm_list()
            
            # Ask if user wants to start the VM now
            start_now = messagebox.askyesno("Start VM", "Do you want to start this VM now?\n\nNote: If you selected an ISO, the VM will boot from it.\nIf no ISO was selected, you'll need to have an OS already installed on the disk.")
            if start_now:
                # Start the newly created VM (it's the last one in the list)
                vm_index = len(self.cloud_manager.virtual_machines) - 1
                success, message = self.cloud_manager.start_virtual_machine(vm_index)
                
                if success:
                    messagebox.showinfo("Success", message)
                else:
                    messagebox.showerror("Error", message)
        else:
            messagebox.showerror("Error", message)
    
    def start_vm(self):
        # Get selected VM
        selected_index = self.vm_listbox.curselection()
        if not selected_index:
            messagebox.showerror("Error", "Please select a virtual machine to start")
            return
        
        vm_index = selected_index[0]
        
        # Start the VM
        success, message = self.cloud_manager.start_virtual_machine(vm_index)
        
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
    
    def browse_iso(self):
        """Open a file dialog to choose an ISO file"""
        file_path = filedialog.askopenfilename(
            title="Select ISO Image",
            filetypes=[("ISO Images", "*.iso"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.iso_path_var.set(file_path)
            # Set default destination name (just the filename)
            self.iso_dest_name_var.set(os.path.basename(file_path))
    
    def import_iso(self):
        """Import an ISO file into the managed directory"""
        # Get values from form
        source_path = self.iso_path_var.get().strip()
        dest_name = self.iso_dest_name_var.get().strip()
        
        if not dest_name:
            dest_name = None
            
        # Validate input
        if not source_path:
            messagebox.showerror("Error", "Please select an ISO file to import")
            return
        
        # Import the ISO
        success, message = self.cloud_manager.import_iso_file(source_path, dest_name)
        
        if success:
            messagebox.showinfo("Success", message)
            # Clear form
            self.iso_path_var.set("")
            self.iso_dest_name_var.set("")
            # Refresh ISO list
            self.refresh_iso_list()
        else:
            messagebox.showerror("Error", message)


def main():
    root = tk.Tk()
    app = CloudManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()