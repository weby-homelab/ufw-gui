"""Require exact-SHA CI and Ubuntu 26 workflow evidence before image publish."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY_API = "https://api.github.com/repos/weby-homelab/ufw-gui"
CI_WORKFLOW_PATH = ".github/workflows/ci.yml"
CI_WORKFLOW_NAME = "CI (Lint and Build)"
INTEGRATION_WORKFLOW_PATH = ".github/workflows/ubuntu26-integration.yml"
INTEGRATION_WORKFLOW_NAME = "Ubuntu 26 Docker and host UFW integration"
INTEGRATION_JOB_NAME = "host-ufw"
CI_CHECK_NAMES = (
    "backend-ruff",
    "backend-tests",
    "backend-compile",
    "backend-lint",
    "frontend-build",
)
CHECK_NAMES = (*CI_CHECK_NAMES, INTEGRATION_JOB_NAME)
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
RELEASE_TAG_PATTERN = re.compile(r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
GITHUB_ACTION_JOB_URL = re.compile(
    r"https://github\.com/weby-homelab/ufw-gui/actions/runs/([1-9][0-9]*)/job/([1-9][0-9]*)"
)
CHECK_STATUSES = {"queued", "in_progress", "completed"}


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _github_urlopen(request: Request, timeout: int = 30):
    """Reject redirects so an Authorization header is never forwarded elsewhere."""
    return build_opener(_RejectRedirects()).open(request, timeout=timeout)


class ReleaseGateError(RuntimeError):
    """Raised when exact-commit release evidence is missing or unsuccessful."""


def _get_json(path: str, token: str, opener=_github_urlopen):
    request = Request(
        f"{REPOSITORY_API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )
    try:
        with opener(request, timeout=30) as response:
            if not 200 <= response.status < 300:
                raise ReleaseGateError(
                    f"GitHub release-gate API request failed with HTTP {response.status}"
                )
            headers = getattr(response, "headers", None)
            if headers is None or not hasattr(headers, "get"):
                raise ReleaseGateError("GitHub response omitted HTTP headers")
            link_header = headers.get("Link", "")
            if not isinstance(link_header, str):
                raise ReleaseGateError("GitHub returned malformed pagination headers")
            if re.search(
                r'<[^>]+>\s*;[^,]*\brel="?next"?\b', link_header, re.IGNORECASE
            ):
                raise ReleaseGateError("GitHub release-gate API response is paginated")
            return json.load(response)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise ReleaseGateError(
            f"GitHub release-gate API request failed with HTTP {status}"
        ) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise ReleaseGateError(
            f"GitHub release-gate API request failed ({type(exc).__name__})"
        ) from None
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        raise ReleaseGateError(
            "GitHub release-gate API returned invalid JSON"
        ) from None


def _validated_created_at(item: dict) -> tuple[datetime, int]:
    created_at = item.get("created_at")
    identifier = item.get("id")
    if (
        not isinstance(created_at, str)
        or not isinstance(identifier, int)
        or isinstance(identifier, bool)
        or identifier < 1
    ):
        raise ReleaseGateError("GitHub returned incomplete check-run metadata")
    try:
        parsed = datetime.fromisoformat(created_at)
    except ValueError:
        raise ReleaseGateError(
            "GitHub returned an invalid check-run timestamp"
        ) from None
    if parsed.tzinfo is None:
        raise ReleaseGateError("GitHub returned a timezone-naive check-run timestamp")
    return parsed, identifier


def _latest_check_run(items: list[dict]) -> dict:
    return max(items, key=_validated_created_at)


def _validate_timestamp(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise ReleaseGateError(f"GitHub returned incomplete {field_name} metadata")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ReleaseGateError(
            f"GitHub returned an invalid {field_name} timestamp"
        ) from None
    if parsed.tzinfo is None:
        raise ReleaseGateError(
            f"GitHub returned a timezone-naive {field_name} timestamp"
        )


def _trusted_github_actions_run(check: dict, sha: str) -> tuple[int, int]:
    app = check.get("app")
    details_url = check.get("details_url")
    if not isinstance(app, dict) or app.get("slug") != "github-actions":
        raise ReleaseGateError(
            "Required release check was not created by GitHub Actions"
        )
    if not isinstance(details_url, str):
        raise ReleaseGateError("Ubuntu 26 check has no trusted workflow-run URL")
    match = GITHUB_ACTION_JOB_URL.fullmatch(details_url)
    if match is None:
        raise ReleaseGateError("Ubuntu 26 check has an unexpected workflow-run URL")
    _validated_created_at(check)
    if str(check.get("head_sha", "")).lower() != sha:
        raise ReleaseGateError("Ubuntu 26 check does not match the release SHA")
    if check.get("status") != "completed" or check.get("conclusion") != "success":
        raise ReleaseGateError(
            "Ubuntu 26 integration is not successful for release SHA"
        )
    return int(match.group(1)), int(match.group(2))


def _verify_workflow_run(
    run_id: int,
    sha: str,
    expected_path: str,
    expected_name: str,
    expected_event: str,
    token: str,
    opener=_github_urlopen,
) -> None:
    run = _get_json(f"/actions/runs/{run_id}", token, opener=opener)
    expected_paths = {
        expected_path,
        f"{expected_path}@main",
        f"{expected_path}@refs/heads/main",
    }
    if not isinstance(run, dict):
        raise ReleaseGateError("GitHub returned invalid workflow-run data")
    workflow_id = run.get("workflow_id")
    run_attempt = run.get("run_attempt")
    if (
        not isinstance(run.get("id"), int)
        or isinstance(run.get("id"), bool)
        or run.get("id") != run_id
        or not isinstance(workflow_id, int)
        or isinstance(workflow_id, bool)
        or workflow_id < 1
        or not isinstance(run_attempt, int)
        or isinstance(run_attempt, bool)
        or run_attempt < 1
    ):
        raise ReleaseGateError("GitHub returned incomplete workflow-run identifiers")
    _validate_timestamp(run.get("created_at"), "workflow-run created_at")
    _validate_timestamp(run.get("updated_at"), "workflow-run updated_at")
    if (
        run.get("path") not in expected_paths
        or run.get("name") != expected_name
        or run.get("event") != expected_event
        or str(run.get("head_sha", "")).lower() != sha
        or run.get("head_branch") != "main"
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        raise ReleaseGateError(
            f"Evidence is not a successful {expected_name} {expected_event} run on main for release SHA"
        )


def _verify_workflow_jobs(
    run_id: int,
    expected_job_ids: dict[str, int],
    sha: str,
    workflow_name: str,
    token: str,
    opener=_github_urlopen,
) -> None:
    payload = _get_json(
        f"/actions/runs/{run_id}/jobs?per_page=100", token, opener=opener
    )
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("jobs"), list)
        or not isinstance(payload.get("total_count"), int)
        or isinstance(payload.get("total_count"), bool)
        or payload["total_count"] != len(payload["jobs"])
    ):
        raise ReleaseGateError("GitHub returned incomplete workflow-job data")

    jobs_by_id: dict[int, dict] = {}
    for job in payload["jobs"]:
        if not isinstance(job, dict):
            raise ReleaseGateError("GitHub returned malformed workflow-job data")
        job_id = job.get("id")
        if (
            not isinstance(job_id, int)
            or isinstance(job_id, bool)
            or job_id < 1
            or not isinstance(job.get("run_id"), int)
            or isinstance(job.get("run_id"), bool)
            or job.get("run_id") != run_id
            or not isinstance(job.get("name"), str)
            or not isinstance(job.get("workflow_name"), str)
            or not isinstance(job.get("head_branch"), str)
            or not SHA_PATTERN.fullmatch(str(job.get("head_sha", "")))
            or job.get("status") not in CHECK_STATUSES
            or (
                job.get("conclusion") is not None
                and not isinstance(job.get("conclusion"), str)
            )
        ):
            raise ReleaseGateError("GitHub returned malformed workflow-job metadata")
        _validate_timestamp(job.get("started_at"), "workflow-job started_at")
        _validate_timestamp(job.get("completed_at"), "workflow-job completed_at")
        if job_id in jobs_by_id:
            raise ReleaseGateError("GitHub returned duplicate workflow-job identifiers")
        jobs_by_id[job_id] = job

    expected_ids = list(expected_job_ids.values())
    if len(set(expected_ids)) != len(expected_ids):
        raise ReleaseGateError("Required checks point to duplicate workflow jobs")
    for expected_name, job_id in expected_job_ids.items():
        job = jobs_by_id.get(job_id)
        if (
            job is None
            or job.get("name") != expected_name
            or job.get("run_id") != run_id
            or str(job.get("head_sha", "")).lower() != sha
            or job.get("workflow_name") != workflow_name
            or job.get("head_branch") != "main"
            or job.get("status") != "completed"
            or job.get("conclusion") != "success"
        ):
            raise ReleaseGateError(
                f"GitHub workflow job {expected_name} is not a successful exact-SHA main job"
            )


def _require_checks_success(sha: str, token: str, opener=_github_urlopen) -> None:
    payload = _get_json(
        f"/commits/{sha}/check-runs?filter=latest&per_page=100",
        token,
        opener=opener,
    )
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("check_runs"), list)
        or not isinstance(payload.get("total_count"), int)
        or isinstance(payload.get("total_count"), bool)
        or payload["total_count"] != len(payload["check_runs"])
    ):
        raise ReleaseGateError("GitHub returned incomplete CI check-run data")

    candidates: dict[str, list[dict]] = {name: [] for name in CHECK_NAMES}
    check_ids: set[int] = set()
    for check in payload["check_runs"]:
        if not isinstance(check, dict):
            raise ReleaseGateError("GitHub returned malformed CI check-run data")
        app = check.get("app")
        if (
            not isinstance(check.get("name"), str)
            or not SHA_PATTERN.fullmatch(str(check.get("head_sha", "")))
            or check.get("status") not in CHECK_STATUSES
            or (
                check.get("conclusion") is not None
                and not isinstance(check.get("conclusion"), str)
            )
            or not isinstance(app, dict)
            or not isinstance(app.get("slug"), str)
            or (
                check.get("details_url") is not None
                and not isinstance(check.get("details_url"), str)
            )
        ):
            raise ReleaseGateError("GitHub returned malformed CI check-run metadata")
        _validated_created_at(check)
        check_id = check["id"]
        if check_id in check_ids:
            raise ReleaseGateError("GitHub returned duplicate CI check-run identifiers")
        check_ids.add(check_id)
        if check["name"] not in candidates:
            continue
        if (
            isinstance(app, dict)
            and app.get("slug") == "github-actions"
            and str(check.get("head_sha", "")).lower() == sha
        ):
            candidates[check["name"]].append(check)

    missing = [name for name, runs in candidates.items() if not runs]
    if missing:
        raise ReleaseGateError(
            "missing required GitHub Actions checks for release SHA: "
            + ", ".join(missing)
        )

    latest_runs = {name: _latest_check_run(runs) for name, runs in candidates.items()}
    unsuccessful = [
        name
        for name in CHECK_NAMES
        if latest_runs[name].get("status") != "completed"
        or latest_runs[name].get("conclusion") != "success"
    ]
    if unsuccessful:
        raise ReleaseGateError(
            "required CI checks did not succeed for release SHA: "
            + ", ".join(unsuccessful)
        )

    ci_run_ids: set[int] = set()
    ci_job_ids: dict[str, int] = {}
    for name in CI_CHECK_NAMES:
        run_id, job_id = _trusted_github_actions_run(latest_runs[name], sha)
        ci_run_ids.add(run_id)
        ci_job_ids[name] = job_id
    if len(ci_run_ids) != 1:
        raise ReleaseGateError(
            "Required CI checks do not share one trusted workflow run"
        )
    ci_run_id = ci_run_ids.pop()
    _verify_workflow_run(
        ci_run_id,
        sha,
        CI_WORKFLOW_PATH,
        CI_WORKFLOW_NAME,
        "push",
        token,
        opener=opener,
    )
    _verify_workflow_jobs(
        ci_run_id,
        ci_job_ids,
        sha,
        CI_WORKFLOW_NAME,
        token,
        opener=opener,
    )

    integration_run_id, integration_job_id = _trusted_github_actions_run(
        latest_runs[INTEGRATION_JOB_NAME], sha
    )
    _verify_workflow_run(
        integration_run_id,
        sha,
        INTEGRATION_WORKFLOW_PATH,
        INTEGRATION_WORKFLOW_NAME,
        "workflow_dispatch",
        token,
        opener=opener,
    )
    _verify_workflow_jobs(
        integration_run_id,
        {INTEGRATION_JOB_NAME: integration_job_id},
        sha,
        INTEGRATION_WORKFLOW_NAME,
        token,
        opener=opener,
    )


def check_release_gates(sha: str, token: str, opener=_github_urlopen) -> None:
    """Fail closed unless CI and the exact trusted integration workflow pass."""
    if not SHA_PATTERN.fullmatch(sha):
        raise ReleaseGateError("release SHA must be a full lowercase commit SHA")
    if not token:
        raise ReleaseGateError("GitHub token is required to verify release gates")
    _require_checks_success(sha, token, opener=opener)


def _numeric_version_order(parts: tuple[str, ...]) -> tuple[tuple[int, str], ...]:
    """Compare arbitrarily long canonical numeric components without int conversion."""
    return tuple((len(part), part) for part in parts)


def check_release_order(release_tag: str, token: str, opener=_github_urlopen) -> None:
    """Prevent an older published release from regressing the mutable latest tag."""
    if not token:
        raise ReleaseGateError("GitHub token is required to verify release order")
    match = RELEASE_TAG_PATTERN.fullmatch(release_tag)
    if match is None or not release_tag.startswith("v"):
        raise ReleaseGateError("release tag must be vMAJOR.MINOR.PATCH")
    candidate = _numeric_version_order(match.groups())
    releases = _get_json("/releases?per_page=100", token, opener=opener)
    if not isinstance(releases, list) or len(releases) >= 100:
        raise ReleaseGateError("GitHub returned invalid or incomplete release history")

    highest_stable: tuple[tuple[int, str], ...] | None = None
    for release in releases:
        if not isinstance(release, dict):
            raise ReleaseGateError("GitHub returned malformed release metadata")
        draft = release.get("draft")
        prerelease = release.get("prerelease")
        if not isinstance(draft, bool) or not isinstance(prerelease, bool):
            raise ReleaseGateError("GitHub returned incomplete release metadata")
        if draft:
            continue
        tag_name = release.get("tag_name")
        if not isinstance(tag_name, str):
            raise ReleaseGateError("GitHub returned incomplete release metadata")
        if prerelease:
            continue
        _validate_timestamp(release.get("published_at"), "release published_at")
        stable_match = RELEASE_TAG_PATTERN.fullmatch(tag_name)
        if stable_match is None:
            continue
        version = _numeric_version_order(stable_match.groups())
        if highest_stable is None or version > highest_stable:
            highest_stable = version

    if highest_stable is not None and candidate < highest_stable:
        raise ReleaseGateError(
            "release tag is older than the highest published stable release"
        )


def main() -> int:
    try:
        api_credential = os.environ.get("GH_TOKEN", "")
        check_release_gates(os.environ.get("GITHUB_SHA", ""), api_credential)
        check_release_order(os.environ.get("RELEASE_TAG", ""), api_credential)
    except ReleaseGateError as exc:
        print(f"Release gate check failed: {exc}", file=sys.stderr)
        return 1
    print("CI, Ubuntu 26 integration, and monotonic release-order checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
