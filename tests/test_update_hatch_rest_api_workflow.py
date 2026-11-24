"""Tests for the hatch-rest-api dependency update workflow."""

from __future__ import annotations

from importlib import util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

WORKFLOW_PATH = Path(".github/workflows/update_hatch_rest_api.yml")
SCRIPT_PATH = Path(".github/scripts/update_hatch_rest_api_pins.py")
RELEASE_NOTES_SCRIPT_PATH = Path(".github/scripts/build_hatch_rest_api_release_notes.py")
CLEANUP_SCRIPT_PATH = Path(".github/scripts/cleanup_hatch_rest_api_update_branches.py")


class FakeCleanupClient:
    """Fake GitHub cleanup client that records mutating calls."""

    def __init__(
        self,
        *,
        open_pulls: list[dict[str, object]],
        closed_pulls: list[dict[str, object]],
        fail_on_close: bool = False,
    ) -> None:
        """Initialize fake pull request state.

        Args:
            open_pulls: Pull requests to return for open PR lookups.
            closed_pulls: Pull requests to return for closed PR lookups.
            fail_on_close: Whether closing a PR should fail the test.
        """
        self.open_pulls = open_pulls
        self.closed_pulls = closed_pulls
        self.fail_on_close = fail_on_close
        self.closed_prs: list[int] = []
        self.deleted_refs: list[str] = []

    def list_pulls(self, *, state: str) -> list[dict[str, object]]:
        """Return fake pull requests by state."""
        return self.open_pulls if state == "open" else self.closed_pulls

    def close_pull(self, pull_number: int) -> None:
        """Record or reject a closed pull request."""
        if self.fail_on_close:
            raise AssertionError(f"Unexpected close for PR {pull_number}")
        self.closed_prs.append(pull_number)

    def delete_ref(self, ref: str) -> None:
        """Record a deleted git ref."""
        self.deleted_refs.append(ref)


def _workflow_pull(
    *,
    number: int,
    ref: str = "chore/update-hatch-rest-api-dependency",
    label: str = "hatch-rest-api-auto-update",
    merged_at: str | None = None,
) -> dict[str, object]:
    """Return a fake workflow pull request object.

    Args:
        number: Pull request number.
        ref: Pull request head ref.
        label: Pull request label name.
        merged_at: Optional merge timestamp for closed PRs.

    Returns:
        Fake pull request object shaped like the GitHub REST API response.
    """
    return {
        "number": number,
        "merged_at": merged_at,
        "head": {"ref": ref, "repo": {"full_name": "o/r"}},
        "labels": [{"name": label}],
    }


def _write_pin_files(
    tmp_path: Path,
    *,
    manifest_version: str,
    pyproject_version: str | None = None,
    pyproject_text: str | None = None,
) -> tuple[Path, Path]:
    """Write temporary manifest and pyproject files with hatch-rest-api pins."""
    manifest_path = tmp_path / "manifest.json"
    pyproject_path = tmp_path / "pyproject.toml"
    manifest_path.write_text(
        json.dumps(
            {
                "requirements": [
                    "numpy==2.3.5",
                    f"hatch-rest-api=={manifest_version}",
                ],
            },
        ),
    )

    if pyproject_text is None:
        pyproject_text = f"""[dependency-groups]
ha = [
    "hatch-rest-api=={pyproject_version or manifest_version}",
]
"""
    pyproject_path.write_text(pyproject_text)
    return manifest_path, pyproject_path


@pytest.fixture
def updater_script() -> ModuleType:
    """Load the hatch-rest-api pin updater script as a test module."""
    return _load_script("update_hatch_rest_api_pins", SCRIPT_PATH)


@pytest.fixture
def release_notes_script() -> ModuleType:
    """Load the hatch-rest-api release-note builder script as a test module."""
    return _load_script("build_hatch_rest_api_release_notes", RELEASE_NOTES_SCRIPT_PATH)


@pytest.fixture
def cleanup_script() -> ModuleType:
    """Load the hatch-rest-api cleanup script as a test module."""
    return _load_script("cleanup_hatch_rest_api_update_branches", CLEANUP_SCRIPT_PATH)


def _load_script(module_name: str, script_path: Path) -> ModuleType:
    """Load a checked-in workflow helper script as a test module."""
    spec = util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "needle",
    [
        "actions/setup-python@v7",
        "python-version: '3.14'",
        "Automated update of hatch-rest-api dependency pins.",
        "custom_components/ha_hatch/manifest.json",
        "pyproject.toml",
        "pyproject_current",
        str(SCRIPT_PATH),
        str(RELEASE_NOTES_SCRIPT_PATH),
        str(CLEANUP_SCRIPT_PATH),
        "--body-path hatch-rest-api-update-pr-body.md",
        "--delete-merged-branches",
        "LATEST_VERSION: ${{ steps.versions.outputs.latest }}",
        '--latest-version "$LATEST_VERSION"',
        "REPOSITORY: ${{ github.repository }}",
        '--repository "$REPOSITORY"',
    ],
)
def test_workflow_contains_expected_update_logic(needle: str) -> None:
    """Workflow should include the expected hatch-rest-api updater logic."""
    assert needle in _read_update_workflow_surface()


def test_workflow_avoids_inline_repository_template_expansion() -> None:
    """Workflow should not expand the repository context inside shell scripts."""
    assert '--repository "${{ github.repository }}"' not in WORKFLOW_PATH.read_text()


def _read_update_workflow_surface() -> str:
    """Read workflow and helper surfaces checked by workflow assertions."""
    return (
        f"{WORKFLOW_PATH.read_text()}\n"
        f"{RELEASE_NOTES_SCRIPT_PATH.read_text()}\n"
        f"{CLEANUP_SCRIPT_PATH.read_text()}"
    )


@pytest.mark.parametrize(
    (
        "manifest_version",
        "pyproject_version",
        "latest_version",
        "expected_update_needed",
        "expected_target",
    ),
    [
        ("3.3.0", "3.3.0", "3.4.0", True, "3.4.0"),
        ("3.3.0", "3.3.0", "3.4.0rc1", False, "3.3.0"),
        ("3.4.0rc1", "3.4.0rc1", "3.4.0", True, "3.4.0"),
        ("3.3.10", "3.3.9", "3.3.9", True, "3.3.10"),
    ],
)
def test_updater_script_pin_update_scenarios(
    tmp_path: Path,
    updater_script: ModuleType,
    manifest_version: str,
    pyproject_version: str,
    latest_version: str,
    expected_update_needed: bool,
    expected_target: str,
) -> None:
    """Updater script should handle stable, prerelease, and drift pin scenarios."""
    manifest_path, pyproject_path = _write_pin_files(
        tmp_path,
        manifest_version=manifest_version,
        pyproject_version=pyproject_version,
    )

    result = updater_script.update_pins(
        manifest_path=manifest_path,
        pyproject_path=pyproject_path,
        latest_version=latest_version,
    )

    assert result.current == manifest_version
    assert result.pyproject_current == pyproject_version
    assert result.latest == expected_target
    assert result.update_needed is expected_update_needed
    assert f"hatch-rest-api=={expected_target}" in manifest_path.read_text()
    assert f'    "hatch-rest-api=={expected_target}",' in pyproject_path.read_text()


def test_updater_script_updates_pyproject_pin_without_trailing_comma(
    tmp_path: Path, updater_script: ModuleType
) -> None:
    """Updater script should preserve valid TOML dependency-list formatting."""
    manifest_path, pyproject_path = _write_pin_files(
        tmp_path,
        manifest_version="3.3.0",
        pyproject_text="""[dependency-groups]
ha = [
    "homeassistant",
    "hatch-rest-api==3.3.0"
]
""",
    )

    result = updater_script.update_pins(
        manifest_path=manifest_path,
        pyproject_path=pyproject_path,
        latest_version="3.4.0",
    )

    assert result.update_needed is True
    assert '    "hatch-rest-api==3.4.0"\n' in pyproject_path.read_text()


@pytest.mark.parametrize(
    ("payload", "expected_latest"),
    [
        (
            {
                "info": {"version": "3.4.0rc1"},
                "releases": {
                    "3.3.0": [{"filename": "hatch-rest-api-3.3.0.tar.gz"}],
                    "3.3.1": [{"filename": "hatch-rest-api-3.3.1.tar.gz"}],
                    "3.4.0rc1": [{"filename": "hatch-rest-api-3.4.0rc1.tar.gz"}],
                },
            },
            "3.3.1",
        ),
        (
            {
                "releases": {
                    "3.3.0": [{"filename": "hatch-rest-api-3.3.0.tar.gz"}],
                    "3.3.1": [],
                    "3.3.2": [{"filename": "hatch-rest-api-3.3.2.tar.gz", "yanked": True}],
                },
            },
            "3.3.0",
        ),
    ],
)
def test_updater_script_selects_latest_stable_from_pypi_payload(
    updater_script: ModuleType,
    payload: dict[str, object],
    expected_latest: str,
) -> None:
    """Updater script should select the latest installable stable PyPI release."""
    latest = updater_script._select_latest_stable_version(
        payload,
    )

    assert latest == expected_latest


def test_updater_script_rejects_duplicate_pyproject_pins(
    tmp_path: Path,
    updater_script: ModuleType,
) -> None:
    """Updater script should fail clearly when pyproject has ambiguous pins."""
    manifest_path, pyproject_path = _write_pin_files(
        tmp_path,
        manifest_version="3.3.0",
        pyproject_text="""[dependency-groups]
ha = [
    "hatch-rest-api==3.3.0",
    "hatch-rest-api==3.3.1",
]
""",
    )

    with pytest.raises(ValueError, match="Expected exactly one pinned hatch-rest-api dependency"):
        updater_script.update_pins(
            manifest_path=manifest_path,
            pyproject_path=pyproject_path,
            latest_version="3.4.0",
        )


def test_updater_script_logs_fetch_errors(
    updater_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Updater script should log PyPI fetch failures before re-raising."""

    def raise_url_error(*_: object, **__: object) -> object:
        """Raise a urlopen-style network failure."""
        raise updater_script.URLError("DNS failure")

    monkeypatch.setattr(updater_script, "urlopen", raise_url_error)
    caplog.set_level("ERROR", logger=updater_script.__name__)

    with pytest.raises(updater_script.URLError, match="DNS failure"):
        updater_script.fetch_latest_version()

    assert "Failed to fetch hatch-rest-api PyPI metadata" in caplog.text


def test_updater_script_main_handles_fetch_errors(
    tmp_path: Path,
    updater_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Updater script should return a failing status for fetch errors."""
    manifest_path, pyproject_path = _write_pin_files(tmp_path, manifest_version="3.3.0")

    def raise_url_error() -> str:
        """Raise a PyPI fetch failure."""
        raise updater_script.URLError("DNS failure")

    monkeypatch.setattr(updater_script, "fetch_latest_version", raise_url_error)
    caplog.set_level("ERROR", logger=updater_script.__name__)

    result = updater_script.main(
        [
            "--manifest-path",
            str(manifest_path),
            "--pyproject-path",
            str(pyproject_path),
        ],
    )

    assert result == 1
    assert "Failed to update hatch-rest-api dependency pins" in caplog.text


def test_release_note_script_builds_sanitized_pr_body(
    tmp_path: Path,
    release_notes_script: ModuleType,
) -> None:
    """Release-note script should build a mention-safe PR body file."""
    releases = [
        {
            "tag_name": "3.3.0",
            "name": "Ignored current",
            "body": "old",
            "html_url": "https://example.test/3.3.0",
        },
        {
            "tag_name": "3.3.1",
            "name": "Fixes @someone",
            "body": "fixes #123 and thanks [@helper](https://github.com/helper)",
            "html_url": "https://example.test/3.3.1",
        },
        {
            "tag_name": "3.4.0rc1",
            "name": "Ignored prerelease",
            "body": "future",
            "html_url": "https://example.test/3.4.0rc1",
        },
    ]
    body_path = tmp_path / "body.md"

    release_notes_script.write_pr_body(
        body_path=body_path,
        releases=releases,
        current_version="3.3.0",
        pyproject_current_version="3.3.0",
        latest_version="3.3.1",
    )

    body = body_path.read_text()
    assert "Automated update of hatch-rest-api dependency pins." in body
    assert "Updated pinned version: `hatch-rest-api==3.3.1`" in body
    assert "### Fixes @<!-- -->someone (3.3.1)" in body
    assert "fixes \\#123 and thanks helper" in body
    assert "Ignored current" not in body
    assert "Ignored prerelease" not in body


def test_release_note_script_handles_url_errors(
    tmp_path: Path,
    release_notes_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release-note script should report network failures without a traceback."""

    def raise_url_error(**_: object) -> list[dict[str, object]]:
        """Raise a urlopen-style network failure."""
        raise release_notes_script.URLError("DNS failure")

    monkeypatch.setattr(release_notes_script, "fetch_releases", raise_url_error)

    result = release_notes_script.main(
        [
            "--current-version",
            "3.3.0",
            "--pyproject-current-version",
            "3.3.0",
            "--latest-version",
            "3.3.1",
            "--release-owner",
            "dahlb",
            "--release-repo",
            "hatch_rest_api",
            "--body-path",
            str(tmp_path / "body.md"),
        ],
    )

    assert result == 1


def test_cleanup_script_closes_stale_prs_and_deletes_workflow_branches(
    cleanup_script: ModuleType,
) -> None:
    """Cleanup script should close stale PRs and remove workflow-created branches."""
    client = FakeCleanupClient(
        open_pulls=[
            _workflow_pull(number=10),
            _workflow_pull(number=9, ref="chore/update-hatch-rest-api-old"),
            _workflow_pull(number=11, ref="feature/manual"),
        ],
        closed_pulls=[
            _workflow_pull(number=8, merged_at="2026-05-28T00:00:00Z"),
            _workflow_pull(number=7, ref="chore/update-hatch-rest-api-old"),
        ],
    )

    result = cleanup_script.cleanup_update_branches(
        client=client,
        repository="o/r",
        branch="chore/update-hatch-rest-api-dependency",
        branch_prefix="chore/update-hatch-rest-api",
        label_name="hatch-rest-api-auto-update",
        keep_pr_number=None,
        close_stale_prs=True,
        delete_stale_branch=True,
        delete_merged_branches=True,
    )

    assert client.closed_prs == [10, 9]
    assert client.deleted_refs == [
        "heads/chore/update-hatch-rest-api-dependency",
        "heads/chore/update-hatch-rest-api-old",
    ]
    assert result.closed_prs == [10, 9]
    assert result.deleted_branches == [
        "chore/update-hatch-rest-api-dependency",
        "chore/update-hatch-rest-api-old",
    ]


def test_cleanup_script_keeps_active_update_branch(cleanup_script: ModuleType) -> None:
    """Cleanup script should not delete the branch for the kept update PR."""
    client = FakeCleanupClient(
        open_pulls=[_workflow_pull(number=12)],
        closed_pulls=[
            _workflow_pull(number=8, merged_at="2026-05-28T00:00:00Z"),
            _workflow_pull(
                number=6,
                ref="chore/update-hatch-rest-api-old",
                merged_at="2026-05-20T00:00:00Z",
            ),
        ],
        fail_on_close=True,
    )

    result = cleanup_script.cleanup_update_branches(
        client=client,
        repository="o/r",
        branch="chore/update-hatch-rest-api-dependency",
        branch_prefix="chore/update-hatch-rest-api",
        label_name="hatch-rest-api-auto-update",
        keep_pr_number=12,
        close_stale_prs=True,
        delete_stale_branch=False,
        delete_merged_branches=True,
    )

    assert client.deleted_refs == ["heads/chore/update-hatch-rest-api-old"]
    assert result.closed_prs == []
    assert result.deleted_branches == ["chore/update-hatch-rest-api-old"]
