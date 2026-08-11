from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def requirement_names(path):
    names = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-r ")):
            continue
        names.add(re.split(r"[<>=!~\[]", line, maxsplit=1)[0].lower())
    return names


class DependencyContractTests(unittest.TestCase):
    def test_runtime_requirements_contain_only_direct_dependencies(self):
        self.assertEqual(
            {
                "mysql-connector-python",
                "numpy",
                "pandas",
                "plotly",
                "pymysql",
                "requests",
                "sqlalchemy",
                "streamlit",
            },
            requirement_names(PROJECT_ROOT / "requirements.txt"),
        )

    def test_development_requirements_extend_runtime_with_quality_tools(self):
        path = PROJECT_ROOT / "requirements-dev.txt"
        lines = {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("-r requirements.txt", lines)
        self.assertEqual({"coverage", "ruff"}, requirement_names(path))


if __name__ == "__main__":
    unittest.main()
