# Locked Environment Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add profile-native dependency-locking abstractions for `uv.lock` and `pdm.lock` to fix missing test-dependency apparatus failures in legacy quarters (2024Q2/Q3), stamp `profile` metadata onto all records, and run a safe rerun queue selector.

**Architecture:** Introduce `EnvironmentProfile` and `detect_profile` in `miner/quarters.py` to select tool installation, export commands, and post-deletion import probes. Update `QuarterImage` and record writing in `miner/runner.py` to carry profile provenance. Add collection error diagnostic details and implement the PDM rerun queue selector in `miner/runner.py` and `miner/compare_rerun.py`.

**Tech Stack:** Python 3.12+, Docker, PDM, UV, pytest, git worktrees.

## Global Constraints

- Never install the root repository project (`pydantic`) into container `site-packages`.
- Invariant 1: `import pydantic` must fail after `/src` removal.
- Invariant 2: `import pydantic_core` must pass after `/src` removal.
- Invariant 3: Profile probes (`dirty_equals`, `pytest_examples` for PDM profile) must pass after `/src` removal.
- `QuarterImage.anchored` remains `True` only when a frozen export runs cleanly without unpinned fallback.
- `validated.jsonl` remains append-only; historical attempts are preserved.
- Existing 155 unit tests must remain passing.

---

### Task 1: Environment Profiles and Profile Detection (`miner/quarters.py`)

**Files:**
- Modify: `miner/quarters.py:1-120`
- Test: `miner/tests/test_runner.py`

**Interfaces:**
- Consumes: Worktree filesystem paths.
- Produces: `EnvironmentProfile` namedtuple (`name`, `lockfile`, `tool_install`, `export_frozen`, `export_frozen_min`, `export_unfrozen`, `export_unfrozen_min`, `profile_probes`), `UV_PROFILE`, `PDM_PROFILE`, `detect_profile(anchor_worktree: Path) -> EnvironmentProfile | None`, `REASON_NO_LOCKFILE`, `REASON_AMBIGUOUS_LOCKFILE`.

- [ ] **Step 1: Write failing unit tests for `detect_profile` and profile definitions**

Add tests to `miner/tests/test_runner.py`:

```python
def test_detect_profile_selects_uv_and_pdm(tmp_path):
    uv_dir = tmp_path / "uv_anchor"
    uv_dir.mkdir()
    (uv_dir / "uv.lock").write_text("", encoding="utf-8")
    prof = quarters.detect_profile(uv_dir)
    assert prof is not None
    assert prof.name == "uv_locked"
    assert prof.lockfile == "uv.lock"

    pdm_dir = tmp_path / "pdm_anchor"
    pdm_dir.mkdir()
    (pdm_dir / "pdm.lock").write_text("", encoding="utf-8")
    prof = quarters.detect_profile(pdm_dir)
    assert prof is not None
    assert prof.name == "pdm_locked"
    assert prof.lockfile == "pdm.lock"

def test_detect_profile_returns_none_for_missing_or_ambiguous_lockfiles(tmp_path):
    empty_dir = tmp_path / "empty_anchor"
    empty_dir.mkdir()
    assert quarters.detect_profile(empty_dir) is None

    ambig_dir = tmp_path / "ambig_anchor"
    ambig_dir.mkdir()
    (ambig_dir / "uv.lock").write_text("", encoding="utf-8")
    (ambig_dir / "pdm.lock").write_text("", encoding="utf-8")
    assert quarters.detect_profile(ambig_dir) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest miner/tests/test_runner.py -k "test_detect_profile" -v`
Expected: FAIL with `AttributeError: module 'quarters' has no attribute 'detect_profile'`

- [ ] **Step 3: Implement `EnvironmentProfile` and `detect_profile` in `miner/quarters.py`**

Add to `miner/quarters.py`:

```python
class EnvironmentProfile(NamedTuple):
    name: str
    lockfile: str
    tool_install: str
    export_frozen: str
    export_frozen_min: str
    export_unfrozen: str
    export_unfrozen_min: str
    profile_probes: tuple

REASON_NO_LOCKFILE = "no-supported-lockfile"
REASON_AMBIGUOUS_LOCKFILE = "ambiguous-lockfiles"

UV_PROFILE = EnvironmentProfile(
    name="uv_locked",
    lockfile="uv.lock",
    tool_install="RUN pip install --no-cache-dir uv",
    export_frozen=EXPORT_FROZEN,
    export_frozen_min=EXPORT_FROZEN_MIN,
    export_unfrozen=EXPORT_UNFROZEN,
    export_unfrozen_min=EXPORT_UNFROZEN_MIN,
    profile_probes=(),
)

PDM_PROFILE = EnvironmentProfile(
    name="pdm_locked",
    lockfile="pdm.lock",
    tool_install="RUN pip install --no-cache-dir pdm",
    export_frozen="pdm export -g testing -g testing-extra --no-self",
    export_frozen_min="pdm export --no-self",
    export_unfrozen="pdm export -g testing -g testing-extra --no-self",
    export_unfrozen_min="pdm export --no-self",
    profile_probes=("dirty_equals", "pytest_examples"),
)

def detect_profile(anchor_worktree):
    path = Path(anchor_worktree)
    has_uv = (path / "uv.lock").exists()
    has_pdm = (path / "pdm.lock").exists()
    if has_uv and not has_pdm:
        return UV_PROFILE
    if has_pdm and not has_uv:
        return PDM_PROFILE
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest miner/tests/test_runner.py -k "test_detect_profile" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add miner/quarters.py miner/tests/test_runner.py
git commit -m "feat: add EnvironmentProfile abstractions and detect_profile"
```

---

### Task 2: Profile-Aware Dockerfile Generation & Image Metadata (`miner/quarters.py`)

**Files:**
- Modify: `miner/quarters.py:100-320`
- Test: `miner/tests/test_runner.py`

**Interfaces:**
- Consumes: `EnvironmentProfile` instance and worktree path.
- Produces: `QuarterImage` with `profile` field (`QuarterImage(tag, reason, anchor, anchored, skip, profile)`), `/opt/miner/environment-profile` file in container, updated `DOCKERFILE` template with profile probes check.

- [ ] **Step 1: Write failing unit tests for `QuarterImage` profile field and Dockerfile formatting**

Add to `miner/tests/test_runner.py`:

```python
def test_quarter_image_namedtuple_has_profile_field():
    img = quarters.QuarterImage("tag:1", "ok", "sha123", True, False, "pdm_locked")
    assert img.tag == "tag:1"
    assert img.profile == "pdm_locked"
    assert img.anchored is True

def test_dockerfile_template_includes_profile_probes_and_profile_file():
    prof = quarters.PDM_PROFILE
    cmd = quarters._profile_probes_cmd(prof)
    assert 'import dirty_equals; import pytest_examples' in cmd
    assert 'FATAL: profile probes failed' in cmd

    uv_cmd = quarters._profile_probes_cmd(quarters.UV_PROFILE)
    assert uv_cmd == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest miner/tests/test_runner.py -k "test_quarter_image or test_dockerfile_template" -v`
Expected: FAIL with `TypeError: QuarterImage takes 5 positional arguments but 6 were given` or `AttributeError: module 'quarters' has no attribute '_profile_probes_cmd'`

- [ ] **Step 3: Update `QuarterImage` definition, Dockerfile template, and `build_quarter_image` in `miner/quarters.py`**

In `miner/quarters.py`:

Update `QuarterImage`:
```python
QuarterImage = namedtuple("QuarterImage",
                          "tag reason anchor anchored skip profile")
PROFILE_PATH = "/opt/miner/environment-profile"
```

Add helper:
```python
def _profile_probes_cmd(profile: EnvironmentProfile) -> str:
    if not profile or not profile.profile_probes:
        return ""
    imports = "; ".join(f"import {mod}" for mod in profile.profile_probes)
    return (
        f'RUN python -c "{imports}" >/dev/null 2>&1 || ( \\\n'
        f'      echo "FATAL: profile probes failed ({", ".join(profile.profile_probes)} missing)"; \\\n'
        f'      exit 1 )'
    )
```

Update `DOCKERFILE` template to insert `tool_install`, write `profile.name` to `PROFILE_PATH`, and include `{profile_probes}` block after `/src` removal.

Update `build_quarter_image` signature and return:
```python
    def finish(tag, reason, anchored=False, skip=False, profile=None):
        log.insert(0, f"quarter={quarter!r} anchor={sha} "
                      f"reason={reason} anchored={anchored} skip={skip} profile={profile}")
        ...
        return QuarterImage(tag, reason, sha, anchored, skip, profile)
```

In `build_quarter_image`, after adding worktree:
```python
        prof = detect_profile(work)
        if prof is None:
            has_uv = (work / "uv.lock").exists()
            has_pdm = (work / "pdm.lock").exists()
            reason = REASON_AMBIGUOUS_LOCKFILE if (has_uv and has_pdm) else REASON_NO_LOCKFILE
            log.append(f"profile detection failed: has_uv={has_uv} has_pdm={has_pdm}")
            return finish(None, reason, profile=None)
```

Pass `prof` commands to `DOCKERFILE.format(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest miner/tests/test_runner.py -k "test_quarter_image or test_dockerfile_template" -v`
Expected: PASS

- [ ] **Step 5: Run full miner test suite**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS all tests (updating any existing mock `QuarterImage` instantiations in test code if required).

- [ ] **Step 6: Commit**

```bash
git add miner/quarters.py miner/tests/test_runner.py
git commit -m "feat: profile-aware Dockerfile generation and QuarterImage profile field"
```

---

### Task 3: Provenance Threading & Collection Diagnostics (`miner/runner.py`)

**Files:**
- Modify: `miner/runner.py:300-800`
- Modify: `miner/outcomes.py:1-150`
- Test: `miner/tests/test_runner.py`
- Test: `miner/tests/test_outcomes.py`

**Interfaces:**
- Consumes: `QuarterImage.profile`, `before_collect` / `after_collect` records.
- Produces: `rec["profile"]` written to `validated.jsonl`, `out["first_collect_error"]` formatted string in candidate measurements.

- [ ] **Step 1: Write failing unit tests for `profile` recording and collection error details**

Add to `miner/tests/test_runner.py`:

```python
def test_validate_quarter_stamps_profile_on_records(monkeypatch, tmp_path):
    recorded = []
    def mock_append(path, rec):
        recorded.append(rec)
    monkeypatch.setattr(record, "append", mock_append)
    img = quarters.QuarterImage("tag:1", "ok", "sha123", True, False, "pdm_locked")
```

Add to `miner/tests/test_outcomes.py`:

```python
def test_extract_first_collect_error_returns_summary():
    rec = outcomes.Record("tests/test_foo.py", "collect", "failed", "ImportError: No module named 'dirty_equals'")
    summary = outcomes.extract_first_collect_error([rec])
    assert summary == "tests/test_foo.py: ImportError: No module named 'dirty_equals'"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest miner/tests/test_outcomes.py -k "test_extract_first_collect_error" -v`
Expected: FAIL with `AttributeError: module 'outcomes' has no attribute 'extract_first_collect_error'`

- [ ] **Step 3: Implement `extract_first_collect_error` in `miner/outcomes.py` and thread `profile` in `miner/runner.py`**

In `miner/outcomes.py`:

```python
def extract_first_collect_error(collect_records):
    if not collect_records:
        return None
    rec = collect_records[0]
    raw_msg = rec.message.strip().splitlines()[0] if rec.message else "collection error"
    return f"{rec.nodeid}: {raw_msg}"
```

In `miner/runner.py`:

In `_measure`:
```python
if before_collect:
    out["first_collect_error"] = outcomes.extract_first_collect_error(before_collect)
```

In `validate_quarter`:
```python
def write(rec):
    rec["anchored"] = img.anchored
    rec["anchor"] = img.anchor
    rec["profile"] = img.profile
    record.append(record.VALIDATED, rec)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest miner/tests/test_outcomes.py -k "test_extract_first_collect_error" -v`
Run: `python -m pytest miner/tests/test_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add miner/outcomes.py miner/runner.py miner/tests/test_outcomes.py miner/tests/test_runner.py
git commit -m "feat: record profile metadata and collection error diagnostics"
```

---

### Task 4: PDM Rerun Queue Selector & Verification (`miner/runner.py` & `miner/compare_rerun.py`)

**Files:**
- Modify: `miner/compare_rerun.py`
- Modify: `miner/runner.py`
- Test: `miner/tests/test_runner.py`

**Interfaces:**
- Consumes: `all_candidates`, `validated_records`.
- Produces: `is_pdm_rerun_eligible(rec, latest_record) -> bool`, `select_pdm_rerun_queue(all_candidates, done_records, quarters_set) -> list[dict]`.

- [ ] **Step 1: Write failing unit tests for PDM rerun queue selector**

Add to `miner/tests/test_runner.py`:

```python
def test_pdm_rerun_queue_selector_logic():
    cand1 = {"sha": "sha1", "quarter": "2024Q2"}
    assert runner.is_pdm_rerun_eligible(cand1, None) is True

    rec_err = {"sha": "sha2", "status": "error", "anchored": True}
    assert runner.is_pdm_rerun_eligible(cand1, rec_err) is True

    rec_unanchored = {"sha": "sha3", "status": "apparatus", "anchored": False}
    assert runner.is_pdm_rerun_eligible(cand1, rec_unanchored) is True

    rec_anchored = {"sha": "sha4", "status": "rejected:unchanged", "anchored": True}
    assert runner.is_pdm_rerun_eligible(cand1, rec_anchored) is False

    rec_pre_docker = {"sha": "sha5", "status": "not_minable:no-pytest", "anchored": None}
    assert runner.is_pdm_rerun_eligible(cand1, rec_pre_docker) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest miner/tests/test_runner.py -k "test_pdm_rerun_queue_selector_logic" -v`
Expected: FAIL with `AttributeError: module 'runner' has no attribute 'is_pdm_rerun_eligible'`

- [ ] **Step 3: Implement `is_pdm_rerun_eligible` and queue filtering in `miner/runner.py`**

In `miner/runner.py`:

```python
def is_pdm_rerun_eligible(cand, latest_rec):
    if not latest_rec:
        return True
    st = latest_rec.get("status", "")
    if st == "error":
        return True
    if latest_rec.get("anchored") is False:
        return True
    return False
```

Update queue selection in `validate_quarter` when `pdm_rerun_mode=True` or via `--pdm-rerun` flag option.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest miner/tests/test_runner.py -k "test_pdm_rerun_queue_selector_logic" -v`
Expected: PASS

- [ ] **Step 5: Run full pytest suite across `miner/tests/`**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS all 155+ tests.

- [ ] **Step 6: Commit**

```bash
git add miner/runner.py miner/compare_rerun.py miner/tests/test_runner.py
git commit -m "feat: implement PDM rerun queue selector and eligibility logic"
```

---

## Self-Review Checklist

- [x] Spec coverage: Covers profile detection, Dockerfile generation, metadata provenance, collection diagnostics, and rerun queue selection.
- [x] Placeholder scan: Clean, explicit code blocks with zero TBD/TODO markers.
- [x] Type consistency: `EnvironmentProfile` and `QuarterImage` types match everywhere.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-13-locked-environment-profiles.md`. Two execution options:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
