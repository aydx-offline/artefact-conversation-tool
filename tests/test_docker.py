import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DockerTest(unittest.TestCase):
    def test_image_contains_runtime_files_and_web_command(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("python:3.12-slim", dockerfile)
        for path in ("ca", "web", "data", "cases", "requirements.txt"):
            self.assertIn(path, dockerfile)
        self.assertIn('CMD ["python", "-m", "ca.web"]', dockerfile)

    def test_readme_contains_exact_build_and_run_commands(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docker build -t ca-messages .", readme)
        self.assertIn(
            'docker run --env-file .env -p 8765:8765 -v "$PWD/runs:/app/runs" '
            '-v "$PWD/data:/app/data" ca-messages',
            readme,
        )

    def test_environment_and_local_output_are_excluded(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        copy_lines = [
            line for line in dockerfile.splitlines() if line.strip().upper().startswith("COPY ")
        ]
        self.assertFalse(any(".env" in line for line in copy_lines))
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        for path in (
            ".env",
            "runs",
            ".git",
            ".worktrees",
            ".superpowers",
            "log",
            "Written_Challenge_Brief.pdf",
            "__pycache__",
        ):
            self.assertIn(path, dockerignore)


if __name__ == "__main__":
    unittest.main()
