from pathlib import Path
import sys
import argparse
from typing import Dict, Any

from textual.widgets import Header, Footer, Label, ProgressBar, Static, DataTable, TabbedContent, TabPane, Markdown
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.binding import Binding
from rich.markdown import Markdown as RichMarkdown

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from parsers import GSDParser

class DashboardData(Static):
    """Holds the data and updates the UI."""
    def __init__(self, parser: GSDParser):
        super().__init__()
        self.parser = parser

import re

class PulseLabel(Label):
    def on_mount(self):
        self.pulse()

    def pulse(self):
        self.styles.animate("opacity", 0.3, duration=0.8, on_complete=lambda: self.styles.animate("opacity", 1.0, duration=0.8, on_complete=self.pulse))

class RoadmapView(Static):
    def compose(self) -> ComposeResult:
        yield Label("Roadmap", id="roadmap-header")
        yield Vertical(id="roadmap-list")

    def update_roadmap(self, phases, current_phase_info=None, phase_status=None):
        container = self.query_one("#roadmap-list")
        container.remove_children()
        
        # Extract phase number from "6 of 7 (Template Versioning)" -> "6"
        current_phase_num = None
        if current_phase_info:
            # Try "6 of 7" format first
            match = re.search(r"^(\d+)", current_phase_info)
            if match:
                current_phase_num = int(match.group(1))
            else:
                # Try "Phase 6" format
                match = re.search(r"Phase (\d+)", current_phase_info)
                if match:
                     current_phase_num = int(match.group(1))

        for phase in phases:
            status = phase.get("status", "pending")
            icon = "○"
            if status == "completed":
                icon = "●"
            elif status == "in_progress":
                icon = "◐"
            
            label_text = f"{icon} {phase['name']}"
            
            is_active = False
            # Extract phase number from "Phase 6: Template Versioning" -> "6"
            phase_match = re.search(r"Phase (\d+)", phase['name'])
            if phase_match and current_phase_num is not None:
                if int(phase_match.group(1)) == current_phase_num:
                    is_active = True
            
            # If the current phase is marked as completed in state, don't pulse it
            if is_active and phase_status and "complete" in phase_status.lower():
                is_active = False
            
            if is_active:
                label = PulseLabel(label_text)
                label.add_class("active-phase")
            else:
                label = Label(label_text)
            
            container.mount(label)

class PendingTodosView(Static):
    def compose(self) -> ComposeResult:
        yield Label("Pending Todos", id="active-header")
        yield Vertical(id="active-list")

    def update_todos(self, todos):
        container = self.query_one("#active-list")
        container.remove_children()
        
        if not todos:
             container.mount(Label("No pending todos found."))
             return

        for todo in todos:
            # We don't really have checked status for pending todos (they are files)
            # But let's keep the UI consistent or just show a bullet
            icon = "•" 
            container.mount(Label(f"{icon} {todo['text']}"))

class ProjectStatsView(Static):
    def compose(self) -> ComposeResult:
        yield Label("Project Stats", id="stats-header")
        yield Label("Phase: Loading...", id="stats-phase")
        yield Label("Last Activity: Loading...", id="stats-activity")
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Label("0%", id="progress-label")

    def update_stats(self, state):
        self.query_one("#stats-phase").update(f"Phase: {state.get('current_phase', 'N/A')}")
        self.query_one("#stats-activity").update(f"Last Activity: {state.get('last_activity', 'N/A')}")
        
        progress = state.get("progress_percent", 0)
        self.query_one("#progress-bar").update(progress=progress)
        self.query_one("#progress-label").update(f"{progress}%")

class FocusableMarkdown(Container):
    """A scrollable container for Markdown content that handles focus."""
    can_focus = True
    can_focus_children = False
    
    BINDINGS = [
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("up", "scroll_up", "Scroll Up"),
        ("pageup", "page_up", "Page Up"),
        ("pagedown", "page_down", "Page Down"),
        ("home", "scroll_home", "Home"),
        ("end", "scroll_end", "End"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(id="inner-markdown")

    def update(self, markdown_text: str):
        try:
             self.query_one("#inner-markdown", Static).update(RichMarkdown(markdown_text))
        except Exception:
             pass

class GSDDashboardApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main-container {
        height: 100%;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    ContentSwitcher {
        height: 100%;
    }
    
    TabPane {
        height: 100%;
        padding: 0;
    }

    /* Dashboard Tab Layout */
    .dashboard-grid {
        height: 100%;
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr;
    }

    #left-pane {
        height: 100%;
        border-right: solid green;
    }
    
    #right-pane {
        height: 100%;
    }

    #roadmap-header, #active-header, #stats-header {
        background: $primary;
        color: $text;
        dock: top;
        text-align: center;
        padding: 1;
    }

    .box {
        height: 100%;
        overflow: auto;
    }
    
    #stats-container {
        height: auto;
        border-bottom: solid blue;
        padding: 1;
    }
    
    FocusableMarkdown {
        height: 100%;
        overflow-y: auto; 
    }
    
    FocusableMarkdown:focus {
        border: solid green;
    }
    
    FocusableMarkdown > Static {
        height: auto;
        padding: 1;
    }
    
    .active-phase {
        color: $success;
        text-style: bold;
        background: $accent 20%;
    }
    """

    auto_refresh = reactive(True)

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_data", "Refresh Data"),
        ("t", "toggle_refresh", "Toggle Auto-Refresh"),
        ("left", "prev_tab", "Previous Tab"),
        ("right", "next_tab", "Next Tab"),
    ]

    TABS = ["dashboard", "summary", "context", "research", "plans", "review"]

    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path
        self.parser = GSDParser(project_path)
        self.observer = None

    def compose(self) -> ComposeResult:
        yield Header()
        
        with TabbedContent(initial="dashboard", id="tab-content"):
            with TabPane("Dashboard", id="dashboard"):
                # Focusing on the dashboard grid container to allow scrolling if needed
                with Container(classes="dashboard-grid", id="dashboard-container"):
                    with Vertical(id="left-pane"):
                        yield RoadmapView(id="roadmap-view")
                    with Vertical(id="right-pane"):
                        yield ProjectStatsView(id="stats-view")
                        yield PendingTodosView(id="active-tasks-view")
            
            with TabPane("Summary", id="summary"):
                 yield FocusableMarkdown(id="md-summary", classes="scrollable-md")

            with TabPane("Context (Discuss)", id="context"):
                 yield FocusableMarkdown(id="md-context", classes="scrollable-md")
            
            with TabPane("Research", id="research"):
                 yield FocusableMarkdown(id="md-research", classes="scrollable-md")
                 
            with TabPane("Plans", id="plans"):
                 yield FocusableMarkdown(id="md-app-plans", classes="scrollable-md")
                 
            with TabPane("Review (Verify)", id="review"):
                 yield FocusableMarkdown(id="md-review", classes="scrollable-md")

        yield Footer()

    def on_mount(self):
        self.action_refresh_data()
        self.start_watcher()
        self.update_title()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated):
        """Focus the content of the activated tab."""
        pane_id = event.pane.id
        
        if pane_id == "dashboard":
            pass
        elif pane_id == "summary":
            self.query_one("#md-summary").focus(scroll_visible=False)
        elif pane_id == "context":
            self.query_one("#md-context").focus(scroll_visible=False)
        elif pane_id == "research":
            self.query_one("#md-research").focus(scroll_visible=False)
        elif pane_id == "plans":
             self.query_one("#md-app-plans").focus(scroll_visible=False)
        elif pane_id == "review":
             self.query_one("#md-review").focus(scroll_visible=False)

    def action_next_tab(self):
        self._switch_tab(1)

    def action_prev_tab(self):
        self._switch_tab(-1)

    def _switch_tab(self, delta):
        tabbed_content = self.query_one("#tab-content", TabbedContent)
        current_tab = tabbed_content.active
        
        try:
            idx = self.TABS.index(current_tab)
            new_idx = (idx + delta) % len(self.TABS)
            tabbed_content.active = self.TABS[new_idx]
        except ValueError:
            pass 
            
    def update_title(self):
        status = "ON" if self.auto_refresh else "OFF"
        self.title = f"GSD Dashboard - {self.project_path.name} [Auto-Refresh: {status}]"

    def watch_auto_refresh(self, value):
        self.update_title()
        if value:
            self.notify("Auto-Refresh Enabled")
            self.action_refresh_data()
        else:
            self.notify("Auto-Refresh Disabled")

    def action_toggle_refresh(self):
        self.auto_refresh = not self.auto_refresh

    def action_refresh_data(self):
        # Parse data
        data = self.parser.get_all_data()
        project_data = data.get("project", {})
        roadmap_data = data.get("roadmap", {})
        state_data = data.get("state", {})
        phase_docs = data.get("phase_docs", {})
        
        pending_todos = data.get("pending_todos", [])
        latest_summary = data.get("latest_summary", "*No summary found for current phase.*")
        
        current_phase = state_data.get('current_phase', '')
        phase_status = state_data.get('phase_status', '')
        inferred_phase = data.get("inferred_active_phase")

        # If the state says the current phase is complete, but we have an inferred "next" phase
        # from the roadmap that is pending/in-progress, use that for highlighting.
        target_phase_info = current_phase
        target_status = phase_status

        if phase_status and "complete" in phase_status.lower() and inferred_phase:
             target_phase_info = inferred_phase['name']
             target_status = "in_progress" # Force it to look active so it pulses

        # Update Views
        self.query_one("#roadmap-view").update_roadmap(roadmap_data.get("phases", []), target_phase_info, target_status)
        self.query_one("#stats-view").update_stats(state_data)
        self.query_one("#active-tasks-view").update_todos(pending_todos)
        
        # Update Markdown Tabs
        self.query_one("#md-summary").update(latest_summary)
        
        # Update Markdown Tabs
        self.query_one("#md-context").update(phase_docs.get("context", "*No Context document found for current phase.*"))
        self.query_one("#md-research").update(phase_docs.get("research", "*No Research document found for current phase.*"))
        self.query_one("#md-review").update(phase_docs.get("verification", "*No Verification document found for current phase.*"))
        
        # Helper for plans
        plans = phase_docs.get("plans", [])
        if plans:
            # Concatenate plans or show latest? Let's show all for now separated by lines
            plan_md = ""
            for p in plans:
                plan_md += f"# {p['name']}\n\n{p['content']}\n\n---\n\n"
            self.query_one("#md-app-plans").update(plan_md)
        else:
             self.query_one("#md-app-plans").update("*No Plans found for current phase.*")

    def start_watcher(self):
        event_handler = Handler(self)
        self.observer = Observer()
        planning_path = self.project_path / ".planning"
        if planning_path.exists():
            self.observer.schedule(event_handler, str(planning_path), recursive=True)
            self.observer.start()

    def on_unmount(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

class Handler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_modified(self, event):
        if event.is_directory:
            return
        if not self.app.auto_refresh:
            return
        if event.src_path.endswith(".md"):
            self.app.call_from_thread(self.app.action_refresh_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, default=".")
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    app = GSDDashboardApp(path)
    app.run()
