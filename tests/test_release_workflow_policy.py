"""Security invariants for the Docker publish workflow."""

import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/docker-publish.yml"


class ReleaseWorkflowPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.triggers = cls.source.split("jobs:", maxsplit=1)[0]

    def test_publish_runs_only_for_published_release_events(self):
        self.assertRegex(
            self.triggers,
            r"(?m)^on:\n  release:\n    types: \[published\]$",
        )
        self.assertNotRegex(self.triggers, r"(?m)^  push:")
        self.assertIn("group: docker-publish-stable-releases", self.triggers)
        self.assertIn("cancel-in-progress: false", self.triggers)
        self.assertIn("queue: max", self.triggers)

    def test_all_external_actions_are_pinned_to_full_commit_shas(self):
        actions = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", self.source)

        self.assertEqual(len(actions), 7)
        self.assertTrue(
            all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in actions),
            actions,
        )

    def test_checkout_does_not_persist_credentials_and_token_is_minimal(self):
        checkout_start = self.source.index("uses: actions/checkout@")
        checkout_end = self.source.index("- name: Validate release tag", checkout_start)
        checkout = self.source[checkout_start:checkout_end]

        self.assertIn("persist-credentials: false", checkout)
        self.assertIn("fetch-depth: 0", checkout)
        self.assertIn("ref: ${{ github.sha }}", checkout)
        self.assertRegex(self.source, r"(?m)^      contents: read$")
        self.assertNotIn("packages: write", self.source)

    def test_release_commit_and_version_are_verified_before_registry_auth(self):
        validation = self.source.index("name: Validate release tag and version sources")
        login = self.source.index("name: Log in to Docker Hub")
        validation_block = self.source[validation:login]

        event_sha_check = validation_block.index("RELEASE_SHA: ${{ github.sha }}")
        tag_commit_check = validation_block.index(
            'git rev-parse "refs/tags/${RELEASE_TAG}^{commit}"'
        )
        ancestry_check = validation_block.index(
            'git merge-base --is-ancestor "$RELEASE_SHA" origin/main'
        )
        clean_checkout_check = validation_block.index("git status --porcelain")
        release_gates = self.source.index(
            'python3 -P "$RUNNER_TEMP/release-gate/scripts/check_release_gates.py"'
        )
        repository_code = self.source.index(
            "python3 -P -m scripts.check_docker_tags --allow-existing"
        )
        postflight_step = self.source.index(
            "name: Verify checkout remains clean after preflight"
        )
        postflight_clean_check = self.source.index(
            "git status --porcelain", postflight_step
        )
        self.assertLess(event_sha_check, tag_commit_check)
        self.assertLess(tag_commit_check, ancestry_check)
        self.assertLess(ancestry_check, clean_checkout_check)
        self.assertLess(clean_checkout_check, release_gates)
        self.assertLess(release_gates, repository_code)
        self.assertLess(repository_code, postflight_clean_check)
        self.assertLess(validation, login)
        self.assertIn("type=semver,pattern={{version}}", self.source)
        self.assertNotIn("type=raw,value=latest", self.source)

    def test_publish_reads_ci_and_integration_gate_permissions(self):
        permissions_start = self.source.index("    permissions:")
        steps_start = self.source.index("    steps:", permissions_start)
        permissions = self.source[permissions_start:steps_start]
        self.assertIn("checks: read", permissions)
        self.assertIn("actions: read", permissions)
        self.assertIn("contents: read", permissions)

    def test_privileged_gate_script_is_loaded_from_main_not_release_checkout(self):
        trusted_copy = self.source.index(
            'git show "${trusted_main_sha}:scripts/$script"'
        )
        gate = self.source.index(
            'python3 -P "$RUNNER_TEMP/release-gate/scripts/check_release_gates.py"'
        )
        docker_preflight = self.source.index("python3 -P -m scripts.check_docker_tags")
        self.assertLess(trusted_copy, gate)
        self.assertLess(trusted_copy, docker_preflight)
        self.assertEqual(
            self.source.count(
                'python3 -P "$RUNNER_TEMP/release-gate/scripts/check_release_gates.py"'
            ),
            2,
        )
        self.assertEqual(
            self.source.count("RELEASE_TAG: ${{ github.event.release.tag_name }}"), 7
        )
        self.assertIn("promote_docker_tags.py", self.source)
        self.assertNotIn("python3 -m scripts.check_release_gates", self.source)
        docker_block = self.source[
            self.source.index("name: Verify Docker Hub immutable tag policy") :
        ]
        self.assertIn("PYTHONPATH: ${{ runner.temp }}/release-gate", docker_block)
        self.assertIn("UFW_GUI_PROJECT_ROOT: ${{ github.workspace }}", docker_block)
        self.assertIn("id: registry-preflight", docker_block)
        self.assertIn(
            "steps.registry-preflight.outputs.version_tag_exists", self.source
        )
        self.assertIn(
            "steps.registry-preflight.outputs.v_version_tag_exists", self.source
        )
        self.assertIn("digest-mismatch: error", self.source)

    def test_release_refs_are_revalidated_immediately_before_docker_login(self):
        validation = self.source.index(
            "name: Revalidate immutable release refs before registry authentication"
        )
        final_gate = self.source.index(
            "name: Reconfirm exact-SHA CI and Ubuntu 26 gates"
        )
        login = self.source.index("name: Log in to Docker Hub")
        build = self.source.index("name: Push or safely resume immutable version tags")
        block = self.source[validation:login]
        self.assertIn("git fetch --force --no-tags origin", block)
        self.assertIn(
            'release_commit="$(git rev-parse "refs/tags/${RELEASE_TAG}^{commit}")"',
            block,
        )
        self.assertIn('git merge-base --is-ancestor "$RELEASE_SHA" origin/main', block)
        self.assertLess(final_gate, validation)
        self.assertLess(validation, login)
        self.assertLess(login, build)

    def test_local_build_precedes_credentials_and_latest_is_promoted_last(self):
        metadata = self.source.index("name: Extract metadata (labels) for Docker")
        build = self.source.index("name: Build Docker image locally before publishing")
        final_gate = self.source.index(
            "name: Reconfirm exact-SHA CI and Ubuntu 26 gates"
        )
        final_registry_gate = self.source.index(
            "name: Reconfirm Docker Hub policy and tag availability"
        )
        login = self.source.index("name: Log in to Docker Hub")
        version_push = self.source.index(
            "name: Push or safely resume immutable version tags"
        )
        latest_gate = self.source.index(
            "name: Reconfirm release order before moving latest"
        )
        workflow_end = self.source.index(
            'python3 -P "$RUNNER_TEMP/release-gate/scripts/promote_docker_tags.py" --latest'
        )
        build_block = self.source[build:final_gate]
        promotion_block = self.source[version_push:latest_gate]
        self.assertIn("platforms: linux/amd64", build_block)
        self.assertIn("load: true", build_block)
        self.assertNotIn("push: true", build_block)
        self.assertIn("github-token: ''", build_block)
        self.assertLess(metadata, build)
        self.assertLess(build, final_gate)
        self.assertLess(final_gate, final_registry_gate)
        self.assertLess(final_registry_gate, login)
        self.assertLess(login, version_push)
        self.assertIn("promote_docker_tags.py", promotion_block)
        self.assertLess(version_push, latest_gate)
        self.assertLess(latest_gate, workflow_end)
        latest_block = self.source[latest_gate:]
        self.assertIn("GH_TOKEN: ${{ github.token }}", latest_block)
        helper = Path(__file__).parents[1] / "scripts/promote_docker_tags.py"
        helper_source = helper.read_text(encoding="utf-8")
        self.assertIn("check_release_order", helper_source)
        self.assertIn("Docker Hub latest tag is newer", helper_source)
        self.assertIn('_docker(["push", f"{REPOSITORY}:latest"]', helper_source)
        self.assertIn("local/ufw-gui:release-candidate", helper_source)

    def test_partial_publish_retry_requires_first_attempt_digest_artifact(self):
        build = self.source.index("name: Build Docker image locally before publishing")
        record = self.source.index(
            "name: Record first-attempt image identity for safe retries"
        )
        upload = self.source.index("name: Upload first-attempt image identity")
        preflight = self.source.index(
            "name: Reconfirm Docker Hub policy and tag availability"
        )
        download = self.source.index(
            "name: Download first-attempt image identity for immutable-tag recovery"
        )
        promote = self.source.index(
            "name: Push or safely resume immutable version tags"
        )
        self.assertLess(build, record)
        self.assertLess(record, upload)
        self.assertLess(upload, preflight)
        self.assertLess(preflight, download)
        self.assertLess(download, promote)
        self.assertIn("github.run_attempt == 1", self.source[record:upload])
        self.assertIn("github.run_attempt > 1", self.source[download:promote])
        self.assertIn("github.token", self.source[download:promote])
        self.assertIn("release-image-identity-${{ github.run_id }}", self.source)
        self.assertIn("RELEASE_IMAGE_IDENTITY_FILE", self.source[promote:])
        helper = Path(__file__).parents[1] / "scripts/promote_docker_tags.py"
        self.assertIn("recorded image digest", helper.read_text(encoding="utf-8"))

    def test_release_validation_workflows_share_sha_cancellation_group(self):
        expected = "group: release-validation-${{ github.sha }}"
        self.assertIn(expected, self.source)
        self.assertIn("cancel-in-progress: true", self.source)
        for filename in ("ci.yml", "ubuntu26-integration.yml"):
            workflow = (WORKFLOW.parent / filename).read_text(encoding="utf-8")
            self.assertIn(expected, workflow)
            self.assertIn("cancel-in-progress: true", workflow)

    def test_ci_runs_on_main_push_to_produce_exact_sha_checks(self):
        ci_source = (WORKFLOW.parents[0] / "ci.yml").read_text(encoding="utf-8")
        self.assertRegex(
            ci_source, r"(?ms)^  push:\n    branches:\n      - main(?:\n|$)"
        )

    def test_integration_check_requires_exact_sha_and_strict_cleanup(self):
        integration = (WORKFLOW.parent / "ubuntu26-integration.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("WORKFLOW_SHA: ${{ github.sha }}", integration)
        self.assertIn('test "$CANDIDATE_SHA" = "$WORKFLOW_SHA"', integration)
        self.assertIn('UFW_GUI_TEST_PASSWORD="$(python3 -c', integration)
        self.assertIn(
            'printf \'%s\' "$UFW_GUI_TEST_PASSWORD" > "$RUNNER_TEMP/ufw-gui-test-password"',
            integration,
        )
        self.assertIn('test_password="$(cat "$test_password_file")"', integration)
        self.assertNotIn('UFW_GUI_TEST_PASSWORD" >> "$GITHUB_ENV"', integration)
        self.assertIn("::add-mask::$UFW_GUI_TEST_PASSWORD", integration)
        self.assertNotIn("temporary-test-password", integration)
        cleanup_start = integration.index(
            "- if: always()", integration.index("Verify legacy recovery evidence")
        )
        cleanup = integration[cleanup_start:]
        password_removal = cleanup.index(
            'rm -f -- "$RUNNER_TEMP/ufw-gui-test-password"'
        )
        docker_inspection = cleanup.index("docker ps -a --format '{{.Names}}'")
        self.assertLess(password_removal, docker_inspection)
        self.assertIn("cleanup_failed=1", cleanup)
        self.assertIn('exit "$cleanup_failed"', cleanup)
        self.assertIn("docker rm -f ufw-gui-ci >/dev/null", cleanup)
        self.assertIn('sudo rm -rf -- "$RUNNER_TEMP/ufw-gui-data"', integration)
        self.assertNotIn("docker rm -f ufw-gui-ci >/dev/null 2>&1 || true", integration)
        self.assertNotIn("statuses: write", integration)
        self.assertNotIn("publish_integration_status", integration)
        self.assertIn("if: ${{ github.ref == 'refs/heads/main' }}", integration)


if __name__ == "__main__":
    unittest.main()
