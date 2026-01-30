# 🚀 smon (Slurm Monitor)

**smon** is a high-performance, real-time Terminal User Interface (TUI) for monitoring Slurm clusters. It provides a specialized dashboard to track cluster health and manage jobs efficiently.

---

## ✨ Features 
- **Live Node Status:** Monitor CPU, Memory, and GPU allocation across the cluster at a glance. - **Job Dashboard:** Track active jobs, their states, and live resource usage. 
- **Interactive Modals:** View full scontrol details or kill jobs with a confirmation prompt. 
- **Remote Clipboard:** Uses **OSC 52** to copy Job IDs directly to your local computer's clipboard, even when working over SSH. 
- **Auto-Refresh:** Continuous updates every 2 seconds.

---

## 🛠 Installation & Building

This project uses [uv](https://astral.sh/uv) for Python environment management and a **Makefile** for automation.

### Prerequisites 
- **Python 3.10+** 
- **uv** (Package Manager) 
- **Slurm** binaries (squeue, scontrol, sstat) must be in your $PATH.

### Commands 
To clean the project, sync dependencies, build the binary, and install it to ~/.local/bin/smon:

```
make deploy
```

*Note: Ensure ~/.local/bin is in your system $PATH to run smon from anywhere.*

---

## ⌨️ Keybindings 
| Key | Action |
| :--- | :--- |
| Q | Quit smon |
| R | Manual Refresh |
| C | Toggle Compact/Detailed Mode | 
| K / Del | Kill Selected Job (with confirmation) | 
| Y | Copy Job ID to Local Clipboard (OSC 52) |
| Enter | View Detailed Job/Resource Info |
| Arrows | Navigate tables and scroll horizontally |

---

## 📋 Clipboard Support
For the **Copy ID (Y)** feature to work over SSH, your terminal must support OSC 52: 
* **Supported:** iTerm2, Windows Terminal, VSCode Terminal, Alacritty, Kitty. 
* **Tmux Users:** Add set -s set-clipboard on to your tmux.conf.

---

## 🏗 Project Structure 
- src/main.py: The core Textual application logic. 
- pyproject.toml: Project metadata and dependencies. 
- Makefile: Automated build and deployment pipeline. 
- dist/smon: The generated standalone binary (after running make build).

---

## 🛠 Makefile Reference 
- make build: Performs a clean build of the standalone binary. 
- make deploy: Builds the binary and moves it to ~/bin. 
- make clean: Removes all build artifacts and temporary files.