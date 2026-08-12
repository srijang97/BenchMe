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
