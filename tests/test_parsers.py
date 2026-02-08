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
