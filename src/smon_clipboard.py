import base64
import os
import shutil
import subprocess


def copy_to_clipboard(text: str) -> bool:
    """
    Attempts to copy text to clipboard using multiple methods:
    1. OSC 52 (Best for SSH/Remote)
    2. Local Command (xclip/wl-copy/pbcopy) - Best for Local Terminals
    """
    success = False

    # METHOD 1: OSC 52 (Remote/SSH)
    try:
        data = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        osc = f"\x1b]52;c;{data}\x07"

        term = os.environ.get("TERM", "")
        if "screen" in term or "tmux" in term or os.environ.get("TMUX"):
            osc = f"\x1bPtmux;\x1b{osc}\x1b\\"

        os.write(1, osc.encode("utf-8"))
        success = True
    except Exception:
        pass

    # METHOD 2: Local Command Fallback (xclip/xsel/pbcopy)
    commands = [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["wl-copy"],
        ["pbcopy"],
    ]

    for cmd in commands:
        if shutil.which(cmd[0]):
            try:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                process.communicate(input=text.encode("utf-8"))
                if process.returncode == 0:
                    success = True
                    break
            except Exception:
                continue

    return success
