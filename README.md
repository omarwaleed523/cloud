# Cloud Management System

A Python-based graphical user interface for managing QEMU virtual machines and disks.

## Features

- Create virtual disks with customizable type, size, and format
- List and manage created virtual disks
- Create virtual machines with configurable CPU, memory, and disk settings
- Start and run virtual machines
- Modern tabbed interface with user-friendly forms

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

This will open the graphical user interface with two tabs:

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

## Notes

- All virtual disks are stored in the `virtual_disks` directory
- Virtual machine configurations are saved in `virtual_machines.json`
- When starting a VM, QEMU will open in a new window