import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "screener"))

import candidates  # noqa: E402

PYDANTIC = "[project]\nname = 'pydantic'\ndependencies = [\n 'pydantic-core==2.37.2',\n]\n"
PYDANTIC_BUMPED = PYDANTIC.replace("2.37.2", "2.38.0")
CORE = "[project]\nname = 'pydantic_core'\n"


def test_project_name_reads_single_and_double_quotes():
    assert candidates.project_name(PYDANTIC) == "pydantic"
    assert candidates.project_name('[project]\nname = "pydantic"\n') == "pydantic"
    assert candidates.project_name(CORE) == "pydantic_core"


def test_project_name_is_none_when_absent():
    """pydantic v1 predates pyproject.toml. Absence is NOT foreignness."""
    assert candidates.project_name("") is None


def test_a_foreign_project_is_not_minable():
    """105 of 1,568 candidates are pydantic-core commits grafted into the
    pydantic clone. They can never run in a pydantic image."""
    assert candidates.not_minable_reason("pydantic", CORE, CORE) == "foreign_project"


def test_a_missing_pyproject_is_not_foreign():
    assert candidates.not_minable_reason("pydantic", "", "") is None


def test_exact_pins_ignores_ranges():
    text = "dependencies = [\n 'a==1.0',\n 'b>=2.0',\n 'c',\n]\n"
    assert candidates.exact_pins(text) == {"a": "1.0"}


def test_a_changed_exact_pin_straddles_a_dependency_bump():
    """Before needs 2.37.2 and after needs 2.38.0. No single quarter image can
    serve both, and the container runs --network none by design."""
    assert candidates.not_minable_reason(
        "pydantic", PYDANTIC, PYDANTIC_BUMPED) == "straddles_dependency_bump"


def test_an_unchanged_pin_is_minable():
    assert candidates.not_minable_reason("pydantic", PYDANTIC, PYDANTIC) is None


def test_a_changed_range_dependency_is_not_a_boundary():
    a = "dependencies = [\n 'b>=2.0',\n]\n"
    b = "dependencies = [\n 'b>=3.0',\n]\n"
    assert candidates.not_minable_reason("pydantic", a, b) is None


def test_an_unknown_repo_filters_nothing():
    assert candidates.not_minable_reason("somethingelse", CORE, CORE) is None


def test_no_pytest_tests_is_not_minable():
    """pydantic/tests/typechecking/ and tests/mypy/ satisfy metrics.is_test_file
    but pytest collects nothing from them (mypy/pyright fixtures). A candidate
    whose test files are exclusively in those trees has no fail-to-pass to
    offer, so it must be stamped no_pytest_tests and never spend a container
    slot discovering the same thing the filter already knows."""
    test_files = ["tests/typechecking/fields.py", "tests/typechecking/optional.py"]
    assert candidates.not_minable_reason(
        "pydantic", PYDANTIC, PYDANTIC, test_files=test_files) == "no_pytest_tests"


def test_no_pytest_tests_requires_every_test_file_to_be_non_pytest():
    """A single real pytest test among the touched files keeps the candidate
    minable: the filter must never drop a candidate that has a fail-to-pass to
    offer, even when most of its tests are static-checker fixtures."""
    test_files = ["tests/typechecking/fields.py", "tests/test_main.py"]
    assert candidates.not_minable_reason(
        "pydantic", PYDANTIC, PYDANTIC, test_files=test_files) is None


def test_no_pytest_tests_is_skipped_when_test_files_are_not_provided():
    """test_files defaults to None for compatibility with the pyproject-only
    callers; the existing reasons still apply."""
    assert candidates.not_minable_reason("pydantic", CORE, CORE) == "foreign_project"
