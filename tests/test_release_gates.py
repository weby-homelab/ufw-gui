"""Tests for exact-commit release checks."""

import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from scripts.check_release_gates import (
    CI_CHECK_NAMES,
    CI_WORKFLOW_NAME,
    CI_WORKFLOW_PATH,
    INTEGRATION_JOB_NAME,
    INTEGRATION_WORKFLOW_NAME,
    INTEGRATION_WORKFLOW_PATH,
    ReleaseGateError,
    check_release_gates,
    check_release_order,
)

SHA = "d9cace929adf8eb4bd16bf87edfe6789ce10f256"
CI_RUN_ID = 12345
INTEGRATION_RUN_ID = 67890
CI_JOB_IDS = {name: 1000 + index for index, name in enumerate(CI_CHECK_NAMES, start=1)}
INTEGRATION_JOB_ID = 2001
CREATED_AT = "2026-10-27T20:00:00Z"


class Response:
    status = 200

    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, *_args):
        return json.dumps(self.payload).encode("utf-8")


def successful_payloads():
    names = (*CI_CHECK_NAMES, INTEGRATION_JOB_NAME)
    job_ids = {**CI_JOB_IDS, INTEGRATION_JOB_NAME: INTEGRATION_JOB_ID}
    checks = {
        "total_count": len(names),
        "check_runs": [
            {
                "name": name,
                "head_sha": SHA,
                "status": "completed",
                "conclusion": "success",
                "created_at": CREATED_AT,
                "id": index,
                "app": {"slug": "github-actions"},
                "details_url": (
                    "https://github.com/weby-homelab/ufw-gui/actions/runs/"
                    f"{CI_RUN_ID if name in CI_CHECK_NAMES else INTEGRATION_RUN_ID}"
                    f"/job/{job_ids[name]}"
                ),
            }
            for index, name in enumerate(names, start=1)
        ],
    }
    ci_run = {
        "id": CI_RUN_ID,
        "workflow_id": 101,
        "run_attempt": 1,
        "name": CI_WORKFLOW_NAME,
        "path": f"{CI_WORKFLOW_PATH}@main",
        "event": "push",
        "head_sha": SHA,
        "head_branch": "main",
        "status": "completed",
        "conclusion": "success",
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    integration_run = {
        "id": INTEGRATION_RUN_ID,
        "workflow_id": 102,
        "run_attempt": 1,
        "name": INTEGRATION_WORKFLOW_NAME,
        "path": f"{INTEGRATION_WORKFLOW_PATH}@main",
        "event": "workflow_dispatch",
        "head_sha": SHA,
        "head_branch": "main",
        "status": "completed",
        "conclusion": "success",
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    return checks, ci_run, integration_run


def workflow_jobs(run_id, workflow_name, names, job_ids):
    return {
        "total_count": len(names),
        "jobs": [
            {
                "id": job_ids[name],
                "run_id": run_id,
                "name": name,
                "workflow_name": workflow_name,
                "head_sha": SHA,
                "head_branch": "main",
                "status": "completed",
                "conclusion": "success",
                "started_at": CREATED_AT,
                "completed_at": CREATED_AT,
            }
            for name in names
        ],
    }


def gate_opener(
    checks,
    ci_run,
    integration_run,
    ci_jobs=None,
    integration_jobs=None,
):
    if ci_jobs is None:
        ci_jobs = workflow_jobs(CI_RUN_ID, CI_WORKFLOW_NAME, CI_CHECK_NAMES, CI_JOB_IDS)
    if integration_jobs is None:
        integration_jobs = workflow_jobs(
            INTEGRATION_RUN_ID,
            INTEGRATION_WORKFLOW_NAME,
            (INTEGRATION_JOB_NAME,),
            {INTEGRATION_JOB_NAME: INTEGRATION_JOB_ID},
        )
    return Mock(
        side_effect=[
            Response(checks),
            Response(ci_run),
            Response(ci_jobs),
            Response(integration_run),
            Response(integration_jobs),
        ]
    )


class ReleaseGateTests(unittest.TestCase):
    def test_exact_sha_checks_and_both_trusted_workflows_pass(self):
        checks, ci_run, integration_run = successful_payloads()
        opener = gate_opener(checks, ci_run, integration_run)

        check_release_gates(SHA, "test-token", opener=opener)

        urls = [call.args[0].full_url for call in opener.call_args_list]
        self.assertIn(f"/commits/{SHA}/check-runs?filter=latest&per_page=100", urls[0])
        self.assertTrue(urls[1].endswith(f"/actions/runs/{CI_RUN_ID}"))
        self.assertTrue(
            urls[2].endswith(f"/actions/runs/{CI_RUN_ID}/jobs?per_page=100")
        )
        self.assertTrue(urls[3].endswith(f"/actions/runs/{INTEGRATION_RUN_ID}"))
        self.assertTrue(
            urls[4].endswith(f"/actions/runs/{INTEGRATION_RUN_ID}/jobs?per_page=100")
        )
        for call in opener.call_args_list:
            self.assertEqual(call.args[0].headers["Authorization"], "Bearer test-token")

    def test_latest_duplicate_ci_run_is_used(self):
        checks, ci_run, integration_run = successful_payloads()
        failed_retry = dict(checks["check_runs"][0])
        failed_retry.update(
            {
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-10-27T23:00:00Z",
                "id": 100,
            }
        )
        checks["check_runs"].append(failed_retry)
        checks["total_count"] += 1

        with self.assertRaisesRegex(ReleaseGateError, "did not succeed"):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

    def test_higher_check_run_id_breaks_timestamp_ties(self):
        checks, ci_run, integration_run = successful_payloads()
        failed_retry = dict(checks["check_runs"][0])
        failed_retry.update({"conclusion": "failure", "id": 100})
        checks["check_runs"].append(failed_retry)
        checks["total_count"] += 1

        with self.assertRaisesRegex(ReleaseGateError, "did not succeed"):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

    def test_missing_ci_or_integration_check_blocks_release(self):
        checks, ci_run, integration_run = successful_payloads()
        checks["check_runs"].pop()
        checks["total_count"] -= 1

        with self.assertRaisesRegex(ReleaseGateError, "host-ufw"):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

    def test_failed_or_pending_ci_check_blocks_release(self):
        for status, conclusion in (("in_progress", None), ("completed", "failure")):
            with self.subTest(status=status, conclusion=conclusion):
                checks, ci_run, integration_run = successful_payloads()
                checks["check_runs"][0]["status"] = status
                checks["check_runs"][0]["conclusion"] = conclusion

                with self.assertRaisesRegex(ReleaseGateError, "did not succeed"):
                    check_release_gates(
                        SHA,
                        "test-token",
                        opener=gate_opener(checks, ci_run, integration_run),
                    )

    def test_check_from_different_sha_does_not_satisfy_gate(self):
        checks, ci_run, integration_run = successful_payloads()
        checks["check_runs"][0]["head_sha"] = "0" * 40

        with self.assertRaisesRegex(ReleaseGateError, "missing required"):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

    def test_checks_from_non_github_actions_apps_do_not_satisfy_gate(self):
        checks, ci_run, integration_run = successful_payloads()
        checks["check_runs"][0]["app"]["slug"] = "untrusted-check-writer"

        with self.assertRaisesRegex(ReleaseGateError, "missing required"):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

    def test_required_ci_checks_must_share_the_trusted_main_push_run(self):
        checks, ci_run, integration_run = successful_payloads()
        ci_run["event"] = "pull_request"

        with self.assertRaisesRegex(
            ReleaseGateError, "CI \\(Lint and Build\\) push run"
        ):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

        checks, ci_run, integration_run = successful_payloads()
        checks["check_runs"][1]["details_url"] = (
            "https://github.com/weby-homelab/ufw-gui/actions/runs/99999/job/2"
        )
        with self.assertRaisesRegex(ReleaseGateError, "do not share one trusted"):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

    def test_integration_requires_successful_main_dispatch_for_exact_sha(self):
        checks, ci_run, integration_run = successful_payloads()
        invalid_runs = (
            {**integration_run, "id": INTEGRATION_RUN_ID + 1},
            {**integration_run, "event": "push"},
            {**integration_run, "path": ".github/workflows/other.yml@main"},
            {**integration_run, "head_sha": "0" * 40},
            {**integration_run, "head_branch": "feature/test"},
            {**integration_run, "status": "in_progress"},
            {**integration_run, "conclusion": "failure"},
            {**integration_run, "name": "Different workflow"},
        )
        for index, invalid_run in enumerate(invalid_runs):
            with (
                self.subTest(run=invalid_run),
                self.assertRaisesRegex(
                    ReleaseGateError,
                    (
                        "incomplete workflow-run identifiers"
                        if index == 0
                        else "integration workflow_dispatch run"
                    ),
                ),
            ):
                check_release_gates(
                    SHA,
                    "test-token",
                    opener=gate_opener(checks, ci_run, invalid_run),
                )

    def test_malformed_or_truncated_check_results_fail_closed(self):
        checks, ci_run, integration_run = successful_payloads()
        checks["total_count"] += 1

        with self.assertRaisesRegex(ReleaseGateError, "incomplete CI"):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run),
            )

        for field, value in (
            ("created_at", None),
            ("created_at", "2026-10-27T20:00:00"),
            ("id", None),
        ):
            with self.subTest(field=field, value=value):
                checks, ci_run, integration_run = successful_payloads()
                checks["check_runs"][0][field] = value
                with self.assertRaises(ReleaseGateError):
                    check_release_gates(
                        SHA,
                        "test-token",
                        opener=gate_opener(checks, ci_run, integration_run),
                    )

    def test_next_page_link_blocks_release_even_with_self_consistent_count(self):
        checks, _ci_run, _integration_run = successful_payloads()
        opener = Mock(
            side_effect=[
                Response(
                    checks,
                    headers={
                        "Link": (
                            "<https://api.github.com/repos/weby-homelab/ufw-gui/"
                            'commits/example/check-runs?page=2>; rel="next"'
                        )
                    },
                )
            ]
        )

        with self.assertRaisesRegex(ReleaseGateError, "response is paginated"):
            check_release_gates(SHA, "test-token", opener=opener)

        opener.assert_called_once()

    def test_invalid_integration_check_url_fails_closed(self):
        checks, ci_run, _integration_run = successful_payloads()
        checks["check_runs"][-1]["details_url"] = "https://attacker.example/run/1"
        opener = Mock(
            side_effect=[
                Response(checks),
                Response(ci_run),
                Response(
                    workflow_jobs(
                        CI_RUN_ID, CI_WORKFLOW_NAME, CI_CHECK_NAMES, CI_JOB_IDS
                    )
                ),
            ]
        )

        with self.assertRaisesRegex(ReleaseGateError, "unexpected workflow-run URL"):
            check_release_gates(SHA, "test-token", opener=opener)

        self.assertEqual(opener.call_count, 3)

    def test_job_id_must_match_authoritative_job_name_and_run(self):
        checks, ci_run, integration_run = successful_payloads()
        ci_jobs = workflow_jobs(CI_RUN_ID, CI_WORKFLOW_NAME, CI_CHECK_NAMES, CI_JOB_IDS)
        ci_jobs["jobs"][0]["name"] = "unrelated-job"

        with self.assertRaisesRegex(
            ReleaseGateError, "not a successful exact-SHA main job"
        ):
            check_release_gates(
                SHA,
                "test-token",
                opener=gate_opener(checks, ci_run, integration_run, ci_jobs=ci_jobs),
            )

    def test_redirect_responses_fail_closed(self):
        redirect = HTTPError(
            "https://api.github.com/",
            302,
            "redirect",
            hdrs={"Location": "https://attacker.example/collect"},
            fp=None,
        )
        with self.assertRaisesRegex(ReleaseGateError, "HTTP 302"):
            check_release_gates(SHA, "test-token", opener=Mock(side_effect=redirect))

    def test_release_order_allows_newest_stable_release_and_repair_of_current(self):
        releases = [
            {"tag_name": None, "draft": True, "prerelease": False},
            {
                "tag_name": "v1.6.2",
                "draft": False,
                "prerelease": False,
                "published_at": CREATED_AT,
            },
            {
                "tag_name": "v9.0.0-rc.1",
                "draft": False,
                "prerelease": True,
                "published_at": CREATED_AT,
            },
            {
                "tag_name": "v1.4.2-classic",
                "draft": False,
                "prerelease": False,
                "published_at": CREATED_AT,
            },
        ]
        opener = Mock(return_value=Response(releases))

        check_release_order("v1.6.3", "test-token", opener=opener)
        check_release_order("v1.6.2", "test-token", opener=opener)

        self.assertEqual(opener.call_count, 2)
        self.assertEqual(
            opener.call_args.args[0].full_url,
            "https://api.github.com/repos/weby-homelab/ufw-gui/releases?per_page=100",
        )

    def test_release_order_blocks_older_release_after_newer_version(self):
        releases = [
            {
                "tag_name": "v1.9.0",
                "draft": False,
                "prerelease": False,
                "published_at": CREATED_AT,
            },
            {
                "tag_name": "v1.10.0",
                "draft": False,
                "prerelease": False,
                "published_at": CREATED_AT,
            },
        ]

        with self.assertRaisesRegex(ReleaseGateError, "older than the highest"):
            check_release_order(
                "v1.9.5", "test-token", opener=Mock(return_value=Response(releases))
            )

    def test_release_order_handles_untrusted_oversized_semver_components(self):
        releases = [
            {
                "tag_name": f"v{'9' * 5000}.0.0",
                "draft": False,
                "prerelease": False,
                "published_at": CREATED_AT,
            }
        ]

        with self.assertRaisesRegex(ReleaseGateError, "older than the highest"):
            check_release_order(
                "v1.6.3", "test-token", opener=Mock(return_value=Response(releases))
            )

    def test_release_order_rejects_a_full_page_without_pagination_evidence(self):
        releases = [
            {
                "tag_name": f"v1.6.{patch}",
                "draft": False,
                "prerelease": False,
                "published_at": CREATED_AT,
            }
            for patch in range(100)
        ]

        with self.assertRaisesRegex(ReleaseGateError, "incomplete release history"):
            check_release_order(
                "v1.6.3", "test-token", opener=Mock(return_value=Response(releases))
            )

    def test_release_order_fails_closed_on_missing_token_malformed_history_or_pagination(
        self,
    ):
        opener = Mock()
        with self.assertRaisesRegex(ReleaseGateError, "token is required"):
            check_release_order("v1.6.3", "", opener=opener)
        opener.assert_not_called()

        with self.assertRaisesRegex(ReleaseGateError, "incomplete release metadata"):
            check_release_order(
                "v1.6.3", "test-token", opener=Mock(return_value=Response([{}]))
            )

        paginated = Response(
            [], headers={"Link": '<https://api.github.com/releases?page=2>; rel="next"'}
        )
        with self.assertRaisesRegex(ReleaseGateError, "response is paginated"):
            check_release_order(
                "v1.6.3", "test-token", opener=Mock(return_value=paginated)
            )

    def test_api_errors_fail_closed_without_echoing_response_body(self):
        failure = HTTPError(
            "https://api.github.com/", 403, "forbidden", hdrs=None, fp=None
        )
        opener = Mock(side_effect=failure)

        with self.assertRaisesRegex(ReleaseGateError, "HTTP 403") as raised:
            check_release_gates(SHA, "test-token", opener=opener)
        self.assertNotIn("test-token", str(raised.exception))

    def test_network_errors_fail_closed(self):
        with self.assertRaisesRegex(ReleaseGateError, "URLError"):
            check_release_gates(
                SHA, "test-token", opener=Mock(side_effect=URLError("offline"))
            )

    def test_invalid_sha_or_missing_token_rejected_before_network(self):
        opener = Mock()

        for sha, token in (("not-a-sha", "token"), (SHA, "")):
            with (
                self.subTest(sha=sha, token=bool(token)),
                self.assertRaises(ReleaseGateError),
            ):
                check_release_gates(sha, token, opener=opener)

        opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
