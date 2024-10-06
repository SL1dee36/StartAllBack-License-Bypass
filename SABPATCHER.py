import subprocess
import winreg
import shutil
import os
import sys
import ctypes  # Unused import
import stat
import re
import requests
import zipfile

# Settings
app_target_dll = "StartAllBackX64.dll"
app_target_exe = "StartAllBackCfg.exe"

HANDLE_URL = "https://download.sysinternals.com/files/Handle.zip"
HANDLE_EXE = "handle.exe"

def find_dll(dll_name):
    """Searches for the DLL in common installation directories."""
    paths = [
        os.path.join(os.environ.get("LOCALAPPDATA"), "StartAllBack", dll_name),
        os.path.join(os.environ.get("ProgramFiles"), "StartAllBack", dll_name),
        os.path.join(os.environ.get("ProgramFiles(x86)"), "StartAllBack", dll_name),
        os.path.join(os.path.dirname(sys.executable), "StartAllBack", dll_name),
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def patch_dll(dll_path):
    """Patches the DLL by replacing a specific byte sequence."""
    backup_path = dll_path + ".bak"
    try:
        shutil.copy2(dll_path, backup_path)
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Error creating backup: {e}")
        return False

    try:
        with open(dll_path, "r+b") as f:
            data = f.read()
            old_bytes = bytes.fromhex("48 89 5C 24 08 55 56 57 48 8D AC 24 70 FF FF FF")
            new_bytes = bytes.fromhex("67 C7 01 01 00 00 00 B8 01 00 00 00 C3 90 90 90")
            index = data.find(old_bytes)
            if index != -1:
                f.seek(index)
                f.write(new_bytes)
                return True
            else:
                print("Hex sequence not found!")
                return False
    except (PermissionError, OSError) as e:
        print(f"Patching error due to insufficient permissions: {e}")
        return False
    except Exception as e:
        print(f"Unexpected patching error: {e}")
        return False

def kill_process(process_name):
    """Terminates a process by name."""
    try:
        result = subprocess.run(["taskkill", "/f", "/im", process_name], capture_output=True, text=True, encoding='cp866', errors='ignore')
        if result.returncode == 0:
            print(f"Success: Process \"{process_name}\" terminated.")
            return True
        elif result.returncode == 128:  # Process not found
            print(f"Process {process_name} not found.")
            return True
        else:
            print(f"Error terminating process {process_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error terminating process {process_name}: {e}")
        return False

def set_registry_value(key_path, value_name, value):
    """Sets a DWORD value in the registry."""
    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
            print(f"Success: Registry value \"{value_name}\" set.")
            return True
    except Exception as e:
        print(f"Registry error: {e}")
        return False

def grant_full_access(filepath):
    """Grants full access permissions to a file."""
    try:
        os.chmod(filepath, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        print(f"Successfully changed permissions for {filepath}.")
        return True
    except OSError as e:
        print(f"Error changing permissions for {filepath}: {e}")
        return False


def download_handle(destination_folder):
    """Downloads and extracts handle.exe from Sysinternals."""
    handle_path = os.path.join(destination_folder, HANDLE_EXE)
    if os.path.exists(handle_path):
        return handle_path

    try:
        print("Downloading handle.exe...")
        response = requests.get(HANDLE_URL, stream=True)
        response.raise_for_status()

        zip_path = os.path.join(destination_folder, "handle.zip")
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination_folder)

        os.remove(zip_path)
        print(f"handle.exe successfully downloaded to {destination_folder}")
        return handle_path

    except requests.exceptions.RequestException as e:
        print(f"Error downloading handle.exe: {e}")
        return None
    except zipfile.BadZipFile as e:
        print(f"Error extracting handle.zip: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def close_handles(dll_path, handle_path):
    """Closes open handles to the DLL file."""
    try:
        output = subprocess.check_output([handle_path, dll_path], text=True, stderr=subprocess.STDOUT)
        lines = output.splitlines()[1:]  # Skip the header line

        for line in lines:
            match = re.match(r"\s*(\d+):.*pid: (\d+)", line)
            if match:
                handle_value = int(match.group(1), 16)
                process_id = int(match.group(2))

                try:
                    subprocess.run(["handle.exe", "-c", hex(handle_value), "-p", str(process_id), "-y"], check=True, capture_output=True, text=True)
                    print(f"Handle {handle_value} in process {process_id} closed successfully.")
                except subprocess.CalledProcessError as e:
                    print(f"Error closing handle {handle_value} in process {process_id}: {e.stdout} {e.stderr}")
                    return False

        return True

    except FileNotFoundError:
        print("handle.exe not found. Ensure the Sysinternals handle.exe utility is in your PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error executing handle.exe: {e.stdout} {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False



if __name__ == "__main__":
    dll_path = find_dll(app_target_dll)
    if dll_path:
        print(f"File found: {dll_path}")

        handle_path = download_handle(os.getcwd())
        if not handle_path:
            print("Failed to download handle.exe. Exiting.")
            sys.exit(1)

        if not grant_full_access(dll_path):
            sys.exit(1)

        if close_handles(dll_path, handle_path):
            kill_process(app_target_exe)
            kill_process("explorer.exe")

            set_registry_value(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "AutoRestartShell", 0)

            if patch_dll(dll_path):
                print("Patch applied successfully!")
                exe_path = os.path.join(os.path.dirname(dll_path), app_target_exe)
                if os.path.exists(exe_path):
                    try:
                        subprocess.Popen(exe_path)  # Non-blocking execution
                    except Exception as e:
                        print(f"Error launching {exe_path}: {e}")

            subprocess.run(["explorer.exe"])  # Restart explorer
            set_registry_value(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "AutoRestartShell", 1)

    else:
        print("StartAllBackX64.dll not found!")