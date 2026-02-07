# GSD TUI Dashboard

A terminal-based dashboard (TUI) for monitoring project progress using Markdown-based planning files.

This tool is designed to work with the "GSD" (Get Shit Done) planning methodology, parsing `PROJECT.md`, `ROADMAP.md`, `STATE.md`, and phase documentation to provide a real-time overview of your project's status.

## Features

-   **Dashboard View**:
    -   **Roadmap**: Visual list of project phases with status indicators. Current phase is highlighted and pulses.
    -   **Project Stats**: Progress bars, velocity metrics, and last activity timestamps.
    -   **Pending Todos**: List of pending tasks dynamically loaded from `.planning/todos/pending/`.
-   **Documentation Tabs**:
    -   **Summary**: Auto-loads the latest `*-SUMMARY.md` for a quick phase overview.
    -   View Context, Research, Plans, and Verification documents for the *current phase* directly in the dashboard.
-   **Live Updates**:
    -   Automatically refreshes when planning files are modified.
    -   Toggle auto-refresh with `t`.
-   **Navigation**:
    -   Keyboard-centric navigation (Vim-style `j`/`k`, arrow keys, PageUp/Down).
    -   Switch tabs with Left/Right arrow keys.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/patrickLorenz83/gsd-tui-dashboard.git
    cd gsd-tui-dashboard
    ```

2.  Create a virtual environment (recommended):
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the dashboard by pointing it to your project's root directory (the directory containing the `.planning` folder).

```bash
python dashboard.py --path /path/to/your/project
```

Or use the helper script:

```bash
./run_dashboard.sh /path/to/your/project
```

### Key Bindings

| Key | Action |
| :--- | :--- |
| `q` | Quit |
| `r` | Manually Refresh Data |
| `t` | Toggle Auto-Refresh |
| `←` / `→` | Switch Tabs |
| `j` / `↓` | Scroll Down |
| `k` / `↑` | Scroll Up |
| `Home` / `End` | Scroll to Top/Bottom |

## Project Structure

This tool expects a specific project structure for the target project:

```
project-root/
└── .planning/
    ├── PROJECT.md      # Active tasks
    ├── ROADMAP.md      # Phase list
    ├── STATE.md        # Current progress & stats
    └── phases/         # Phase-specific documentation
        ├── 01-phase-name/
        │   ├── 01-CONTEXT.md
        │   ├── 01-RESEARCH.md
        │   └── ...
        └── ...
```

## License

MIT
