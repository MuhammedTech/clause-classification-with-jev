"""ADR-0003: nothing is fitted, so nothing needs holding out.

The ticket asks that no Cutoff tuning, fold assignment or overlap threshold exists anywhere in the
code. Prose may say "no threshold"; this checks identifiers only (names, attributes, parameters,
functions and classes), which is where such a thing would actually live.
"""

import ast
from pathlib import Path

import jev_cascade

# `seed` is not forbidden: the stub Jev client hashes its inputs with one so its answers are
# reproducible. That is the stub's identity, not a fold assignment or a tuned Cutoff.
FORBIDDEN = ("fold", "tune", "tuning", "tuned", "threshold", "random", "shuffle")

#: Modules allowed to use a seeded random generator, and why. ADR-0003 is about **grading**: nothing
#: is fitted, so nothing is held out. Ticket 08's study draws a sample and bootstraps an interval
#: before the real run, which needs a seeded draw. It is a pre-run tool, not part of how a run is
#: graded, so `GRADING_MODULES` below must never import it.
SEEDED_SAMPLING_MODULES = {"sample_study.py"}

#: Everything that grades or reports a run. None may depend on the sampling module.
GRADING_MODULES = ("evaluator.py", "pipeline.py", "report.py", "runner.py", "cost.py", "charts.py")


def _identifiers(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            yield node.id
        elif isinstance(node, ast.Attribute):
            yield node.attr
        elif isinstance(node, ast.arg):
            yield node.arg
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            yield node.name
        elif isinstance(node, ast.alias):
            yield node.name.split(".")[-1]
            if node.asname:
                yield node.asname


def test_no_module_names_a_fold_a_tuned_cutoff_a_threshold_or_randomness():
    source_dir = Path(jev_cascade.__file__).parent
    offenders = []
    for path in sorted(source_dir.glob("*.py")):
        if path.name in SEEDED_SAMPLING_MODULES:
            continue
        for identifier in _identifiers(ast.parse(path.read_text(encoding="utf-8"))):
            if any(word in identifier.lower() for word in FORBIDDEN):
                offenders.append(f"{path.name}: {identifier}")
    assert offenders == []


def test_nothing_that_grades_a_run_imports_the_seeded_sampling_module():
    source_dir = Path(jev_cascade.__file__).parent
    for name in GRADING_MODULES:
        text = (source_dir / name).read_text(encoding="utf-8")
        assert "sample_study" not in text, f"{name} must not depend on the sampling module"
