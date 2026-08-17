# Isolated Demo Environment

The outer `demo` folder now owns its own Python virtual environment:

```text
project_root/
├── streamlit_app.py
└── demo/
    ├── .venv/          # created by setup_demo.ps1
    ├── streamlit_demo.py
    ├── setup_demo.ps1
    ├── validate_demo.ps1
    ├── run_demo.ps1
    └── demo/
        ├── data.py
        └── runtime.py
```

This avoids depending on whichever global Python happens to launch Streamlit.

## First run

From the project root:

```powershell
.\demo\setup_demo.ps1
.\demo\validate_demo.ps1
.\demo\run_demo.ps1
```

`run_demo.ps1` will automatically call `setup_demo.ps1` if `demo\.venv`
does not yet exist.

The environment installs the project's pinned runtime requirements because the
normal application modules are reused by the demo and import packages such as
Plotly and SQLAlchemy at module-import time, even though the demo backend itself
does not connect to MySQL.

To remove the demo completely, delete the outer `demo` directory. The isolated
virtual environment is removed with it.
