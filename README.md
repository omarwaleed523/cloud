# Cloud Management System

A Python-based graphical user interface for managing QEMU virtual machines and disks.

## Features

- Create virtual disks with customizable type, size, and format
- Import and manage ISO images for OS installation
- Create virtual machines with configurable CPU, memory, and disk settings
- Start and run virtual machines with proper boot options
- Modern tabbed interface with user-friendly forms

## Current Setup

This project has the following components:
- `cloud_manager.py`: Main application file
- `virtual_disks/`: Directory for VM disk images
- `iso_images/`: Directory for OS installation ISO files
- `virtual_machines.json`: Configuration file for virtual machines

## Prerequisites

- QEMU (must be installed and available in PATH)
- Python 3.6+
- Tkinter (included with most Python installations)

## Installation

1. Ensure QEMU is installed on your system.
2. Place the `cloud_manager.py` script in your desired directory.
3. Make the script executable (Linux/macOS only):
   ```
   chmod +x cloud_manager.py
   ```

## Usage

Run the script:

```
python cloud_manager.py
```

This will open the graphical user interface with three tabs:

### Virtual Disks Tab
- Left side: List of all created virtual disks
- Right side: Form to create new virtual disks
  - Specify disk name
  - Select disk format (qcow2, raw, vdi, vmdk)
  - Set disk size (with G, M, or K units)

### Virtual Machines Tab
- Left side: List of all created virtual machines with a button to start them
- Right side: Form to create new virtual machines
  - Specify VM name
  - Set CPU cores
  - Configure memory size
  - Select a previously created virtual disk to use
  - Optionally select an ISO image to boot from

### ISO Images Tab
- Left side: List of all available ISO images
- Right side: Form to import new ISO images
  - Browse to select an ISO file
  - Optionally rename the ISO file for storage

## Complete Workflow

1. **Create a Virtual Disk**:
   - Go to the "Virtual Disks" tab
   - Enter a name, select a format (qcow2 recommended), and set a size
   - Click "Create Disk"

2. **Import an ISO Image**:
   - Go to the "ISO Images" tab
   - Click "Browse..." to select an OS installation ISO
   - Click "Import ISO"

3. **Create a Virtual Machine**:
   - Go to the "Virtual Machines" tab
   - Fill in the VM details (name, CPU, memory)
   - Select the disk you created
   - Select the ISO you imported
   - Click "Create Virtual Machine"

4. **Start the Virtual Machine**:
   - When prompted after VM creation, choose to start the VM
   - Or select a VM from the list and click "Start VM"
   - The VM will boot from the ISO, allowing you to install the operating system

## Notes

- All virtual disks are stored in the `virtual_disks` directory
- ISO images are stored in the `iso_images` directory
- Virtual machine configurations are saved in `virtual_machines.json`
- When starting a VM, QEMU will open in a new window