"""Keep the reference in step with the registry and run its local examples."""
import re
import shlex
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from priemka.checks import CHECKS, DETERMINISTIC
from priemka.policy import load_pack

class GateReferenceTest(unittest.TestCase):
    def test_reference_covers_registered_and_example_gates(self):
        text = (ROOT / "docs/gates.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| `([^`]+)` \| ([^|]+) \| [^|]+ \| `([^`]+)` \|$", text, re.M)
        self.assertEqual(set(CHECKS) | DETERMINISTIC, {row[0] for row in rows})
        self.assertEqual(len(CHECKS) + len(DETERMINISTIC), len(rows))
        for gate in load_pack(ROOT / "examples/pack-rag.toml").gates:
            self.assertTrue(any(kind == gate.kind and gate.id in ids.strip().split(", ") for kind, ids, _ in rows))
        for kind, _, command in rows:
            with self.subTest(kind=kind):
                args = shlex.split(command)
                self.assertEqual("python", args[0])
                ran = subprocess.run([sys.executable, *args[1:]], cwd=ROOT, text=True, capture_output=True, timeout=10)
                self.assertEqual(0, ran.returncode, ran.stderr)
                self.assertEqual("False", ran.stdout.strip())
