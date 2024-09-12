import os
import subprocess
import winreg
import json
from datetime import datetime

# Fichier pour sauvegarder l'état initial
REFERENCE_FILE = "hids_reference.json"
LOG_FILE = "hids_log.txt"

# 1. Comparaison des GPO
def get_gpo_state():
    # Exécute la commande PowerShell pour extraire les GPO
    cmd = "powershell -Command 'Get-GPO -All | Select-Object DisplayName, GPOStatus'"
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.stdout

def compare_gpo(base_gpo, current_gpo):
    return base_gpo == current_gpo

# 2. Vérification des modifications du registre
def get_registry_value(key, subkey, value):
    try:
        registry_key = winreg.OpenKey(key, subkey, 0, winreg.KEY_READ)
        reg_value, reg_type = winreg.QueryValueEx(registry_key, value)
        winreg.CloseKey(registry_key)
        return reg_value
    except WindowsError:
        return None

def compare_registry(base_registry, current_registry):
    return base_registry == current_registry

# 3. Vérification du service Netlogon
def check_netlogon_status():
    cmd = "sc query netlogon"
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return "RUNNING" in result.stdout

# Sauvegarder l'état de référence (GPO et registre) dans un fichier JSON
def save_reference(base_gpo, base_registry):
    reference_data = {
        "gpo": base_gpo,
        "registry": base_registry
    }
    with open(REFERENCE_FILE, "w") as ref_file:
        json.dump(reference_data, ref_file)
    print(f"État de référence sauvegardé dans {REFERENCE_FILE}")

# Charger l'état de référence depuis un fichier JSON
def load_reference():
    if os.path.exists(REFERENCE_FILE):
        with open(REFERENCE_FILE, "r") as ref_file:
            reference_data = json.load(ref_file)
        return reference_data["gpo"], reference_data["registry"]
    else:
        return None, None

# Journal des modifications détectées
def log_changes(message):
    with open(LOG_FILE, "a") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"{timestamp}: {message}\n")
    print(message)

# Fonction principale du HIDS
def hids_check():
    # Charger les valeurs de référence
    base_gpo, base_registry = load_reference()
    if base_gpo is None or base_registry is None:
        print("[ERREUR] Pas de référence trouvée. Exécutez d'abord la sauvegarde de l'état initial.")
        return

    # Comparaison des GPO
    current_gpo = get_gpo_state()
    if not compare_gpo(base_gpo, current_gpo):
        log_changes("[ALERTE] Les GPO ont été modifiés !")

    # Comparaison du registre
    current_registry_value = get_registry_value(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Netlogon", "Start")
    if not compare_registry(base_registry, current_registry_value):
        log_changes("[ALERTE] Le registre a été modifié !")

    # Vérification du service Netlogon
    if not check_netlogon_status():
        log_changes("[ALERTE] Le service Netlogon est désactivé !")

# Sauvegarde de l'état initial
def get_factory_defaults():
    # Sauvegarde l'état de référence pour une machine Windows propre
    base_gpo = get_gpo_state()
    base_registry = get_registry_value(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Netlogon", "Start")
    save_reference(base_gpo, base_registry)

# Instructions pour planification avec le Planificateur de tâches Windows
def schedule_task():
    task_name = "HIDS_Check"
    script_path = os.path.abspath(__file__)
    cmd = f"schtasks /create /tn {task_name} /tr \"python {script_path}\" /sc daily /st 09:00"
    subprocess.run(cmd, shell=True)
    print(f"Tâche planifiée sous le nom '{task_name}' pour s'exécuter tous les jours à 9h00.")

# Exécution du script
if __name__ == "__main__":
    choice = input("Choisissez une option: (1) Sauvegarder l'état initial, (2) Exécuter la vérification HIDS, (3) Planifier la vérification quotidienne: ")

    if choice == "1":
        get_factory_defaults()
    elif choice == "2":
        hids_check()
    elif choice == "3":
        schedule_task()
    else:
        print("Option invalide.")
