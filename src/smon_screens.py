import getpass
import re

from rich import box
from rich.table import Table as RichTable
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from slurm_backend import get_job_details


class KillConfirmationScreen(ModalScreen):
    CSS = """
    KillConfirmationScreen { align: center middle; background: rgba(40, 0, 0, 0.8); }
    #kill-dialog { width: 74; height: auto; background: $surface; border: solid red; padding: 1 2; }
    .warning-text { text-align: center; color: red; text-style: bold; margin-bottom: 1; width: 100%; }
    .info-text { text-align: center; margin-bottom: 2; width: 100%; }
    #button-row { align: center middle; height: auto; width: 100%; margin-top: 1; }
    Button { margin: 0 2; }
    """

    def __init__(self, job_id: str, job_user: str):
        super().__init__()
        self.job_id = job_id
        self.job_user = job_user
        self.current_user = getpass.getuser()

    def compose(self) -> ComposeResult:
        with Container(id="kill-dialog"):
            yield Label("⚠️  KILL JOB CONFIRMATION ⚠️", classes="warning-text")
            msg = f"Are you sure you want to cancel job {self.job_id}?"
            if self.job_user != self.current_user:
                msg += (
                    "\n\n[bold red]WARNING: You are "
                    f"{self.current_user}, but this job belongs to {self.job_user}![/]"
                )
            yield Label(msg, classes="info-text")
            with Horizontal(id="button-row"):
                yield Button("Yes, Kill it", variant="error", id="confirm")
                yield Button("No, Keep it", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class JobDetailScreen(ModalScreen):
    CSS = """
    JobDetailScreen { align: center middle; background: rgba(0,0,0,0.7); }
    #detail-container { width: 80%; height: 80%; background: $surface; border: solid $accent; padding: 1 2; }
    #detail-content { margin-top: 1; }
    .header { text-style: bold; color: $accent; border-bottom: solid $accent; width: 100%; }
    .label { color: $text-muted; text-align: center; width: 100%; margin-top: 1; }
    """

    def __init__(self, job_id: str):
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
                        grid.add_row(Text("Ave RSS (Mem):"), Text(parts[1], style="green"))
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
                for token in tokens:
                    if "=" in token:
                        key, value = token.split("=", 1)
                        if key in interesting_keys:
                            parsed_map[key] = value
                for key, value in parsed_map.items():
                    grid.add_row(key, value)
                yield Static(grid)
            yield Label("\n[Press ESC or Enter to close]", classes="label")

    def key_escape(self):
        self.dismiss()

    def key_enter(self):
        self.dismiss()


class JobFilterScreen(ModalScreen[dict[str, str] | None]):
    CSS = """
    JobFilterScreen { align: center middle; background: rgba(0,0,0,0.72); }
    #filter-dialog { width: 74; height: auto; background: $surface; border: solid $accent; padding: 1 2; }
    .header { text-style: bold; color: $accent; border-bottom: solid $accent; width: 100%; margin-bottom: 1; }
    .hint { color: $text-muted; margin-bottom: 1; width: 100%; }
    .field-label { text-style: bold; margin-top: 1; width: 100%; }
    #button-row { align: center middle; height: auto; width: 100%; margin-top: 2; }
    Button { margin: 0 1; }
    .label { color: $text-muted; text-align: center; width: 100%; margin-top: 1; }
    """

    def __init__(self, current_user: str = "", current_prefix: str = ""):
        super().__init__()
        self.current_user = current_user
        self.current_prefix = current_prefix

    def compose(self) -> ComposeResult:
        with Container(id="filter-dialog"):
            yield Label("🔎 Job Filter", classes="header")
            yield Label(
                "Case-insensitive matching. User + prefix filters are combined with AND.",
                classes="hint",
            )
            yield Label("User (exact)", classes="field-label")
            yield Input(value=self.current_user, id="filter-user-input")
            yield Label("Name prefix (starts with)", classes="field-label")
            yield Input(value=self.current_prefix, id="filter-prefix-input")
            with Horizontal(id="button-row"):
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Clear", variant="warning", id="clear")
                yield Button("Cancel", id="cancel")
            yield Label("[Enter apply • Esc cancel]", classes="label")

    def on_mount(self) -> None:
        self.query_one("#filter-user-input", Input).focus()

    def _collect_filters(self) -> dict[str, str]:
        user_value = self.query_one("#filter-user-input", Input).value.strip()
        prefix_value = self.query_one("#filter-prefix-input", Input).value.strip()
        return {"user": user_value, "prefix": prefix_value}

    def _apply(self) -> None:
        self.dismiss(self._collect_filters())

    def key_enter(self) -> None:
        self._apply()

    def key_escape(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply":
            self._apply()
        elif event.button.id == "clear":
            self.dismiss({"user": "", "prefix": ""})
        else:
            self.dismiss(None)


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
                        ("Filters", "Use / to filter jobs by user and name prefix."),
                        ("m", "Toggle Normal/Edit mode."),
                    ],
                )
                yield Static(mode_table)

                normal_table = make_table(
                    "Normal Mode",
                    [
                        ("j / k", "Move down/up in the focused table."),
                        (
                            "h / l",
                            "Scroll jobs table left/right (when Jobs pane is focused).",
                        ),
                        ("Shift+Left / Shift+H", "Focus Nodes pane."),
                        ("Shift+Right / Shift+L", "Focus Jobs pane."),
                        ("c", "Toggle compact jobs view."),
                        ("/", "Open job filter dialog (user and name prefix)."),
                        ("z", "Clear all active job filters."),
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
                filter_table = make_table(
                    "Filters",
                    [
                        ("User filter", "Exact user match (case-insensitive)."),
                        ("Name prefix", "Job name starts-with match (case-insensitive)."),
                        ("Combination", "Both fields are combined with AND."),
                        ("Persistence", "Filters stay active across auto-refresh."),
                    ],
                )
                yield Static(filter_table)

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
