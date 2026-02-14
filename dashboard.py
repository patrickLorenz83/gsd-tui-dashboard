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

__version__ = "0.0.2"

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
    EXPAND_LEVELS = [3, 5, 10, None]  # None = show all

    def compose(self) -> ComposeResult:
        yield Label("Roadmap", id="roadmap-header")
        yield Vertical(id="roadmap-list")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._expand_index = 0
        self._max_visible = self.EXPAND_LEVELS[0]

    def cycle_expand(self):
        self._expand_index = (self._expand_index + 1) % len(self.EXPAND_LEVELS)
        self._max_visible = self.EXPAND_LEVELS[self._expand_index]

    def get_expand_label(self) -> str:
        if self._max_visible is None:
            return "All"
        return str(self._max_visible)

    def update_roadmap(self, phases, current_phase_info=None, phase_status=None):
        container = self.query_one("#roadmap-list")
        try:
            container.remove_children()

            if not phases:
                container.mount(Label("No roadmap available.", classes="empty-state"))
                return

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

            # Collapse old completed phases: count leading completed/shipped
            leading_completed = 0
            for phase in phases:
                if phase.get("status") in ("completed", "shipped"):
                    leading_completed += 1
                else:
                    break

            # How many to keep visible
            max_visible = self._max_visible if self._max_visible is not None else leading_completed
            collapse_count = max(0, leading_completed - max_visible)

            if collapse_count > 0:
                label = Label(f"  ● {collapse_count} earlier phases completed")
                label.add_class("collapsed-phases")
                container.mount(label)

            for i, phase in enumerate(phases):
                # Skip collapsed phases
                if i < collapse_count:
                    continue

                status = phase.get("status", "pending")
                icon = "○"
                if status in ("completed", "shipped"):
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
        except Exception as e:
            container.mount(Label(f"Error displaying roadmap: {str(e)}"))

class TodosView(Static):
    def compose(self) -> ComposeResult:
        yield Label("Todos", id="active-header")
        yield Vertical(id="active-list")

    def update_todos(self, pending, completed):
        container = self.query_one("#active-list")
        try:
            container.remove_children()

            if not pending and not completed:
                container.mount(Label("No todos found.", classes="empty-state"))
                return

            # Pending section
            if pending:
                for todo in pending:
                    text = todo.get("text", "Unknown todo")
                    container.mount(Label(f"  • {text}"))

            # Separator
            if pending and completed:
                container.mount(Label(""))

            # Completed section
            if completed:
                for todo in completed:
                    text = todo.get("text", "Unknown todo")
                    label = Label(f"  ✓ {text}")
                    label.add_class("completed-todo")
                    container.mount(label)
        except Exception as e:
            container.mount(Label(f"Error displaying todos: {str(e)}"))

class ConcernsView(Static):
    def compose(self) -> ComposeResult:
        yield Label("Blockers / Concerns", id="concerns-header")
        yield Vertical(id="concerns-list")

    def update_concerns(self, concerns):
        container = self.query_one("#concerns-list")
        try:
            container.remove_children()

            if not concerns:
                container.mount(Label("No concerns.", classes="empty-state"))
                return

            for concern in concerns:
                text = concern.get("text", "Unknown concern")
                label = Label(f"  \u26a0 {text}")
                label.add_class("concern-item")
                container.mount(label)
        except Exception as e:
            container.mount(Label(f"Error displaying concerns: {str(e)}"))

class ProjectStatsView(Static):
    def compose(self) -> ComposeResult:
        yield Label("Project Stats", id="stats-header")
        yield Label("Phase: Loading...", id="stats-phase")
        yield Label("Last Activity: Loading...", id="stats-activity")
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Label("0%", id="progress-label")

    def update_stats(self, state):
        try:
            milestone_complete = state.get("milestone_complete", False)

            if milestone_complete:
                version = state.get("milestone_version", "")
                phase_text = f"Milestone {version} Complete!" if version else "Milestone Complete!"
                self.query_one("#stats-phase").update(phase_text)
                self.query_one("#progress-bar").update(progress=100)
                self.query_one("#progress-label").update("100%")
            else:
                current_phase = state.get("current_phase", "N/A")
                self.query_one("#stats-phase").update(f"Phase: {current_phase}")
                progress = state.get("progress_percent", 0)
                self.query_one("#progress-bar").update(progress=progress)
                self.query_one("#progress-label").update(f"{progress}%")

            last_activity = state.get("last_activity", "N/A")
            self.query_one("#stats-activity").update(f"Last Activity: {last_activity}")
        except Exception as e:
            try:
                self.query_one("#stats-phase").update(f"Error: {str(e)}")
            except Exception:
                pass

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

    #roadmap-header, #active-header, #stats-header, #concerns-header {
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
    
    #right-pane Label, #right-pane Static {
        width: 100%;
    }

    .collapsed-phases {
        color: $text-muted;
        text-style: dim italic;
    }

    .active-phase {
        color: $success;
        text-style: bold;
        background: $accent 20%;
    }

    .completed-todo {
        color: $text-muted;
        text-style: dim;
    }

    .concern-item {
        color: orange;
    }

    .empty-state {
        color: $text-muted;
        text-style: italic;
    }
    """

    auto_refresh = reactive(True)

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_data", "Refresh Data"),
        ("t", "toggle_refresh", "Toggle Auto-Refresh"),
        ("e", "expand_roadmap", "Expand Roadmap"),
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
                        yield TodosView(id="active-tasks-view")
                        yield ConcernsView(id="concerns-view")
            
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

    def action_expand_roadmap(self):
        roadmap_view = self.query_one("#roadmap-view", RoadmapView)
        roadmap_view.cycle_expand()
        self.notify(f"Roadmap: show last {roadmap_view.get_expand_label()}")
        self.action_refresh_data()

    def action_refresh_data(self):
        try:
            data = self.parser.get_all_data()
            project_data = data.get("project", {})
            roadmap_data = data.get("roadmap", {})
            state_data = data.get("state", {})
            phase_docs = data.get("phase_docs", {})

            pending_todos = data.get("pending_todos", [])
            completed_todos = data.get("completed_todos", [])
            concerns = data.get("concerns", [])
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
                 target_status = "in_progress"

            # Update Views
            self.query_one("#roadmap-view").update_roadmap(roadmap_data.get("phases", []), target_phase_info, target_status)
            self.query_one("#stats-view").update_stats(state_data)
            self.query_one("#active-tasks-view").update_todos(pending_todos, completed_todos)
            self.query_one("#concerns-view").update_concerns(concerns)

            # Update Markdown Tabs
            self.query_one("#md-summary").update(latest_summary)

            self.query_one("#md-context").update(phase_docs.get("context", "*No Context document found for current phase.*"))
            self.query_one("#md-research").update(phase_docs.get("research", "*No Research document found for current phase.*"))
            self.query_one("#md-review").update(phase_docs.get("verification", "*No Verification document found for current phase.*"))

            plans = phase_docs.get("plans", [])
            if plans:
                plan_md = ""
                for p in plans:
                    plan_md += f"# {p['name']}\n\n{p['content']}\n\n---\n\n"
                self.query_one("#md-app-plans").update(plan_md)
            else:
                 self.query_one("#md-app-plans").update("*No Plans found for current phase.*")
        except Exception as e:
            self.notify(f"Refresh error: {str(e)}", severity="error")

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

    def on_any_event(self, event):
        if event.is_directory:
            return
        if not self.app.auto_refresh:
            return
        src = getattr(event, "src_path", "") or ""
        dest = getattr(event, "dest_path", "") or ""
        if src.endswith(".md") or dest.endswith(".md"):
            self.app.call_from_thread(self.app.action_refresh_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, default=".")
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    app = GSDDashboardApp(path)
    app.run()
