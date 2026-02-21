import subprocess
import re
import getpass
import sys
import base64
from datetime import datetime
from rich.text import Text
from rich.panel import Panel
from rich.table import Table as RichTable
from rich import box
from rich.progress import Progress, BarColumn, TextColumn

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Footer, DataTable, Static, Label, Button
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual import on
import os
import shutil

# --- CONFIGURATION ---

def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


USE_FAKE_DATA = _is_truthy(os.environ.get("SMON_FAKE_DATA"))


def _get_cluster_name() -> str:
    if USE_FAKE_DATA:
        try:
            from .fake_slurm_fixtures import get_fake_cluster_name
        except ImportError:
            from fake_slurm_fixtures import get_fake_cluster_name
        return get_fake_cluster_name()
    return subprocess.getoutput("hostname").upper()


CLUSTER_NAME = _get_cluster_name()
DASHBOARD_TITLE = "🚀 HPC CLUSTER MONITOR"
REFRESH_RATE = 2.0


# --- HELPER: REMOTE CLIPBOARD ---
def copy_to_clipboard(text):
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
        success = True  # Assume success if we wrote to stdout
    except:
        pass

    # METHOD 2: Local Command Fallback (xclip/xsel/pbcopy)
    # This fixes issues in GNOME Terminal or local sessions where OSC 52 is ignored.
    commands = [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["wl-copy"],  # Wayland
        ["pbcopy"],  # Mac
    ]

    for cmd in commands:
        if shutil.which(cmd[0]):
            try:
                p = subprocess.Popen(
                    cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                p.communicate(input=text.encode("utf-8"))
                if p.returncode == 0:
                    success = True
                    break
            except:
                continue

    return success


# --- DATA FETCHING ---
if USE_FAKE_DATA:
    try:
        from .fake_slurm_fixtures import run_fake_slurm_command
    except ImportError:
        from fake_slurm_fixtures import run_fake_slurm_command
else:

    def run_fake_slurm_command(cmd: str) -> str:
        return ""


def run_slurm_command(cmd: str) -> str:
    if USE_FAKE_DATA:
        return run_fake_slurm_command(cmd)
    return subprocess.getoutput(cmd)


def get_cluster_stats():
    try:
        output = run_slurm_command("scontrol show node -o")
    except Exception:
        return [], (0, 0, 0, 0), (0, 0)

    nodes_data = []
    t_cpu_u, t_cpu_t, t_gpu_u, t_gpu_t = 0, 0, 0, 0
    r_cpu_t, r_gpu_t = 0, 0

    OFFLINE_STATES = ["DOWN", "DRAIN", "FAIL", "MAINT", "NO_RESPOND"]

    for line in output.split("\n"):
        if not line.strip():
            continue
        tokens = line.split()
        data = {k: v for k, v in [t.split("=", 1) for t in tokens if "=" in t]}

        name = data.get("NodeName", "Unknown")
        state = data.get("State", "Unknown")
        c_u = int(data.get("CPUAlloc", 0))
        c_t = int(data.get("CPUTot", 0))
        m_u = int(data.get("AllocMem", 0))
        m_t = int(data.get("RealMemory", 1))

        g_t, g_u = 0, 0
        gres_str = data.get("Gres", "")
        if "gpu" in gres_str:
            parts = re.findall(r":(\d+)", gres_str)
            if parts:
                g_t = int(parts[0])

        alloc_tres = data.get("AllocTRES", "")
        if "gres/gpu" in alloc_tres:
            match = re.search(r"gres/gpu[^=]*=(\d+)", alloc_tres)
            if match:
                g_u = int(match.group(1))

        t_cpu_u += c_u
        t_cpu_t += c_t
        t_gpu_u += g_u
        t_gpu_t += g_t

        if not any(s in state for s in OFFLINE_STATES):
            r_cpu_t += c_t
            r_gpu_t += g_t

        nodes_data.append(
            {
                "name": name,
                "state": state,
                "c_u": c_u,
                "c_t": c_t,
                "m_u": m_u,
                "m_t": m_t,
                "g_u": g_u,
                "g_t": g_t,
            }
        )

    return nodes_data, (t_cpu_u, t_cpu_t, t_gpu_u, t_gpu_t), (r_cpu_t, r_gpu_t)


def get_job_stats():
    cmd = (
        'squeue --all --format="'
        "%.8i %.8u %.11T %.11M %.12L %.10Q %.4D %.40R %.20b %.40j "
        "%.6C %.8m %.10P %.20a %.10q %.20V %.20E"
        '" --sort=T'
    )
    try:
        output = run_slurm_command(cmd)
    except Exception:
        return []

    jobs_data = []
    lines = output.split("\n")

    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 17:
            continue

        gpu_count = "-"
        gpu_field = parts[8]
        if "gpu" in gpu_field:
            try:
                # Support explicit total notation in fixtures: gpu_total=64
                total_match = re.search(
                    r"(?:gpu_total|total_gpu|gres/gpu)[:=](\d+)", gpu_field
                )
                if total_match:
                    gpu_count = total_match.group(1)
                else:
                    node_mult = int(parts[6])
                    per_node_match = re.search(r"gpu[^0-9]*(\d+)", gpu_field)
                    if per_node_match:
                        per_node = int(per_node_match.group(1))
                        gpu_count = str(node_mult * per_node)
            except:
                pass

        dep = parts[16]
        if dep == "(null)" or dep == "N/A":
            dep = ""

        jobs_data.append(
            {
                "id": parts[0],
                "user": parts[1],
                "state": parts[2],
                "time": parts[3],
                "left": parts[4],
                "prio": parts[5],
                "nodes": parts[6],
                "reason": parts[7],
                "gpu": gpu_count,
                "name": parts[9],
                "cpu": parts[10],
                "mem": parts[11],
                "part": parts[12],
                "account": parts[13],
                "qos": parts[14],
                "submit": parts[15],
                "dep": dep,
            }
        )

    return jobs_data


def get_job_details(job_id):
    details = {"raw": "", "sstat": ""}
    try:
        details["raw"] = run_slurm_command(f"scontrol show job {job_id}")
    except:
        details["raw"] = "Error fetching job details."

    if "JobState=RUNNING" in details["raw"]:
        try:
            cmd = f"sstat -j {job_id} --format=AveCPU,AveRSS,MaxRSS,MaxDiskRead,MaxDiskWrite -n -P"
            sstat_out = run_slurm_command(cmd)
            details["sstat"] = sstat_out
        except:
            pass

    return details


# --- MODAL SCREENS ---


class KillConfirmationScreen(ModalScreen):
    CSS = """
    KillConfirmationScreen { align: center middle; background: rgba(40, 0, 0, 0.8); }
    #kill-dialog { width: 74; height: auto; background: $surface; border: solid red; padding: 1 2; }
    .warning-text { text-align: center; color: red; text-style: bold; margin-bottom: 1; width: 100%; }
    .info-text { text-align: center; margin-bottom: 2; width: 100%; }
    #button-row { align: center middle; height: auto; width: 100%; margin-top: 1; }
    Button { margin: 0 2; }
    """

    def __init__(self, job_id, job_user):
        super().__init__()
        self.job_id = job_id
        self.job_user = job_user
        self.current_user = getpass.getuser()

    def compose(self) -> ComposeResult:
        with Container(id="kill-dialog"):
            yield Label("⚠️  KILL JOB CONFIRMATION ⚠️", classes="warning-text")
            msg = f"Are you sure you want to cancel job {self.job_id}?"
            if self.job_user != self.current_user:
                msg += f"\n\n[bold red]WARNING: You are {self.current_user}, but this job belongs to {self.job_user}![/]"
            yield Label(msg, classes="info-text")
            with Horizontal(id="button-row"):
                yield Button("Yes, Kill it", variant="error", id="confirm")
                yield Button("No, Keep it", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class JobDetailScreen(ModalScreen):
    CSS = """
    JobDetailScreen { align: center middle; background: rgba(0,0,0,0.7); }
    #detail-container { width: 80%; height: 80%; background: $surface; border: solid $accent; padding: 1 2; }
    #detail-content { margin-top: 1; }
    .header { text-style: bold; color: $accent; border-bottom: solid $accent; width: 100%; }
    .label { color: $text-muted; text-align: center; width: 100%; margin-top: 1; }
    """

    def __init__(self, job_id):
        super().__init__()
        self.job_id = job_id
        self.data = get_job_details(job_id)

    def compose(self) -> ComposeResult:
        with Container(id="detail-container"):
            yield Label(f"🔍 Job Details: {self.job_id}", classes="header")
            with ScrollableContainer(id="detail-content"):
                if self.data.get("sstat") and "error" not in self.data["sstat"].lower():
                    yield Label("\n📈 Live Resource Usage (sstat)", classes="header")
                    parts = self.data["sstat"].strip().split("|")
                    if len(parts) >= 3:
                        grid = RichTable.grid(padding=(0, 2))
                        grid.add_column()
                        grid.add_column()
                        grid.add_row(Text("Ave CPU:"), Text(parts[0], style="green"))
                        grid.add_row(
                            Text("Ave RSS (Mem):"), Text(parts[1], style="green")
                        )
                        grid.add_row(
                            Text("Max RSS (Peak):"), Text(parts[2], style="bold red")
                        )
                        yield Static(grid)
                    else:
                        yield Label("No sstat metrics available yet.")

                yield Label("\n📋 Configuration (scontrol)", classes="header")
                raw_text = self.data["raw"]
                grid = RichTable.grid(padding=(0, 2))
                grid.add_column(style="dim cyan", justify="right")
                grid.add_column(style="white")
                interesting_keys = [
                    "JobId",
                    "JobName",
                    "UserId",
                    "Account",
                    "QOS",
                    "JobState",
                    "Reason",
                    "Dependency",
                    "RunTime",
                    "TimeLimit",
                    "SubmitTime",
                    "StartTime",
                    "Partition",
                    "NodeList",
                    "NumNodes",
                    "NumCPUs",
                    "Command",
                    "WorkDir",
                    "StdOut",
                ]
                parsed_map = {}
                tokens = re.split(r"\s+", raw_text)
                for t in tokens:
                    if "=" in t:
                        k, v = t.split("=", 1)
                        if k in interesting_keys:
                            parsed_map[k] = v
                for k, v in parsed_map.items():
                    grid.add_row(k, v)
                yield Static(grid)
            yield Label("\n[Press ESC or Enter to close]", classes="label")

    def key_escape(self):
        self.dismiss()

    def key_enter(self):
        self.dismiss()


class ShortcutHelpScreen(ModalScreen):
    CSS = """
    ShortcutHelpScreen { align: center middle; background: rgba(0,0,0,0.75); }
    #help-container { width: 88%; height: 88%; background: $surface; border: solid $accent; padding: 1 2; }
    #help-content { margin-top: 1; }
    .header { text-style: bold; color: $accent; border-bottom: solid $accent; width: 100%; }
    .label { color: $text-muted; text-align: center; width: 100%; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        def make_table(title: str, rows: list[tuple[str, str]]) -> RichTable:
            table = RichTable(title=title, box=box.ROUNDED, expand=True)
            table.add_column("Key", style="bold cyan", no_wrap=True)
            table.add_column("Action", style="white")
            for key, action in rows:
                table.add_row(key, action)
            return table

        with Container(id="help-container"):
            yield Label("⌨️ Shortcut Manual", classes="header")
            with ScrollableContainer(id="help-content"):
                mode_table = make_table(
                    "Modes",
                    [
                        ("Normal mode", "Default mode for navigation and actions."),
                        ("Edit mode", "Layout control mode (resize/toggle panes)."),
                        ("m", "Toggle Normal/Edit mode."),
                    ],
                )
                yield Static(mode_table)

                normal_table = make_table(
                    "Normal Mode",
                    [
                        ("j / k", "Move down/up in the focused table."),
                        ("h / l", "Scroll jobs table left/right (when Jobs pane is focused)."),
                        ("Shift+Left / Shift+H", "Focus Nodes pane."),
                        ("Shift+Right / Shift+L", "Focus Jobs pane."),
                        ("c", "Toggle compact jobs view."),
                        ("x / Delete", "Kill selected job."),
                        ("y", "Copy selected job ID."),
                        ("Enter", "Open selected job details."),
                        ("?", "Open/close this manual."),
                        ("q", "Quit smon."),
                    ],
                )
                yield Static(normal_table)

                edit_table = make_table(
                    "Edit Mode",
                    [
                        ("h / Left", "Narrow nodes pane width."),
                        ("l / Right", "Widen nodes pane width."),
                        ("n", "Toggle nodes-only view."),
                        ("j", "Toggle jobs-only view."),
                        ("v", "Reset split view and default width."),
                        ("Shift+Left / Shift+H", "Focus Nodes pane."),
                        ("Shift+Right / Shift+L", "Focus Jobs pane."),
                        ("m / Esc", "Return to normal mode."),
                    ],
                )
                yield Static(edit_table)

            yield Label("[Press ? or ESC to close]", classes="label")

    def key_escape(self):
        self.dismiss()

    def key_question_mark(self):
        self.dismiss()

    def on_mount(self):
        # Focus scroll area so keyboard scrolling works immediately on open.
        self.query_one("#help-content", ScrollableContainer).focus()

    def on_key(self, event):
        content = self.query_one("#help-content", ScrollableContainer)
        if event.key in ("j", "down"):
            content.scroll_down(animate=False)
            event.stop()
        elif event.key in ("k", "up"):
            content.scroll_up(animate=False)
            event.stop()


# --- MAIN APP ---


class Branding(Static):
    def on_mount(self):
        self.update_branding()
        self.set_interval(1.0, self.update_branding)

    def update_branding(self):
        grid = RichTable.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right", ratio=1)
        title = Text(f" {DASHBOARD_TITLE}", style="bold cyan")
        cluster = Text(f"🖥  {CLUSTER_NAME}", style="bold magenta")
        clock = Text(f"{datetime.now().strftime('%H:%M:%S')} ", style="bold green")
        grid.add_row(title, cluster, clock)
        self.update(Panel(grid, style="white", box=box.ROUNDED, height=3))


class ClusterBars(Static):
    def update_bars(self, theo, real):
        c_used, c_tot, g_used, g_tot = theo
        c_real, g_real = real

        def make_bar(label, used, total, color):
            pct = int((used / total) * 100) if total > 0 else 0
            bar = Progress(
                TextColumn(f"[{color}]{label}"),
                BarColumn(bar_width=None, style=color, complete_style=color),
                TextColumn(f"{used}/{total} ({pct}%)"),
                expand=True,
            )
            bar.add_task("", total=max(total, used), completed=used)
            return bar

        cpu_grid = RichTable.grid(expand=True, padding=(0, 1))
        cpu_grid.add_column()
        cpu_grid.add_row(make_bar("Total", c_used, c_tot, "cyan"))
        cpu_grid.add_row(make_bar("Active", c_used, c_real, "blue"))
        gpu_grid = RichTable.grid(expand=True, padding=(0, 1))
        gpu_grid.add_column()
        gpu_grid.add_row(make_bar("Total", g_used, g_tot, "magenta"))
        gpu_grid.add_row(make_bar("Active", g_used, g_real, "purple"))
        main_grid = RichTable.grid(expand=True, padding=(0, 0))
        main_grid.add_column(ratio=1)
        main_grid.add_column(ratio=1)
        main_grid.add_row(
            Panel(cpu_grid, title="CPU Load", box=box.ROUNDED),
            Panel(gpu_grid, title="GPU Load", box=box.ROUNDED),
        )
        self.update(main_grid)


class SlurmDashboard(App):
    CSS = """
    Screen { layout: vertical; }
    Branding { height: auto; width: 100%; margin: 0; padding: 0; }
    #header-stats { height: auto; width: 100%; margin: 0; padding: 0; }
    #node-pane { width: 42; height: 100%; border-right: solid $accent; }
    
    #job-pane { 
        width: 1fr; 
        height: 100%; 
        overflow: hidden; 
    }
    
    #job-scroll-wrapper {
        width: 100%;
        height: 1fr;
        overflow-x: auto;
    }
    
    .pane-header { text-align: center; text-style: bold; background: $panel; color: $text; padding: 0 1; width: 100%; border-bottom: solid $accent; }
    DataTable { height: 100%; scrollbar-gutter: stable; }

    #statusline {
        height: 1;
        width: 100%;
        layout: horizontal;
        background: $footer-background;
        color: $footer-foreground;
    }

    #mode-pill {
        width: auto;
        height: 1;
        min-width: 8;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
        background: #1e3a8a;
        color: #dbeafe;
    }

    #status-footer {
        width: 1fr;
        height: 1;
        dock: none;
    }

    #status-footer FooterKey {
        background: transparent;
    }

    #status-footer FooterLabel {
        background: transparent;
    }

    SlurmDashboard.-mode-normal #mode-pill {
        background: #1e3a8a;
        color: #dbeafe;
    }

    SlurmDashboard.-mode-normal #statusline,
    SlurmDashboard.-mode-normal #status-footer,
    SlurmDashboard.-mode-normal #status-footer FooterKey,
    SlurmDashboard.-mode-normal #status-footer FooterLabel {
        background: #334155;
        color: #e2e8f0;
    }

    SlurmDashboard.-mode-normal #status-footer FooterKey .footer-key--key {
        background: #1e3a8a;
        color: #dbeafe;
    }

    SlurmDashboard.-mode-normal #status-footer FooterKey .footer-key--description {
        background: #334155;
        color: #e2e8f0;
    }

    SlurmDashboard.-mode-toggle #mode-pill {
        background: #f59e0b;
        color: #1f2937;
    }

    SlurmDashboard.-mode-toggle #statusline,
    SlurmDashboard.-mode-toggle #status-footer,
    SlurmDashboard.-mode-toggle #status-footer FooterKey,
    SlurmDashboard.-mode-toggle #status-footer FooterLabel {
        background: #7c2d12;
        color: #ffedd5;
    }

    SlurmDashboard.-mode-toggle #status-footer FooterKey .footer-key--key {
        background: #f59e0b;
        color: #1f2937;
    }

    SlurmDashboard.-mode-toggle #status-footer FooterKey .footer-key--description {
        background: #7c2d12;
        color: #ffedd5;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "toggle_compact", "Compact"),
        ("m", "toggle_mode", "Mode"),
        ("question_mark", "show_help", "Help"),
        ("shift+left", "focus_nodes_pane", "Focus Nodes"),
        ("shift+right", "focus_jobs_pane", "Focus Jobs"),
        ("shift+h", "focus_nodes_pane", "Focus Nodes"),
        ("shift+l", "focus_jobs_pane", "Focus Jobs"),
        ("x", "kill_job", "Kill Job"),
        ("delete", "kill_job", "Kill Job"),
        ("y", "copy_job_id", "Copy ID"),  # Key to copy
        ("copy", "copy_job_id", "Copy ID"),
    ]

    DEFAULT_NODE_PANE_WIDTH = 42
    MIN_NODE_PANE_WIDTH = 24
    PANE_RESIZE_STEP = 4
    show_compact = reactive(False)
    pane_mode = "split"
    node_pane_width = DEFAULT_NODE_PANE_WIDTH
    key_mode = "normal"  # normal, toggle

    def compose(self) -> ComposeResult:
        yield Branding()
        yield Container(ClusterBars(), id="header-stats")
        with Horizontal():
            with Vertical(id="node-pane"):
                yield Label("🖥  NODES", classes="pane-header")
                yield DataTable(id="node_table", cursor_type="row")
            with Vertical(id="job-pane"):
                yield Label("📊 ACTIVE JOBS", classes="pane-header")
                with Container(id="job-scroll-wrapper"):
                    yield DataTable(id="job_table", cursor_type="row")
        with Horizontal(id="statusline"):
            yield Static(" NORMAL ", id="mode-pill")
            yield Footer(id="status-footer")

    def on_mount(self) -> None:
        self.title = "Slurm Dashboard"
        self.pane_mode = "split"  # split, nodes, jobs
        self.node_pane_width = self.DEFAULT_NODE_PANE_WIDTH

        node_table = self.query_one("#node_table", DataTable)
        node_table.add_columns("Node", "State", "CPU", "Mem", "GPU")
        node_table.zebra_stripes = True

        self.query_one("#job_table", DataTable).focus()
        self._apply_mode_visual_state()
        self.apply_pane_layout()
        self.set_interval(REFRESH_RATE, self.update_data)
        self.update_data()

    def on_resize(self, event) -> None:
        # Re-apply split sizing so panes stay usable after terminal resize.
        if getattr(self, "pane_mode", "split") == "split":
            self.apply_pane_layout()

    def apply_pane_layout(self) -> None:
        node_pane = self.query_one("#node-pane", Vertical)
        job_pane = self.query_one("#job-pane", Vertical)
        node_table = self.query_one("#node_table", DataTable)
        job_table = self.query_one("#job_table", DataTable)

        if self.pane_mode == "nodes":
            node_pane.display = True
            job_pane.display = False
            node_pane.styles.width = "1fr"
            node_table.focus()
            return

        if self.pane_mode == "jobs":
            node_pane.display = False
            job_pane.display = True
            job_pane.styles.width = "1fr"
            job_table.focus()
            return

        # split mode
        max_nodes = max(self.MIN_NODE_PANE_WIDTH, self.size.width - 40)
        self.node_pane_width = max(
            self.MIN_NODE_PANE_WIDTH, min(self.node_pane_width, max_nodes)
        )
        node_pane.display = True
        job_pane.display = True
        node_pane.styles.width = self.node_pane_width
        job_pane.styles.width = "1fr"

    # --- CUSTOM KEY HANDLER FOR VIM NAV + LAYOUT MODE ---
    def on_key(self, event):
        """Enable vim navigation in normal mode and pane control in toggle mode."""
        if event.character == "?":
            self.action_show_help()
            event.stop()
            return

        if event.character == "H":
            self.action_focus_nodes_pane()
            event.stop()
            return

        if event.character == "L":
            self.action_focus_jobs_pane()
            event.stop()
            return

        if self.key_mode == "toggle":
            if event.key in ("m", "escape"):
                self._set_key_mode("normal")
                event.stop()
            elif event.key in ("h", "left"):
                self.action_narrow_nodes_pane()
                event.stop()
            elif event.key in ("l", "right"):
                self.action_widen_nodes_pane()
                event.stop()
            elif event.key == "n":
                self.action_toggle_nodes_only()
                event.stop()
            elif event.key == "j":
                self.action_toggle_jobs_only()
                event.stop()
            elif event.key == "v":
                self.action_reset_panes()
                event.stop()
            return

        job_table = self.query_one("#job_table", DataTable)
        node_table = self.query_one("#node_table", DataTable)

        if job_table.has_focus:
            wrapper = self.query_one("#job-scroll-wrapper")
            if event.key in ("left", "h"):
                wrapper.scroll_left(animate=False)
                event.stop()
            elif event.key in ("right", "l"):
                wrapper.scroll_right(animate=False)
                event.stop()
            elif event.key == "j":
                job_table.action_cursor_down()
                event.stop()
            elif event.key == "k":
                job_table.action_cursor_up()
                event.stop()
            return

        if node_table.has_focus:
            if event.key == "j":
                node_table.action_cursor_down()
                event.stop()
            elif event.key == "k":
                node_table.action_cursor_up()
                event.stop()

    # --- ACTIONS ---

    @on(DataTable.RowSelected)
    def show_job_details(self, event: DataTable.RowSelected):
        if event.control.id == "job_table":
            row_data = event.control.get_row(event.row_key)
            job_id = str(row_data[0])
            self.push_screen(JobDetailScreen(job_id))

    def action_copy_job_id(self):
        """Copies ID to local clipboard via OSC 52."""
        table = self.query_one("#job_table", DataTable)
        if not table.has_focus:
            return
        try:
            cursor_row = table.cursor_row
            if cursor_row < 0:
                return
            row_data = table.get_row_at(cursor_row)
            job_id = str(row_data[0])

            # Use OSC 52
            copy_to_clipboard(job_id)
        except Exception as e:
            self.notify(f"Clipboard Error: {e}", severity="error")

    def action_kill_job(self):
        table = self.query_one("#job_table", DataTable)
        if not table.has_focus:
            self.notify("Select the Jobs table first!", severity="warning")
            return
        try:
            cursor_row = table.cursor_row
            if cursor_row < 0:
                self.notify("No job selected.", severity="warning")
                return
            row_data = table.get_row_at(cursor_row)
            job_id = str(row_data[0])
            job_user = str(row_data[1]) if self.show_compact else str(row_data[2])

            def handle_kill_response(confirmed: bool):
                if confirmed:
                    try:
                        run_slurm_command(f"scancel {job_id}")
                        self.update_data()
                    except Exception as e:
                        self.notify(f"Error: {e}", severity="error")

            self.push_screen(
                KillConfirmationScreen(job_id, job_user), handle_kill_response
            )
        except Exception:
            self.notify("Could not identify job.", severity="error")

    def watch_show_compact(self, value: bool) -> None:
        self.rebuild_job_columns()
        self.update_data()

    def rebuild_job_columns(self):
        table = self.query_one("#job_table", DataTable)
        # Capture scroll before clearing logic
        table.clear(columns=True)
        if self.show_compact:
            table.styles.min_width = "100%"
            table.add_columns("ID", "User", "State", "Left", "Nodes", "GPU")
        else:
            # Force min-width to trigger scrollbar on wrapper
            table.styles.min_width = 170
            table.add_columns(
                "ID",
                "Name",
                "User",
                "Acct",
                "State",
                "Prio",
                "Left",
                "GPU",
                "CPU",
                "Mem",
                "Nodes",
                "Node/Reason",
                "QOS",
                "Part",
                "Dep",
                "Time",
                "Submit",
            )

    def action_toggle_compact(self):
        self.show_compact = not self.show_compact

    def _apply_mode_visual_state(self) -> None:
        mode_pill = self.query_one("#mode-pill", Static)
        mode_pill.update(" EDIT " if self.key_mode == "toggle" else " NORMAL ")
        self.set_class(self.key_mode == "toggle", "-mode-toggle")
        self.set_class(self.key_mode == "normal", "-mode-normal")

    def _set_key_mode(self, mode: str) -> None:
        self.key_mode = mode
        self._apply_mode_visual_state()

    def action_toggle_mode(self):
        next_mode = "normal" if self.key_mode == "toggle" else "toggle"
        self._set_key_mode(next_mode)

    def action_show_help(self):
        if isinstance(self.screen, ShortcutHelpScreen):
            self.pop_screen()
            return
        self.push_screen(ShortcutHelpScreen())

    def action_focus_nodes_pane(self):
        if self.pane_mode == "jobs":
            self.pane_mode = "split"
            self.apply_pane_layout()
        self.query_one("#node_table", DataTable).focus()

    def action_focus_jobs_pane(self):
        if self.pane_mode == "nodes":
            self.pane_mode = "split"
            self.apply_pane_layout()
        self.query_one("#job_table", DataTable).focus()

    def action_narrow_nodes_pane(self):
        if self.pane_mode != "split":
            return
        self.node_pane_width = max(
            self.MIN_NODE_PANE_WIDTH, self.node_pane_width - self.PANE_RESIZE_STEP
        )
        self.apply_pane_layout()

    def action_widen_nodes_pane(self):
        if self.pane_mode != "split":
            return
        max_nodes = max(self.MIN_NODE_PANE_WIDTH, self.size.width - 40)
        self.node_pane_width = min(
            max_nodes, self.node_pane_width + self.PANE_RESIZE_STEP
        )
        self.apply_pane_layout()

    def action_toggle_nodes_only(self):
        self.pane_mode = "split" if self.pane_mode == "nodes" else "nodes"
        self.apply_pane_layout()

    def action_toggle_jobs_only(self):
        self.pane_mode = "split" if self.pane_mode == "jobs" else "jobs"
        self.apply_pane_layout()

    def action_reset_panes(self):
        self.pane_mode = "split"
        self.node_pane_width = self.DEFAULT_NODE_PANE_WIDTH
        self.apply_pane_layout()

    def update_data(self):
        nodes, theo, real = get_cluster_stats()
        jobs = get_job_stats()

        self.query_one(ClusterBars).update_bars(theo, real)

        # UPDATE NODES
        n_table = self.query_one("#node_table", DataTable)
        n_scroll, n_cursor = n_table.scroll_y, n_table.cursor_coordinate
        n_table.clear()
        for n in nodes:
            c_style = "[red]" if n["c_u"] >= n["c_t"] else "[green]"
            g_style = "[red]" if n["g_u"] >= n["g_t"] else "[green]"
            state_fmt = (
                f"[green]{n['state']}[/]"
                if "IDLE" in n["state"]
                else f"[bold red]{n['state']}[/]"
                if any(x in n["state"] for x in ["DOWN", "DRAIN"])
                else n["state"]
            )
            n_table.add_row(
                n["name"],
                Text.from_markup(state_fmt),
                Text.from_markup(f"{c_style}{n['c_u']}[/]/[dim]{n['c_t']}[/]"),
                f"{n['m_u'] // 1024}G",
                Text.from_markup(f"{g_style}{n['g_u']}[/]/[dim]{n['g_t']}[/]"),
            )
        n_table.scroll_y = n_scroll
        n_table.move_cursor(row=n_cursor.row, column=n_cursor.column, animate=False)

        # UPDATE JOBS (With Scroll Preservation)
        j_wrapper = self.query_one("#job-scroll-wrapper")
        j_table = self.query_one("#job_table", DataTable)

        # 1. SAVE SCROLL X/Y
        j_scroll_x = j_wrapper.scroll_x
        j_scroll_y = j_table.scroll_y
        j_cursor = j_table.cursor_coordinate

        j_table.clear()

        for j in jobs:
            state_color = "green" if j["state"] == "RUNNING" else "yellow"
            state_txt = Text.from_markup(f"[{state_color}]{j['state']}[/]")
            if self.show_compact:
                j_table.add_row(
                    j["id"], j["user"], state_txt, j["left"], j["nodes"], j["gpu"]
                )
            else:
                j_table.add_row(
                    j["id"],
                    j["name"],
                    j["user"],
                    j["account"],
                    state_txt,
                    j["prio"],
                    j["left"],
                    j["gpu"],
                    j["cpu"],
                    j["mem"],
                    j["nodes"],
                    j["reason"],
                    j["qos"],
                    j["part"],
                    j["dep"],
                    j["time"],
                    j["submit"],
                )

        # 2. RESTORE SCROLL X/Y
        # We must restore X on the wrapper and Y on the table
        j_table.scroll_y = j_scroll_y
        j_wrapper.scroll_x = j_scroll_x
        j_table.move_cursor(row=j_cursor.row, column=j_cursor.column, animate=False)


if __name__ == "__main__":
    app = SlurmDashboard()
    app.run()
