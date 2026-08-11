import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate  # noqa: E402


def test_split_paths_separates_tests_from_code():
    files = [
        "pydantic/main.py",
        "tests/test_main.py",
        "pydantic/_internal/_fields.py",
        "tests/benchmarks/test_north_star.py",
        "docs/index.md",
        "tests/fixtures/expected.json",
        "conftest.py",
    ]
    tests, code = validate.split_paths(files)
    assert tests == [
        "conftest.py",
        "tests/benchmarks/test_north_star.py",
        "tests/fixtures/expected.json",
        "tests/test_main.py",
    ]
    assert code == ["docs/index.md", "pydantic/_internal/_fields.py",
                    "pydantic/main.py"]
    assert not set(tests) & set(code)
    assert sorted(tests + code) == sorted(files)
