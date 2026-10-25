"""
Module Matériel & Surveillance Système — Inspiré d'OpenJarvis (Stanford)
Optimisé spécifiquement pour MacBook Pro 15" 2017 (MacBookPro14,3).
"""

import os
import re
import subprocess

def get_cpu_info() -> dict:
    try:
        load = os.getloadavg()
        cores = subprocess.check_output(["sysctl", "-n", "hw.ncpu"], text=True).strip()
        return {
            "load_1m": round(load[0], 2),
            "load_5m": round(load[1], 2),
            "cores": int(cores)
        }
    except Exception:
        return {"load_1m": 0.0, "cores": 8}

def get_memory_info() -> dict:
    try:
        vm_stat = subprocess.check_output(["vm_stat"], text=True)
        page_size = 4096
        free_pages = 0
        active_pages = 0
        for line in vm_stat.splitlines():
            if "Pages free" in line:
                free_pages = int(re.search(r'\d+', line).group(0))
            elif "Pages active" in line:
                active_pages = int(re.search(r'\d+', line).group(0))
        
        free_gb = round((free_pages * page_size) / (1024 ** 3), 1)
        active_gb = round((active_pages * page_size) / (1024 ** 3), 1)
        total_gb = 16  # standard MacBookPro14,3
        return {
            "free_gb": free_gb,
            "active_gb": active_gb,
            "total_gb": total_gb,
            "used_pct": int(((total_gb - free_gb) / total_gb) * 100)
        }
    except Exception:
        return {"free_gb": 4.0, "total_gb": 16, "used_pct": 50}

def get_battery_info() -> dict:
    try:
        out = subprocess.check_output(["pmset", "-g", "batt"], text=True)
        pct_match = re.search(r'(\d+)%', out)
        pct = int(pct_match.group(1)) if pct_match else 100
        charging = "secteur (en charge)" if "charging" in out.lower() else "sur batterie"
        
        time_match = re.search(r'(\d+:\d+)\s+remaining', out)
        remaining = time_match.group(1) if time_match else "calcul en cours"
        
        return {
            "percent": pct,
            "state": charging,
            "time_remaining": remaining
        }
    except Exception:
        return {"percent": 100, "state": "secteur", "time_remaining": "N/A"}

_CACHED_GPU = None
_CACHED_GPU_TIME = 0

def get_active_gpu() -> str:
    """Détecte si le dGPU Radeon Pro 560 ou l'iGPU Intel HD 630 est actuellement actif (avec cache de 60s)."""
    global _CACHED_GPU, _CACHED_GPU_TIME
    import time
    now = time.time()
    if _CACHED_GPU and (now - _CACHED_GPU_TIME < 60):
        return _CACHED_GPU
    try:
        out = subprocess.check_output(["system_profiler", "SPDisplaysDataType", "-timeout", "2"], text=True)
        if "Radeon Pro 560" in out and "Color LCD" in out.split("Radeon Pro 560")[1]:
            _CACHED_GPU = "AMD Radeon Pro 560 (dGPU Performance)"
        else:
            _CACHED_GPU = "Intel HD Graphics 630 (iGPU Économie d'énergie)"
    except Exception:
        _CACHED_GPU = "AMD Radeon Pro 560 / Intel HD 630"
    _CACHED_GPU_TIME = now
    return _CACHED_GPU

def get_full_telemetry() -> dict:
    """Rassemble l'ensemble des métriques de la machine."""
    cpu = get_cpu_info()
    mem = get_memory_info()
    batt = get_battery_info()
    gpu = get_active_gpu()

    # Espace disque
    try:
        df_out = subprocess.check_output(["df", "-h", "/"], text=True).splitlines()[1].split()
        disk_free = df_out[3]
    except Exception:
        disk_free = "Inconnu"

    return {
        "modele": "MacBook Pro 15\" (2017) [MacBookPro14,3]",
        "cpu": f"Intel Core i7 ({cpu['cores']} cœurs, charge: {cpu['load_1m']})",
        "gpu": gpu,
        "memoire": f"{mem['used_pct']}% utilisée ({mem['free_gb']} Go libres sur {mem['total_gb']} Go)",
        "batterie": f"{batt['percent']}% ({batt['state']}, restant: {batt['time_remaining']})",
        "disque": f"{disk_free} d'espace disponible"
    }
