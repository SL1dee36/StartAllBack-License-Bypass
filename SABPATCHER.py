import subprocess
import winreg
import shutil
import os
import sys
import stat

# Settings
app_target_dll = "StartAllBackX64.dll"
app_target_exe = "StartAllBackCfg.exe"

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

    # 1. Clear the Read-Only attribute if it's set
    try:
        os.chmod(dll_path, stat.S_IWRITE)
    except Exception:
        pass

    try:
        # 2. Classic Windows file-lock bypass:
        # We rename the original file (Windows allows renaming locked DLLs).
        # Then we copy it back to get a fresh, unlocked file to modify.
        if os.path.exists(backup_path):
            try:
                os.chmod(backup_path, stat.S_IWRITE)
                os.remove(backup_path)
            except Exception:
                pass

        os.rename(dll_path, backup_path)
        shutil.copy2(backup_path, dll_path)
        
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Error preparing file for patching (File lock bypass failed): {e}")
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
                print("Hex sequence not found! The file might already be patched.")
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


if __name__ == "__main__":
    dll_path = find_dll(app_target_dll)
    if dll_path:
        print(f"File found: {dll_path}")

        kill_process(app_target_exe)
        kill_process("explorer.exe")
        kill_process("ShellHost.exe")

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
