"""A gate cannot pass because its required input was silently defaulted."""
import tempfile
import unittest
from pathlib import Path

from priemka.policy import PolicyError, load_pack, starter_pack


class GateParameterTests(unittest.TestCase):
    def load(self, kind, extra=""):
        text = '[system]\nname="test"\ntarget="fixture"\n[[gates]]\nid="required-input"\nkind="' + kind + '"\n' + extra
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pack.toml"
            path.write_text(text, encoding="utf-8")
            return load_pack(path)

    def test_required_parameters_are_named_with_the_gate(self):
        for kind, parameter in (
            ("contains", "value"), ("not_contains", "value"),
            ("matches", "pattern"), ("citation", "marker"),
            ("latency", "max_ms"), ("cost", "max_cost"), ("grounded", "context"),
        ):
            with self.subTest(kind=kind):
                with self.assertRaises(PolicyError) as caught:
                    self.load(kind)
                for name in ("required-input", kind, parameter):
                    self.assertIn(name, str(caught.exception))

    def test_misspelled_parameter_is_not_a_silent_default(self):
        with self.assertRaisesRegex(PolicyError, "value"):
            self.load("contains", 'valuee="needle"\n')

    def test_empty_contains_and_matches_are_refused(self):
        for kind, parameter in (("contains", "value"), ("matches", "pattern")):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(PolicyError, parameter):
                    self.load(kind, parameter + '=""\n')

    def test_explicit_parameters_and_zero_limits_stay_valid(self):
        for kind, extra in (
            ("contains", 'value="needle"'), ("not_contains", 'value="needle"'),
            ("matches", 'pattern="needle"'), ("citation", 'marker="source:"'),
            ("latency", "max_ms=0"), ("cost", "max_cost=0"),
            ("grounded", 'context="reference"'),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(self.load(kind, extra).gates[0].kind, kind)

    def test_shipped_and_starter_packs_load(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue(load_pack(root / "examples/pack-rag.toml").gates)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "starter.toml"
            path.write_text(starter_pack("test", "fixture"), encoding="utf-8")
            self.assertTrue(load_pack(path).gates)
