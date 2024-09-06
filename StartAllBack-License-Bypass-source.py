import winreg
import random
import time
import ctypes
import sys

def modify_registry_key():
    try:
        # Open the registry key
        reg_path = r'Software\Microsoft\Windows\CurrentVersion\Explorer\CLSID'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_ALL_ACCESS) as clsid_key:
            # Iterate through all keys in CLSID
            index = 0
            while True:
                try:
                    key_name = winreg.EnumKey(clsid_key, index)
                    # Open the key to check for subkeys
                    with winreg.OpenKey(clsid_key, key_name, 0, winreg.KEY_ALL_ACCESS) as sub_key:
                        # Check the number of subkeys
                        num_subkeys = winreg.QueryInfoKey(sub_key)[0]
                        # If the key has no subkeys, modify the date
                        if num_subkeys == 0:
                            # Modify the last modification date
                            winreg.SetValueEx(sub_key, "StartAllBack-License-Bypass", 0, winreg.REG_DWORD, int(time.time()))
                            print(f"Key '{key_name}' updated.")
                            input('Exiting the loop, if there are no more keys to enumerate')
                            break  # Exit after the first key found
                    index += 1
                except WindowsError:
                    # Exit the loop if there are no more keys to enumerate
                    input('Exiting the loop, if there are no more keys to enumerate')
                    break
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Check for administrator privileges
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("Administrator privileges are required to perform this operation.")
        # Run the program with administrator privileges
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    else:
        modify_registry_key()
        input('\nPress Enter to exit...')