"""
Module Vocal — Inspiré de sosoj92/jarvis-assistant-vocal
Gère la synthèse vocale macOS (TTS) et l'émission audio.
"""

import os
import re
import subprocess

DEFAULT_VOICE = "Thomas"
DEFAULT_RATE = 185
_VOICE_MUTED = False

def set_mute(muted: bool):
    global _VOICE_MUTED
    _VOICE_MUTED = muted

def is_muted() -> bool:
    return _VOICE_MUTED

def play_chime(kind: str = "activate"):
    """Joue un son système discret macOS pour confirmer l'action."""
    sounds = {
        "activate": "/System/Library/Sounds/Tink.aiff",
        "success": "/System/Library/Sounds/Glass.aiff",
        "alert": "/System/Library/Sounds/Basso.aiff"
    }
    sound_path = sounds.get(kind, sounds["activate"])
    if os.path.exists(sound_path) and not _VOICE_MUTED:
        subprocess.Popen(["afplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def speak(text: str, voice: str = DEFAULT_VOICE, rate: int = DEFAULT_RATE):
    """Prononce le texte avec la voix macOS choisie."""
    if _VOICE_MUTED:
        return

    # Nettoyage du markdown (astérisques, backticks, emojis)
    cleaned = re.sub(r'[*_`#\n]', ' ', text)
    cleaned = re.sub(r'[^\w\s,\.?!:\'\"àâéèêëîïôöùûüçÀÂÉÈÊËÎÏÔÖÙÛÜÇ-]', '', cleaned).strip()

    if cleaned:
        try:
            subprocess.run(["say", "-v", voice, "-r", str(rate), cleaned], check=False)
        except Exception:
            pass
