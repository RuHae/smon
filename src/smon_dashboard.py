from datetime import datetime

from rich import box
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table as RichTable
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Label, Static

from slurm_backend import (
    get_cluster_stats,
    get_job_stats,
    run_slurm_command,
)
from smon_clipboard import copy_to_clipboard
from smon_config import CLUSTER_NAME, DASHBOARD_TITLE, REFRESH_RATE
from smon_screens import JobDetailScreen, KillConfirmationScreen, ShortcutHelpScreen


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
        ("y", "copy_job_id", "Copy ID"),
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
        self.pane_mode = "split"
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

        max_nodes = max(self.MIN_NODE_PANE_WIDTH, self.size.width - 40)
        self.node_pane_width = max(
            self.MIN_NODE_PANE_WIDTH, min(self.node_pane_width, max_nodes)
        )
        node_pane.display = True
        job_pane.display = True
        node_pane.styles.width = self.node_pane_width
        job_pane.styles.width = "1fr"

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
            copy_to_clipboard(job_id)
        except Exception as error:
            self.notify(f"Clipboard Error: {error}", severity="error")

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
                    except Exception as error:
                        self.notify(f"Error: {error}", severity="error")

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
        table.clear(columns=True)
        if self.show_compact:
            table.styles.min_width = "100%"
            table.add_columns("ID", "User", "State", "Left", "Nodes", "GPU")
        else:
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

        n_table = self.query_one("#node_table", DataTable)
        n_scroll, n_cursor = n_table.scroll_y, n_table.cursor_coordinate
        n_table.clear()
        for node in nodes:
            c_style = "[red]" if node["c_u"] >= node["c_t"] else "[green]"
            g_style = "[red]" if node["g_u"] >= node["g_t"] else "[green]"
            state_fmt = (
                f"[green]{node['state']}[/]"
                if "IDLE" in node["state"]
                else f"[bold red]{node['state']}[/]"
                if any(x in node["state"] for x in ["DOWN", "DRAIN"])
                else node["state"]
            )
            n_table.add_row(
                node["name"],
                Text.from_markup(state_fmt),
                Text.from_markup(f"{c_style}{node['c_u']}[/]/[dim]{node['c_t']}[/]"),
                f"{node['m_u'] // 1024}G",
                Text.from_markup(f"{g_style}{node['g_u']}[/]/[dim]{node['g_t']}[/]"),
            )
        n_table.scroll_y = n_scroll
        n_table.move_cursor(row=n_cursor.row, column=n_cursor.column, animate=False)

        j_wrapper = self.query_one("#job-scroll-wrapper")
        j_table = self.query_one("#job_table", DataTable)

        j_scroll_x = j_wrapper.scroll_x
        j_scroll_y = j_table.scroll_y
        j_cursor = j_table.cursor_coordinate

        j_table.clear()

        for job in jobs:
            state_color = "green" if job["state"] == "RUNNING" else "yellow"
            state_txt = Text.from_markup(f"[{state_color}]{job['state']}[/]")
            if self.show_compact:
                j_table.add_row(
                    job["id"],
                    job["user"],
                    state_txt,
                    job["left"],
                    job["nodes"],
                    job["gpu"],
                )
            else:
                j_table.add_row(
                    job["id"],
                    job["name"],
                    job["user"],
                    job["account"],
                    state_txt,
                    job["prio"],
                    job["left"],
                    job["gpu"],
                    job["cpu"],
                    job["mem"],
                    job["nodes"],
                    job["reason"],
                    job["qos"],
                    job["part"],
                    job["dep"],
                    job["time"],
                    job["submit"],
                )

        j_table.scroll_y = j_scroll_y
        j_wrapper.scroll_x = j_scroll_x
        j_table.move_cursor(row=j_cursor.row, column=j_cursor.column, animate=False)
