"""Comprehensive tests for GSDParser roadmap parsing functionality."""
import pytest
from pathlib import Path


class TestParseRoadmapCheckbox:
    """Tests for checkbox format roadmap parsing."""

    def test_parse_checkbox_completed(self, parser):
        """Test parsing completed phase in checkbox format."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("- [x] **Phase 1: Setup** - Initial setup\n")

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 1
        phase = result["phases"][0]
        assert phase["name"] == "Phase 1: Setup"
        assert phase["description"] == "Initial setup"
        assert phase["status"] == "completed"

    def test_parse_checkbox_pending(self, parser):
        """Test parsing pending phase in checkbox format."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("- [ ] **Phase 2: Implementation**\n")

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 1
        phase = result["phases"][0]
        assert phase["name"] == "Phase 2: Implementation"
        assert phase["description"] == ""
        assert phase["status"] == "pending"

    def test_parse_checkbox_in_progress(self, parser):
        """Test parsing in-progress phase in checkbox format."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("- [/] **Phase 3: Testing** - Run tests\n")

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 1
        phase = result["phases"][0]
        assert phase["name"] == "Phase 3: Testing"
        assert phase["description"] == "Run tests"
        assert phase["status"] == "in_progress"

    def test_parse_checkbox_decimal_phase(self, parser):
        """Test parsing phase with decimal number (e.g., 1.1)."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("- [x] **Phase 1.1: Hotfix** - Emergency fix\n")

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 1
        phase = result["phases"][0]
        assert phase["name"] == "Phase 1.1: Hotfix"
        assert phase["description"] == "Emergency fix"
        assert phase["status"] == "completed"

    def test_parse_checkbox_extra_whitespace(self, parser):
        """Test parsing with extra whitespace in checkbox format."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("- [x]  **Phase 1: Setup**  -  Initial setup\n")

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 1
        phase = result["phases"][0]
        assert phase["name"] == "Phase 1: Setup"
        # Description might have extra spaces - that's OK as long as it extracts
        assert "Initial setup" in phase["description"]
        assert phase["status"] == "completed"

    def test_parse_checkbox_multiple_phases(self, parser):
        """Test parsing multiple phases in checkbox format."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Roadmap

- [x] **Phase 1: Foundation** - Build core
- [/] **Phase 2: Features** - Add features
- [ ] **Phase 3: Polish** - Final polish
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 3
        assert result["phases"][0]["status"] == "completed"
        assert result["phases"][1]["status"] == "in_progress"
        assert result["phases"][2]["status"] == "pending"


class TestParseRoadmapTable:
    """Tests for table format roadmap parsing."""

    def test_parse_table_all_complete(self, parser):
        """Test parsing table format with all phases complete."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Milestone Progress

| Phase | Milestone | Plans | Status |
|-------|-----------|-------|--------|
| 1. Foundation | v1.0 | 3/3 | Complete |
| 2. Features | v1.0 | 5/5 | Complete |
| 3. Polish | v1.0 | 2/2 | Complete |
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 3
        assert result["phases"][0]["name"] == "Phase 1: Foundation"
        assert result["phases"][0]["status"] == "completed"
        assert result["phases"][1]["name"] == "Phase 2: Features"
        assert result["phases"][1]["status"] == "completed"
        assert result["phases"][2]["name"] == "Phase 3: Polish"
        assert result["phases"][2]["status"] == "completed"

    def test_parse_table_mixed_status(self, parser):
        """Test parsing table format with mixed statuses."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Milestone Progress

| Phase | Milestone | Plans | Status |
|-------|-----------|-------|--------|
| 1. Setup | v2.0 | 1/1 | Complete |
| 2. Core | v2.0 | 0/3 | In Progress |
| 3. UI | v2.0 | 0/2 | Not started |
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 3
        assert result["phases"][0]["status"] == "completed"
        assert result["phases"][1]["status"] == "in_progress"
        assert result["phases"][2]["status"] == "pending"

    def test_parse_table_skips_header(self, parser):
        """Test that table parser skips header and separator rows."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Milestone Progress

| Phase | Milestone | Plans | Status |
|-------|-----------|-------|--------|
| 1. Setup | v1.0 | 1/1 | Complete |
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        # Should only have 1 phase, not 3 (header + separator + data)
        assert len(result["phases"]) == 1
        assert result["phases"][0]["name"] == "Phase 1: Setup"

    def test_parse_table_dash_format(self, parser):
        """Test parsing table with dash-separated phase names: '1 - Foundation'."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Progress Tracking

| Phase | Status | Requirements | Success Criteria | Completion |
|-------|--------|--------------|------------------|------------|
| 1 - Foundation & Type Safety | ✓ Complete (2026-02-14) | 5 | 5 | 100% |
| 2 - LLM Provider Migration | Planned | 3 | 5 | 0% |
| 3 - MCP Server Integration | Pending | 7 | 6 | 0% |
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 3
        assert result["phases"][0]["name"] == "Phase 1: Foundation & Type Safety"
        assert result["phases"][0]["status"] == "completed"
        assert result["phases"][1]["name"] == "Phase 2: LLM Provider Migration"
        assert result["phases"][1]["status"] == "pending"
        assert result["phases"][2]["name"] == "Phase 3: MCP Server Integration"
        assert result["phases"][2]["status"] == "pending"

    def test_parse_table_with_shipped_status(self, parser):
        """Test parsing table format with 'Shipped' status."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Milestone Progress

| Phase | Milestone | Plans | Status |
|-------|-----------|-------|--------|
| 1. Core | v1.0 | 5/5 | Shipped |
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 1
        assert result["phases"][0]["status"] == "completed"


class TestParseRoadmapShipped:
    """Tests for SHIPPED line parsing."""

    def test_parse_shipped_line(self, parser):
        """Test parsing SHIPPED milestone line."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("- SHIPPED **v1.0 Parser Stabilization** — Phases 1-7\n")

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 1
        phase = result["phases"][0]
        assert "v1.0" in phase["name"] or phase.get("version") == "v1.0"
        assert "Parser Stabilization" in phase["name"]
        assert phase["status"] == "shipped" or phase["status"] == "completed"

    def test_parse_shipped_with_checkbox_phases(self, parser):
        """Test parsing SHIPPED line followed by new checkbox phases."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Roadmap

## Shipped Milestones

- SHIPPED **v1.0 Core Features** — Phases 1-3

## Current Milestone: v2.0

- [x] **Phase 1: Refactor** - Code cleanup
- [ ] **Phase 2: New Feature** - Add feature
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        # Should have 3 phases: 1 shipped + 2 current
        assert len(result["phases"]) == 3

        # First phase should be shipped/completed
        assert result["phases"][0]["status"] in ["shipped", "completed"]

        # Next phases should be checkbox format
        assert result["phases"][1]["name"] == "Phase 1: Refactor"
        assert result["phases"][1]["status"] == "completed"
        assert result["phases"][2]["name"] == "Phase 2: New Feature"
        assert result["phases"][2]["status"] == "pending"

    def test_parse_shipped_multiple_versions(self, parser):
        """Test parsing multiple SHIPPED lines."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Roadmap

## Shipped Milestones

- SHIPPED **v1.0 Initial Release** — Phases 1-5
- SHIPPED **v1.1 Bug Fixes** — Phases 6-7
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        assert len(result["phases"]) == 2
        assert all(p["status"] in ["shipped", "completed"] for p in result["phases"])


class TestParseRoadmapEdgeCases:
    """Tests for edge cases and error handling."""

    def test_parse_empty_file(self, parser):
        """Test parsing empty ROADMAP.md."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("")

        result = parser.parse_roadmap()

        assert result == {"phases": []}

    def test_parse_file_no_phases(self, parser):
        """Test parsing file with content but no phase lines."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Roadmap

This is a roadmap document with no actual phases yet.

Just some text.
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        assert result == {"phases": []}

    def test_parse_missing_file(self, parser):
        """Test parsing when ROADMAP.md doesn't exist."""
        # Don't create the file
        result = parser.parse_roadmap()

        assert result == {"phases": []}

    def test_parse_mixed_formats(self, parser):
        """Test parsing file with mixed checkbox, table, and SHIPPED formats."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """# Roadmap

## Shipped Milestones

- SHIPPED **v1.0 Core** — Phases 1-3

## v2.0 Milestone Progress

| Phase | Milestone | Plans | Status |
|-------|-----------|-------|--------|
| 1. Migration | v2.0 | 2/2 | Complete |

## Current Work

- [/] **Phase 2: New Features** - Adding features
- [ ] **Phase 3: Testing** - Test everything
"""
        roadmap.write_text(content)

        result = parser.parse_roadmap()

        # Should parse all formats: 1 shipped + 1 table + 2 checkbox = 4 phases
        assert len(result["phases"]) == 4


class TestInferActivePhase:
    """Tests for infer_active_phase_from_roadmap functionality."""

    def test_infer_active_first_pending(self, parser):
        """Test inferring active phase returns first pending phase."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """- [x] **Phase 1: Done** - Completed
- [ ] **Phase 2: Next** - Pending
- [ ] **Phase 3: Later** - Also pending
"""
        roadmap.write_text(content)

        result = parser.infer_active_phase_from_roadmap()

        assert result is not None
        assert result["name"] == "Phase 2: Next"
        assert result["status"] == "pending"

    def test_infer_active_in_progress(self, parser):
        """Test inferring active phase returns in-progress phase."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """- [x] **Phase 1: Done** - Completed
- [/] **Phase 2: Current** - In progress
- [ ] **Phase 3: Later** - Pending
"""
        roadmap.write_text(content)

        result = parser.infer_active_phase_from_roadmap()

        assert result is not None
        assert result["name"] == "Phase 2: Current"
        assert result["status"] == "in_progress"

    def test_infer_active_all_complete(self, parser):
        """Test inferring active phase returns None when all complete."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        content = """- [x] **Phase 1: Done** - Completed
- [x] **Phase 2: Also Done** - Completed
"""
        roadmap.write_text(content)

        result = parser.infer_active_phase_from_roadmap()

        assert result is None

    def test_infer_active_empty_roadmap(self, parser):
        """Test inferring active phase with empty roadmap."""
        roadmap = parser.project_path / ".planning" / "ROADMAP.md"
        roadmap.write_text("")

        result = parser.infer_active_phase_from_roadmap()

        assert result is None


class TestParseStatePhaseFormats:
    """Tests for STATE.md phase format parsing."""

    def test_parse_state_active_format(self, parser):
        """Test parsing active phase format: 'Phase: 5 of 7 (Template Versioning)'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Phase: 5 of 7 (Template Versioning)\n")

        result = parser.parse_state()

        assert result["current_phase"] == "5 of 7 (Template Versioning)"
        assert result["phase_number"] == 5
        assert result["total_phases"] == 7
        assert result["phase_name"] == "Template Versioning"

    def test_parse_state_completed_milestone_format(self, parser):
        """Test parsing completed milestone format: 'Phase: v1.0 complete — 7 of 7 phases shipped'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Phase: v1.0 complete — 7 of 7 phases shipped\n")

        result = parser.parse_state()

        assert result["current_phase"] == "v1.0 complete"
        assert result["milestone_complete"] is True
        assert result["milestone_version"] == "v1.0"
        assert result["phases_shipped"] == 7
        assert result["total_phases"] == 7

    def test_parse_state_not_started_format(self, parser):
        """Test parsing not started format: 'Phase: Not started'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Phase: Not started\n")

        result = parser.parse_state()

        assert result["current_phase"] == "Not started"
        assert result["phase_status"] == "not_started"

    def test_parse_state_simple_format(self, parser):
        """Test parsing simple format: 'Phase: 1 of 2 (Robust Parsing)'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Phase: 1 of 2 (Robust Parsing)\n")

        result = parser.parse_state()

        assert result["current_phase"] == "1 of 2 (Robust Parsing)"
        assert result["phase_number"] == 1
        assert result["total_phases"] == 2
        assert result["phase_name"] == "Robust Parsing"

    def test_parse_state_bold_markdown_phase(self, parser):
        """Test parsing bold markdown format: '**Phase:** 1 - Foundation & Type Safety'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("**Phase:** 1 - Foundation & Type Safety\n")

        result = parser.parse_state()

        assert result["phase_number"] == 1
        assert result["phase_name"] == "Foundation & Type Safety"
        assert "1" in result["current_phase"]

    def test_parse_state_dash_phase_format(self, parser):
        """Test parsing dash format: 'Phase: 3 - MCP Server Integration'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Phase: 3 - MCP Server Integration\n")

        result = parser.parse_state()

        assert result["phase_number"] == 3
        assert result["phase_name"] == "MCP Server Integration"

    def test_parse_state_missing_phase_line(self, parser):
        """Test parsing content without Phase line."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Status: In progress\nLast activity: 2026-02-08\n")

        result = parser.parse_state()

        assert "current_phase" not in result or result.get("current_phase") == ""


class TestParseStateProgressFormats:
    """Tests for STATE.md progress format parsing."""

    def test_parse_state_progress_bar_60(self, parser):
        """Test parsing progress bar format: 'Progress: [██████░░░░] 60%'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Progress: [██████░░░░] 60%\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 60

    def test_parse_state_progress_bar_100(self, parser):
        """Test parsing full progress bar: 'Progress: [██████████] 100%'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Progress: [██████████] 100%\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 100

    def test_parse_state_progress_bar_0(self, parser):
        """Test parsing empty progress bar: 'Progress: [░░░░░░░░░░] 0%'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Progress: [░░░░░░░░░░] 0%\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 0

    def test_parse_state_progress_count_100(self, parser):
        """Test parsing count format: '100% (16/16 plans completed)'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("100% (16/16 plans completed)\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 100

    def test_parse_state_progress_count_75(self, parser):
        """Test parsing count format partial: '75% (12/16 plans completed)'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("75% (12/16 plans completed)\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 75

    def test_parse_state_progress_requirements_format(self, parser):
        """Test parsing progress with 'requirements' instead of 'plans': '38% (10/26 requirements)'."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("[████████░░░░░░░░░░░░] 38% (10/26 requirements)\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 38

    def test_parse_state_progress_bar_no_prefix(self, parser):
        """Test parsing progress bar without 'Progress:' prefix."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("[██████░░░░] 60%\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 60

    def test_parse_state_no_progress_line(self, parser):
        """Test parsing content without progress line."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Phase: 1 of 2 (Test)\nStatus: In progress\n")

        result = parser.parse_state()

        assert result["progress_percent"] == 0


class TestParseStateFullDocument:
    """Tests for full STATE.md document parsing."""

    def test_parse_state_active_document(self, parser):
        """Test parsing complete active state document."""
        state_file = parser.planning_path / "STATE.md"
        content = """# Project State

## Current Position

Phase: 1 of 2 (Robust Parsing)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-08 — Roadmap created
Progress: [░░░░░░░░░░] 0%
Average duration: N/A
"""
        state_file.write_text(content)

        result = parser.parse_state()

        assert result["current_phase"] == "1 of 2 (Robust Parsing)"
        assert result["phase_number"] == 1
        assert result["total_phases"] == 2
        assert result["phase_name"] == "Robust Parsing"
        assert result["progress_percent"] == 0
        assert "2026-02-08" in result["last_activity"]
        assert result["phase_status"] == "Ready to plan"
        assert result["avg_duration"] == "N/A"

    def test_parse_state_completed_milestone_document(self, parser):
        """Test parsing complete milestone document."""
        state_file = parser.planning_path / "STATE.md"
        content = """# Project State

Phase: v1.0 complete — 7 of 7 phases shipped
Status: Shipped
Last activity: 2026-02-01 — All phases complete
Progress: [██████████] 100%
"""
        state_file.write_text(content)

        result = parser.parse_state()

        assert result["milestone_complete"] is True
        assert result["milestone_version"] == "v1.0"
        assert result["phases_shipped"] == 7
        assert result["total_phases"] == 7
        assert result["progress_percent"] == 100
        assert result["phase_status"] == "Shipped"

    def test_parse_state_not_started_document(self, parser):
        """Test parsing not started document."""
        state_file = parser.planning_path / "STATE.md"
        content = """# Project State

Phase: Not started
Status: Not started
Last activity: N/A
Progress: [░░░░░░░░░░] 0%
"""
        state_file.write_text(content)

        result = parser.parse_state()

        assert result["current_phase"] == "Not started"
        assert result["phase_status"] == "not_started"
        assert result["progress_percent"] == 0
        assert result["last_activity"] == "N/A"


class TestParseStateEdgeCases:
    """Tests for STATE.md edge cases and error handling."""

    def test_parse_state_missing_file(self, parser):
        """Test parsing when STATE.md doesn't exist."""
        # Don't create the file
        result = parser.parse_state()

        assert result == {}

    def test_parse_state_empty_file(self, parser):
        """Test parsing empty STATE.md file."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("")

        result = parser.parse_state()

        assert result["progress_percent"] == 0

    def test_parse_state_only_status(self, parser):
        """Test parsing STATE.md with only Status line."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Status: In progress\n")

        result = parser.parse_state()

        assert result["phase_status"] == "In progress"
        assert "current_phase" not in result or result.get("current_phase") == ""


class TestParseCompletedTodos:
    """Tests for completed todo parsing from todos/done/ directory."""

    def test_parse_completed_todos_basic(self, parser):
        """Test parsing basic completed todos."""
        todos_dir = parser.planning_path / "todos" / "done"
        todos_dir.mkdir(parents=True)

        (todos_dir / "fix-login-bug.md").write_text("")
        (todos_dir / "add-settings-page.md").write_text("")

        result = parser.parse_completed_todos()

        assert len(result) == 2
        for todo in result:
            assert "text" in todo
            assert "checked" in todo
            assert todo["checked"] is True
            assert isinstance(todo["text"], str)

    def test_parse_completed_todos_with_date_prefix(self, parser):
        """Test that date prefixes are stripped and text is prettified."""
        todos_dir = parser.planning_path / "todos" / "done"
        todos_dir.mkdir(parents=True)

        (todos_dir / "2026-02-07-settings-detail-page-refactor.md").write_text("")

        result = parser.parse_completed_todos()

        assert len(result) == 1
        assert result[0]["text"] == "Settings detail page refactor"
        assert result[0]["checked"] is True

    def test_parse_completed_todos_empty_directory(self, parser):
        """Test parsing when todos/done/ directory exists but is empty."""
        todos_dir = parser.planning_path / "todos" / "done"
        todos_dir.mkdir(parents=True)

        result = parser.parse_completed_todos()

        assert result == []

    def test_parse_completed_todos_missing_directory(self, parser):
        """Test parsing when todos/done/ directory doesn't exist."""
        result = parser.parse_completed_todos()

        assert result == []

    def test_parse_completed_todos_sorted(self, parser):
        """Test that completed todos are sorted alphabetically by text."""
        todos_dir = parser.planning_path / "todos" / "done"
        todos_dir.mkdir(parents=True)

        (todos_dir / "c-task.md").write_text("")
        (todos_dir / "a-task.md").write_text("")
        (todos_dir / "b-task.md").write_text("")

        result = parser.parse_completed_todos()

        assert len(result) == 3
        assert result[0]["text"] == "A task"
        assert result[1]["text"] == "B task"
        assert result[2]["text"] == "C task"


class TestGetAllDataIntegration:
    """Tests for get_all_data integration with enriched state dict."""

    def test_get_all_data_returns_enriched_state(self, parser):
        """Verify dashboard.py can consume enriched state dict via get_all_data()."""
        state_file = parser.planning_path / "STATE.md"
        state_file.write_text("Phase: 5 of 7 (Template Versioning)\nProgress: [██████░░░░] 60%\n")
        roadmap_file = parser.planning_path / "ROADMAP.md"
        roadmap_file.write_text("- [/] **Phase 5: Template Versioning** - Current work\n")

        data = parser.get_all_data()
        state = data["state"]

        assert state["phase_number"] == 5
        assert state["total_phases"] == 7
        assert state["progress_percent"] == 60
        assert "current_phase" in state

    def test_get_all_data_includes_completed_todos_and_inferred_phase(self, parser):
        """Verify get_all_data() includes completed_todos and inferred_active_phase keys."""
        # Create completed todo
        todos_dir = parser.planning_path / "todos" / "done"
        todos_dir.mkdir(parents=True)
        (todos_dir / "completed-task.md").write_text("")

        # Create roadmap with pending phase
        roadmap_file = parser.planning_path / "ROADMAP.md"
        roadmap_file.write_text("- [ ] **Phase 1: Setup** - Initial phase\n")

        data = parser.get_all_data()

        assert "completed_todos" in data
        assert len(data["completed_todos"]) == 1
        assert data["completed_todos"][0]["text"] == "Completed task"

        assert "inferred_active_phase" in data
        assert data["inferred_active_phase"] is not None
        assert data["inferred_active_phase"]["name"] == "Phase 1: Setup"
