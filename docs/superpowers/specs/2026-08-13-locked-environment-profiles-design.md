# Locked Environment Profiles for the Legacy Sweep

**Date:** 2026-08-13  
**Status:** approved design direction; implementation plan pending review  
**Branch:** `feat/miner-adjudication`  
**First corpus:** Pydantic v2, 2023Q3-2026Q3

## 1. Decision

BenchMe will build quarter images through a small, lockfile-native
**environment-profile** interface. The first two supported profiles are:

| Lockfile present at quarter anchor | Profile | Status |
|---|---|---|
| `uv.lock` | `uv_locked` | existing modern path, retained and made explicit |
| `pdm.lock` | `pdm_locked` | new legacy path |
| neither, or more than one supported lockfile | no selected profile | fail closed; no fresh dependency resolution |

This replaces the current unsafe fallback from failed frozen `uv export` to a
fresh unpinned UV resolution. A fresh resolution can produce a runnable but
historically false environment, so it must never be called `anchored`.

The abstraction is deliberately narrow. It is not a generic package-manager
framework and does not add Poetry, Pipenv, Conda, or requirements-file support
in this change. A future repository can add a profile only by defining the same
locked-closure contract below.

## 2. Problem and evidence

Pydantic 2024Q2 and 2024Q3 use `pdm.lock` and legacy
`[tool.pdm.dev-dependencies]`. The current builder only understands `uv.lock`.
Its frozen UV export therefore fails; its UV group selection cannot see PDM's
groups; and its final minimal, unpinned fallback succeeds with only production
dependencies. Those images are stamped `anchored=false`.

The fallback omitted locked test dependencies such as `dirty-equals`,
`pytest-examples`, `pytest-mock`, `pytest-pretty`, `faker`, `devtools`,
`sqlalchemy`, and `greenlet`. Consequently, candidate test modules failed to
collect or produced no parseable test outcomes. These are apparatus failures,
not verdicts about commits.

This is distinct from candidate-level pydantic-core alignment. The current
wheel-cache path successfully downloaded compatible CPython 3.12 wheels for
every Q2/Q3 pin (`2.17.0` through `2.24.0`) and remains unchanged. It aligns a
candidate's exact core version only after a valid shared test closure exists;
it cannot provide missing pytest plugins or test-only packages.

Pydantic switches from PDM to UV at commit `53bf2f28` (2024-11-08). 2024Q4
and later have `uv.lock`, build with a frozen closure, and are `anchored=true`.

## 3. Invariants

Every successful profile image must prove all of the following before the
runtime container starts:

1. **Native-lock authority.** The profile consumed the lockfile committed at
   the quarter anchor. It did not resolve a new graph.
2. **Dependency-only image.** The root repository project is not installed in
   site-packages. Candidate checkouts, not the image, provide the project code.
3. **Selected test closure.** The profile installed the declared test scope
   from the native lock, not an inferred or minimal substitute.
4. **Runtime dependency closure.** Required runtime packages import after
   `/src` is removed. For Pydantic this includes `pydantic_core`.
5. **Profile test probes.** The selected profile's explicit probe modules
   import after `/src` is removed. For the Pydantic PDM profile these are
   `dirty_equals` and `pytest_examples`.
6. **No runtime network.** Candidate execution remains in the existing Docker
   container with `--network none`.
7. **Candidate alignment stays separate.** A candidate's `core_pin` is still
   aligned from `/opt/miner/wheels` immediately before tests run; no profile
   may replace this with a live network install.

A failure of any invariant fails the image build. It must not produce an
unanchored benchmark image as a fallback.

## 4. Profile contract

`miner/quarters.py` will expose a small immutable profile representation. Its
exact Python shape may be a `NamedTuple` or dataclass, but it must supply:

```python
EnvironmentProfile(
    name: str,                 # "uv_locked" or "pdm_locked"
    lockfile: str,             # "uv.lock" or "pdm.lock"
    tool_install: str,         # Dockerfile command to install pinned manager
    export_command: str,       # writes locked requirements to stdout
    profile_probes: tuple[str, ...],
)
```

`detect_profile(anchor_worktree) -> EnvironmentProfile | None` is based solely
on files at the anchor worktree:

* exactly `uv.lock` -> `UV_PROFILE`;
* exactly `pdm.lock` -> `PDM_PROFILE`;
* neither or both -> `None`, with an explicit build reason.

The image writes the selected profile name to
`/opt/miner/environment-profile`; `QuarterImage` gains a `profile` field so
every later record can preserve the environment provenance.

## 5. UV profile

The UV profile preserves the established path:

```text
uv export --frozen --no-hashes --no-emit-project --no-editable
  --all-extras --group testing-extra
```

The existing minimal frozen UV export may remain only if it is explicitly
needed by a valid UV-lock project and still passes all profile probes. It must
not fall through to an unfrozen export.

The Pydantic UV profile has no additional probes beyond the global
`pydantic`-absent and `pydantic_core`-present guards unless evidence identifies
a missing locked test dependency.

## 6. PDM profile

The PDM profile is a native reader of a committed `pdm.lock`.

### Pinned tool and interpreter

The implementation must select a **tested** PDM/toolchain pair for the committed
`lock_version = "4.3"` files, rather than assuming that a modern-looking PDM
release is compatible. The pilot first runs the native lock freshness/read
check and a dependency-only export against the actual Q2 and Q3 anchors. It
records the chosen PDM and Python versions in the image provenance only after
both anchors pass. If that pair cannot consume the lock without rewriting it
or resolving a new graph, the build fails and the compatibility investigation
continues; it does not fall back to UV or an unlocked PDM command.

The profile runs on a project-compatible base interpreter selected by the
profile implementation. An incompatible interpreter or unavailable locked
wheel must fail the build rather than silently source-resolve at runtime.

### Closure selection

For the first Pydantic PDM configuration, export the committed lock's default
dependencies plus PDM dev groups:

```text
testing
testing-extra
```

The exported/installable closure must not include the root project. The
implementation must prove this with the existing source-removal and
`import pydantic` absence guard; it must not rely on an assumed PDM flag
semantic. The output is installed with the existing dependency-only image
discipline.

Profile-specific group selection belongs in a declarative profile configuration,
not in a branch named after Pydantic. A different PDM repository may select a
different set of explicit test groups while reusing the exporter.

### Pydantic PDM probes

After source removal, the Pydantic PDM image must verify:

```text
import pydantic_core       # runtime closure
import dirty_equals        # historical testing group
import pytest_examples     # docs/test plugin dependency
```

The pre-existing absence guard for `import pydantic` remains mandatory.

## 7. Collection diagnostics

Retain concise pytest output, but collect a bounded first traceback when a
selected test module cannot collect. The structured reporter record must carry
the first collection exception type and normalized first message line. This is
diagnostic evidence only; it does not change adjudication ordering or turn an
apparatus failure into a verdict.

## 8. Data and rerun policy

`validated.jsonl` remains append-only. Rates and current status are computed by
last record per candidate SHA, matching `record.read_all` semantics. Historical
attempts are never deleted.

After the PDM image passes its pilot gate, resume the PDM-era range:

```text
2023Q3, 2023Q4, 2024Q1, 2024Q2, 2024Q3
```

The queue selector for this explicit repair rerun is:

* candidate has no latest record; or
* latest status is `error`; or
* latest record entered a container and has `anchored is False`.

The selector must **not** rerun pre-Docker `not_minable:*` records
(`anchored is None`) and must not rerun valid `anchored is True` terminal
records. This deliberately reopens Q2/Q3: their prior container records exist,
but are methodologically invalid because their image was unanchored.

Records produced by the PDM profile supersede earlier `anchored=false` attempts
only in the latest-record projection. The final report must retain a separate
attempt-history/quarantine note.

## 9. Gates

### Build gate

For a Q2-or-Q3 anchor, image construction must report:

```text
profile = pdm_locked
anchored = true
```

and pass all global plus PDM probes after source deletion.

### Pilot gate

Before any full PDM-era rerun, run a small deterministic pilot covering:

* a `dirty_equals`-using test target;
* a `pytest_examples`/docs target;
* a normal Pydantic test target; and
* a candidate requiring a cached `pydantic-core` pin change.

The pilot must have no environment-closure apparatus outcome. If it does, stop
and diagnose the exact structured collection error before sweeping.

### Sweep and reporting gate

After the five PDM quarters are rerun, the all-12-quarter report must:

* use the fixed candidate manifest and latest record per SHA;
* separate valid anchored outcomes, unanchored historical attempts, `error`,
  and pre-Docker `not_minable` records;
* state conversion and apparatus denominators inline; and
* pass the overall `<10%` apparatus gate for the primary anchored lane before
  claiming a ready benchmark corpus.

## 10. Non-goals

* Supporting every Python package manager in this change.
* Per-candidate full image builds.
* Reclassifying historical unanchored attempts or deleting their JSONL lines.
* Changing the pure verdict taxonomy or candidate-level core alignment policy.
* Solving the separate anchored 2024Q4 pytest `137` process failures. Those
  remain a distinct resource/reporter investigation.

## 11. Acceptance criteria

1. Profile detection selects UV or PDM from an anchor worktree, and refuses
   ambiguous/unsupported lockfile states.
2. A PDM Q2/Q3 image is locked, root-project-free, and passes the stated PDM
   import probes after source deletion.
3. Existing UV-quarter behavior remains locked and covered by regression tests.
4. Core-wheel alignment remains operational in the PDM image.
5. PDM pilot results demonstrate that former missing-test-closure targets
   collect and emit parseable reports.
6. Only the defined incomplete/error/unanchored PDM candidates are rerun.
7. The miner unit suite remains at least 155 green tests before the pilot and
   after the implementation.
