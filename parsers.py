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

        return data

    def get_phase_directory(self) -> Optional[Path]:
        """Finds the directory for the current phase."""
        state = self.parse_state()
        if "current_phase" not in state:
            return None
        
        # Extract phase number, e.g. "5" from "5 of 7 (Live Preview Panel)"
        match = re.search(r"^(\d+)", state["current_phase"])
        if not match:
            return None
            
        phase_num = match.group(1).zfill(2) # "05"
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

    def get_all_data(self) -> Dict[str, Any]:
        """Aggregates all data."""
        return {
            "project": self.parse_project(),
            "roadmap": self.parse_roadmap(),
            "state": self.parse_state(),
            "phase_docs": self.parse_phase_docs(),
        }
