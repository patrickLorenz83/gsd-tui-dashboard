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

    def _parse_checkbox_phase(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse checkbox format phase line.

        Examples:
            - [x] **Phase 1: Setup** - Initial setup
            - [ ] **Phase 2: Implementation**
            - [/] **Phase 3: Testing** - Run tests

        Returns:
            Dict with name, description, and status, or None if not a match.
        """
        # Updated regex to handle extra whitespace more flexibly
        match = re.match(
            r"- \[(?P<status>.)\]\s*\*\*(?P<name>Phase\s+[\d\.]+:.*?)\*\*(?:\s*-\s*(?P<desc>.*))?$",
            line.strip()
        )
        if not match:
            return None

        status_char = match.group("status")
        name = match.group("name")
        desc = match.group("desc") or ""

        # Map checkbox status to standard status
        status_map = {"x": "completed", "X": "completed", "/": "in_progress", " ": "pending"}
        status = status_map.get(status_char, "pending")

        return {
            "name": name,
            "description": desc.strip(),
            "status": status
        }

    def _parse_table_phase(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse table format phase line.

        Examples:
            | 1. Foundation | v1.0 | 3/3 | Complete |
            | 2. Features | v1.0 | 5/5 | In Progress |
            | 3. Polish | v1.0 | 0/2 | Not started |

        Returns:
            Dict with name, description, and status, or None if not a valid table row.
        """
        stripped = line.strip()
        if not stripped.startswith("|"):
            return None

        # Split by | and clean up
        parts = [p.strip() for p in stripped.split("|") if p.strip()]

        # Need at least 4 columns: Phase, Milestone, Plans, Status
        if len(parts) < 4:
            return None

        # Skip header row (contains "Phase" as first word) and separator row
        first_part = parts[0].lower()
        if "phase" in first_part or parts[0].startswith("-"):
            return None

        # Extract phase number and title from first column
        # Format: "1. Title" or "1. Title text"
        phase_match = re.match(r"(\d+)\.\s*(.*)", parts[0])
        if not phase_match:
            return None

        phase_num = phase_match.group(1)
        phase_title = phase_match.group(2).strip()

        # Extract status from last column (4th column)
        status_text = parts[3].lower()

        # Map status text to standard status
        if "complete" in status_text or "shipped" in status_text:
            status = "completed"
        elif "progress" in status_text or "active" in status_text:
            status = "in_progress"
        else:
            status = "pending"

        return {
            "name": f"Phase {phase_num}: {phase_title}",
            "description": "",
            "status": status
        }

    def _parse_shipped_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse SHIPPED milestone line.

        Examples:
            - SHIPPED **v1.0 Parser Stabilization** — Phases 1-7
            - SHIPPED **v2.0 Feature Set** - Phases 1-3

        Returns:
            Dict with version, name, phases, and status="shipped", or None if not a match.
        """
        # Match SHIPPED lines with em dash (—) or regular dash (-)
        match = re.match(
            r"- SHIPPED\s+\*\*(?P<version>v[\d\.]+)\s+(?P<name>.*?)\*\*\s*[—\-]\s*Phases?\s*(?P<phases>[\d\-,\s]+)",
            line.strip()
        )
        if not match:
            return None

        version = match.group("version")
        name = match.group("name").strip()
        phases = match.group("phases").strip()

        return {
            "name": f"{version} {name}",
            "description": f"Phases {phases}",
            "status": "shipped",
            "version": version,
            "phases": phases
        }

    def parse_roadmap(self) -> Dict[str, Any]:
        """
        Parses ROADMAP.md for phases, supporting multiple formats:
        - Checkbox format: - [x] **Phase 1: Title** - Description
        - Table format: | 1. Title | v1.0 | 3/3 | Complete |
        - SHIPPED lines: - SHIPPED **v1.0 Title** — Phases 1-3

        Returns:
            Dict with 'phases' key containing list of phase dicts.
        """
        roadmap_file = self.planning_path / "ROADMAP.md"
        if not roadmap_file.exists():
            return {"phases": []}

        content = roadmap_file.read_text(encoding="utf-8")
        phases = []

        for line in content.splitlines():
            stripped = line.strip()

            # Try checkbox format first (most common during active development)
            result = self._parse_checkbox_phase(stripped)
            if result:
                phases.append(result)
                continue

            # Try SHIPPED line
            result = self._parse_shipped_line(stripped)
            if result:
                phases.append(result)
                continue

            # Try table format
            result = self._parse_table_phase(stripped)
            if result:
                phases.append(result)
                continue

        return {"phases": phases}

    def infer_active_phase_from_roadmap(self) -> Optional[Dict[str, Any]]:
        """Infers the active phase based on the first non-completed phase in ROADMAP.md."""
        roadmap = self.parse_roadmap()
        for phase in roadmap.get("phases", []):
            if phase["status"] != "completed":
                return phase
        return None

    def _parse_state_phase(self, content: str) -> Dict[str, Any]:
        """
        Parse phase info from STATE.md - handle multiple formats.

        Supports:
        - Format 1: "Phase: 5 of 7 (Template Versioning)"
        - Format 2: "Phase: v1.0 complete — 7 of 7 phases shipped"
        - Format 3: "Phase: Not started"
        - Format 4: Generic fallback - "Phase: anything"

        Returns:
            Dict with phase information (phase_number, total_phases, phase_name,
            milestone_complete, etc.) or empty dict if no phase line found.
        """
        result = {}

        # Format 1: "Phase: 5 of 7 (Template Versioning)"
        match = re.search(r"Phase:\s*(\d+)\s+of\s+(\d+)\s*\(([^)]+)\)", content)
        if match:
            result["phase_number"] = int(match.group(1))
            result["total_phases"] = int(match.group(2))
            result["phase_name"] = match.group(3)
            result["current_phase"] = f"{match.group(1)} of {match.group(2)} ({match.group(3)})"
            return result

        # Format 2: "Phase: v1.0 complete — 7 of 7 phases shipped"
        match = re.search(
            r"Phase:\s*(v[\d\.]+)\s+complete\s*[—\-]\s*(\d+)\s+of\s+(\d+)\s+phases?\s+shipped",
            content
        )
        if match:
            result["milestone_version"] = match.group(1)
            result["phases_shipped"] = int(match.group(2))
            result["total_phases"] = int(match.group(3))
            result["current_phase"] = f"{match.group(1)} complete"
            result["milestone_complete"] = True
            return result

        # Format 3: "Phase: Not started"
        match = re.search(r"Phase:\s*Not\s+started", content, re.IGNORECASE)
        if match:
            result["current_phase"] = "Not started"
            result["phase_status"] = "not_started"
            return result

        # Format 4: Generic fallback - "Phase: anything"
        match = re.search(r"Phase:\s*(.+?)(?:\n|$)", content)
        if match:
            result["current_phase"] = match.group(1).strip()

        return result

    def _parse_progress(self, content: str) -> int:
        """
        Extract progress percentage from various formats.

        Supports:
        - Format 1: "Progress: [██████░░░░] 60%"
        - Format 2: "100% (16/16 plans completed)"
        - Format 3: Simple percentage on Progress line

        Returns:
            Progress percentage as integer, or 0 if not found.
        """
        try:
            # Format 1: "Progress: [██████░░░░] 60%"
            match = re.search(r"Progress:\s*\[.*?\]\s*(\d+)%", content)
            if match:
                return int(match.group(1))

            # Format 2: "100% (16/16 plans completed)"
            match = re.search(r"(\d+)%\s*\(\d+/\d+\s+plans?\s+completed\)", content)
            if match:
                return int(match.group(1))

            # Format 3: Simple percentage on Progress line
            match = re.search(r"Progress:.*?(\d+)%", content)
            if match:
                return int(match.group(1))

            return 0
        except (ValueError, AttributeError):
            return 0

    def parse_state(self) -> Dict[str, Any]:
        """
        Parses STATE.md for progress and status.

        Supports multiple format variations for phase and progress information.
        Returns enriched dict with structured fields for dashboard consumption.
        """
        state_file = self.planning_path / "STATE.md"
        if not state_file.exists():
            return {}

        content = state_file.read_text(encoding="utf-8")
        data = {}

        # Extract phase info (multi-format)
        phase_data = self._parse_state_phase(content)
        data.update(phase_data)

        # Extract progress (multi-format)
        data["progress_percent"] = self._parse_progress(content)

        # Extract Last Activity
        activity_match = re.search(r"Last activity:\s*(.*)", content)
        if activity_match:
            data["last_activity"] = activity_match.group(1).strip()

        # Velocity / Specs
        velocity_match = re.search(r"Average duration:\s*(.*)", content)
        if velocity_match:
            data["avg_duration"] = velocity_match.group(1).strip()

        # Extract Status (if not already set by phase parser)
        status_match = re.search(r"Status:\s*(.*)", content)
        if status_match:
            if "phase_status" not in data:
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
