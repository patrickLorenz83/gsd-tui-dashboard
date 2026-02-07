import re
from pathlib import Path
from typing import Dict, List, Optional, Any

class GSDParser:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.planning_path = project_path / ".planning"

    def parse_project(self) -> Dict[str, Any]:
        """Parses PROJECT.md for active tasks and other info."""
        project_file = self.planning_path / "PROJECT.md"
        if not project_file.exists():
            return {"active_tasks": []}

        content = project_file.read_text(encoding="utf-8")
        active_tasks = []
        
        # Simple finite state machine to find "### Active" section
        lines = content.splitlines()
        in_active_section = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("### Active"):
                in_active_section = True
                continue
            elif line.startswith("### ") and in_active_section:
                in_active_section = False
                break
            
            if in_active_section and line.startswith("- ["):
                # Check if checked
                checked = line.startswith("- [x]")
                text = line[5:].strip()
                active_tasks.append({"text": text, "checked": checked})
                
        return {"active_tasks": active_tasks}

    def parse_roadmap(self) -> Dict[str, Any]:
        """Parses ROADMAP.md for phases."""
        roadmap_file = self.planning_path / "ROADMAP.md"
        if not roadmap_file.exists():
            return {"phases": []}

        content = roadmap_file.read_text(encoding="utf-8")
        phases = []
        
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            # Match lines like "- [x] **Phase 1: Title** - Description"
            # or "- [ ] **Phase 6: Title**"
            match = re.match(r"- \[(?P<status>.)\] \*\*(?P<name>Phase [\d\.]+:.*?)\*\*(?: - (?P<desc>.*))?", line)
            if match:
                status_char = match.group("status")
                name = match.group("name")
                desc = match.group("desc") or ""
                
                status = "completed" if status_char.lower() == "x" else "pending"
                if status_char == "/": # In progress
                     status = "in_progress"

                phases.append({
                    "name": name,
                    "description": desc,
                    "status": status
                })
        
        return {"phases": phases}

    def infer_active_phase_from_roadmap(self) -> Optional[Dict[str, Any]]:
        """Infers the active phase based on the first non-completed phase in ROADMAP.md."""
        roadmap = self.parse_roadmap()
        for phase in roadmap.get("phases", []):
            if phase["status"] != "completed":
                return phase
        return None

    def parse_state(self) -> Dict[str, Any]:
        """Parses STATE.md for progress and status."""
        state_file = self.planning_path / "STATE.md"
        if not state_file.exists():
            return {}

        content = state_file.read_text(encoding="utf-8")
        data = {}
        
        # Extract Phase info
        phase_match = re.search(r"Phase: (\d+ of \d+ \(.*?\))", content)
        if phase_match:
            data["current_phase"] = phase_match.group(1)
            
        # Extract Progress
        progress_match = re.search(r"Progress: \[.*?\] (\d+%)", content)
        if progress_match:
            data["progress_percent"] = int(progress_match.group(1).replace("%", ""))
        else:
             data["progress_percent"] = 0

        # Extract Last Activity
        activity_match = re.search(r"Last activity: (.*)", content)
        if activity_match:
            data["last_activity"] = activity_match.group(1)
            
        # Velocity / Specs
        velocity_match = re.search(r"Average duration: (.*)", content)
        if velocity_match:
            data["avg_duration"] = velocity_match.group(1)

        # Extract Status
        status_match = re.search(r"Status: (.*)", content)
        if status_match:
            data["phase_status"] = status_match.group(1).strip()

        return data

    def get_phase_directory(self) -> Optional[Path]:
        """Finds the directory for the current phase."""
        # Try state first
        state = self.parse_state()
        phase_num = None
        
        if "current_phase" in state:
             match = re.search(r"^(\d+)", state["current_phase"])
             if match:
                 phase_num = match.group(1).zfill(2)
        
        # If no phase num from state or state says complete, try roadmap inference
        # Actually, let's prioritize roadmap if state says "complete" or if we want the "next" phase
        # But for now, let's just fallback to roadmap if state is missing or we want to be smarter
        
        if not phase_num:
             active_phase = self.infer_active_phase_from_roadmap()
             if active_phase:
                  match = re.search(r"Phase (\d+)", active_phase['name'])
                  if match:
                       phase_num = match.group(1).zfill(2)

        if not phase_num:
            return None
            
        phases_dir = self.planning_path / "phases"
        
        if not phases_dir.exists():
            return None
            
        # Find folder starting with phase_num
        for child in phases_dir.iterdir():
            if child.is_dir() and child.name.startswith(phase_num):
                return child
        return None



    def parse_phase_docs(self) -> Dict[str, str]:
        """Reads content of Context, Research, and Verification docs for active phase."""
        phase_dir = self.get_phase_directory()
        docs = {}
        
        if not phase_dir:
            return docs

        # Pattern matching for files
        # e.g. 05-CONTEXT.md, 05-RESEARCH.md, 05-VERIFICATION.md
        # Or just *CONTEXT.md, *RESEARCH.md
        
        for file in phase_dir.glob("*.md"):
            if "CONTEXT" in file.name:
                docs["context"] = file.read_text(encoding="utf-8")
            elif "RESEARCH" in file.name:
                docs["research"] = file.read_text(encoding="utf-8")
            elif "VERIFICATION" in file.name:
                docs["verification"] = file.read_text(encoding="utf-8")
            elif "PLAN" in file.name:
                # Store plans in a list or specific key?
                # Let's accumulate plans
                if "plans" not in docs:
                    docs["plans"] = []
                docs["plans"].append({"name": file.name, "content": file.read_text(encoding="utf-8")})
        
        # Sort plans by name
        if "plans" in docs:
            docs["plans"].sort(key=lambda x: x["name"])
            
        return docs

    def parse_pending_todos(self) -> List[Dict[str, Any]]:
        """Parses pending todos from .planning/todos/pending directory."""
        todos_dir = self.planning_path / "todos" / "pending"
        if not todos_dir.exists():
            return []
            
        todos = []
        for file in todos_dir.glob("*.md"):
            # prettify filename: 2026-02-07-settings-detail-page-refactor.md -> Settings detail page refactor
            name = file.stem
            # Remove date prefix if present
            name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
            # Replace dashes with spaces
            name = name.replace("-", " ")
            # Capitalize
            name = name.capitalize()
            
            todos.append({"text": name, "checked": False})
            
        return todos

    def get_latest_phase_summary(self) -> Optional[str]:
        """Gets the content of the latest SUMMARY.md in the current phase."""
        phase_dir = self.get_phase_directory()
        if not phase_dir:
            return None
            
        summary_files = sorted(list(phase_dir.glob("*-SUMMARY.md")))
        if not summary_files:
            return None
            
        # Get the last one (latest)
        latest = summary_files[-1]
        return latest.read_text(encoding="utf-8")

    def get_all_data(self) -> Dict[str, Any]:
        """Aggregates all data."""
        return {
            "project": self.parse_project(),
            "roadmap": self.parse_roadmap(),
            "state": self.parse_state(),
            "phase_docs": self.parse_phase_docs(),
            "pending_todos": self.parse_pending_todos(),
            "latest_summary": self.get_latest_phase_summary(),
        }
