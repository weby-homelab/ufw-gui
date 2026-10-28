"""Immutable Docker tag promotion is resumable without overwriting mismatches."""

import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from scripts.promote_docker_tags import (
    DockerTagPromotionError,
    _existing_tags_from_environment,
    _load_expected_image_id,
    promote_latest,
    promote_version_tags,
)

RELEASE_SHA = "d9cace929adf8eb4bd16bf87edfe6789ce10f256"
LOCAL_IMAGE_ID = "sha256:" + "1" * 64
REMOTE_IMAGE_ID = "sha256:" + "2" * 64
OLDER_SHA = "a" * 40


def docker_runner(
    image_data: dict[str, dict[str, str]],
) -> tuple[Callable, list[list[str]]]:
    commands: list[list[str]] = []

    def run(command, *, check, capture_output, text):
        del check, capture_output, text
        args = command[1:]
        commands.append(args)
        if args[:2] == ["image", "inspect"]:
            format_value, reference = args[3], args[4]
            if reference not in image_data:
                return subprocess.CompletedProcess(command, 1, "", "missing image")
            image = image_data[reference]
            if format_value == "{{.Id}}":
                output = image["id"]
            elif "org.opencontainers.image.revision" in format_value:
                output = image["revision"]
            elif "org.opencontainers.image.version" in format_value:
                output = image["version"]
            else:
                raise AssertionError(f"unexpected inspect format: {format_value}")
            return subprocess.CompletedProcess(command, 0, output, "")
        if args[0] in {"pull", "tag", "push"}:
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected Docker command: {args}")

    return run, commands


class DockerTagPromotionTests(unittest.TestCase):
    def test_first_publish_uses_validated_local_build_for_both_tags(self):
        local = {
            f"local/ufw-gui:{RELEASE_SHA}": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            }
        }
        runner, commands = docker_runner(local)

        promote_version_tags("v1.6.3", RELEASE_SHA, (), runner=runner)

        pushes = [command[1] for command in commands if command[0] == "push"]
        self.assertEqual(
            pushes,
            ["webyhomelab/ufw-gui:1.6.3", "webyhomelab/ufw-gui:v1.6.3"],
        )

    def test_partial_publish_resumes_from_existing_matching_release_image(self):
        local = {
            f"local/ufw-gui:{RELEASE_SHA}": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:1.6.3": {
                "id": REMOTE_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
        }
        runner, commands = docker_runner(local)

        promote_version_tags(
            "v1.6.3",
            RELEASE_SHA,
            ("1.6.3",),
            run_attempt=2,
            expected_image_id=REMOTE_IMAGE_ID,
            runner=runner,
        )

        pulls = [command[1] for command in commands if command[0] == "pull"]
        pushes = [command[1] for command in commands if command[0] == "push"]
        tags = [command[1:] for command in commands if command[0] == "tag"]
        self.assertEqual(pulls, ["webyhomelab/ufw-gui:1.6.3"])
        self.assertEqual(pushes, ["webyhomelab/ufw-gui:v1.6.3"])
        self.assertIn(
            ["webyhomelab/ufw-gui:1.6.3", "local/ufw-gui:release-candidate"], tags
        )

    def test_existing_immutable_tag_with_wrong_revision_blocks_all_pushes(self):
        local = {
            f"local/ufw-gui:{RELEASE_SHA}": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:1.6.3": {
                "id": REMOTE_IMAGE_ID,
                "revision": "0" * 40,
                "version": "1.6.3",
            },
        }
        runner, commands = docker_runner(local)

        with self.assertRaisesRegex(DockerTagPromotionError, "revision"):
            promote_version_tags(
                "v1.6.3",
                RELEASE_SHA,
                ("1.6.3",),
                run_attempt=2,
                expected_image_id=REMOTE_IMAGE_ID,
                runner=runner,
            )

        self.assertFalse(any(command[0] == "push" for command in commands))

    def test_existing_release_tags_must_have_matching_image_ids(self):
        local = {
            f"local/ufw-gui:{RELEASE_SHA}": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:1.6.3": {
                "id": REMOTE_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:v1.6.3": {
                "id": "sha256:" + "3" * 64,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
        }
        runner, commands = docker_runner(local)

        with self.assertRaisesRegex(DockerTagPromotionError, "recorded image digest"):
            promote_version_tags(
                "v1.6.3",
                RELEASE_SHA,
                ("1.6.3", "v1.6.3"),
                run_attempt=2,
                expected_image_id=REMOTE_IMAGE_ID,
                runner=runner,
            )

        self.assertFalse(any(command[0] == "push" for command in commands))

    def test_retry_with_both_aliases_at_recorded_digest_is_idempotent(self):
        local = {
            f"local/ufw-gui:{RELEASE_SHA}": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:1.6.3": {
                "id": REMOTE_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:v1.6.3": {
                "id": REMOTE_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
        }
        runner, commands = docker_runner(local)

        promote_version_tags(
            "v1.6.3",
            RELEASE_SHA,
            ("1.6.3", "v1.6.3"),
            run_attempt=2,
            expected_image_id=REMOTE_IMAGE_ID,
            runner=runner,
        )

        self.assertEqual(
            [command[1] for command in commands if command[0] == "pull"],
            ["webyhomelab/ufw-gui:1.6.3", "webyhomelab/ufw-gui:v1.6.3"],
        )
        self.assertFalse(any(command[0] == "push" for command in commands))

    def test_latest_is_not_regressed_when_registry_contains_newer_version(self):
        images = {
            "local/ufw-gui:release-candidate": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:latest": {
                "id": REMOTE_IMAGE_ID,
                "revision": OLDER_SHA,
                "version": "1.10.0",
            },
        }
        runner, commands = docker_runner(images)

        with self.assertRaisesRegex(DockerTagPromotionError, "latest tag is newer"):
            promote_latest(
                "v1.6.3",
                RELEASE_SHA,
                "test-token",
                runner=runner,
                latest_tag_exists=lambda _tag: True,
                order_check=lambda _tag, _token: None,
            )

        self.assertFalse(any(command[0] in {"tag", "push"} for command in commands))

    def test_latest_comparison_handles_oversized_registry_version_labels(self):
        images = {
            "local/ufw-gui:release-candidate": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:latest": {
                "id": REMOTE_IMAGE_ID,
                "revision": OLDER_SHA,
                "version": f"{'9' * 5000}.0.0",
            },
        }
        runner, commands = docker_runner(images)

        with self.assertRaisesRegex(DockerTagPromotionError, "latest tag is newer"):
            promote_latest(
                "v1.6.3",
                RELEASE_SHA,
                "test-token",
                runner=runner,
                latest_tag_exists=lambda _tag: True,
                order_check=lambda _tag, _token: None,
            )

        self.assertFalse(any(command[0] in {"tag", "push"} for command in commands))

    def test_latest_promotion_is_idempotent_for_same_recorded_image(self):
        images = {
            "local/ufw-gui:release-candidate": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:latest": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
        }
        runner, commands = docker_runner(images)

        result = promote_latest(
            "v1.6.3",
            RELEASE_SHA,
            "test-token",
            runner=runner,
            latest_tag_exists=lambda _tag: True,
            order_check=lambda _tag, _token: None,
        )

        self.assertEqual(result, "already-current")
        self.assertFalse(any(command[0] == "push" for command in commands))

    def test_latest_moves_forward_from_older_tag(self):
        images = {
            "local/ufw-gui:release-candidate": {
                "id": LOCAL_IMAGE_ID,
                "revision": RELEASE_SHA,
                "version": "1.6.3",
            },
            "webyhomelab/ufw-gui:latest": {
                "id": REMOTE_IMAGE_ID,
                "revision": OLDER_SHA,
                "version": "1.6.2",
            },
        }
        runner, commands = docker_runner(images)

        result = promote_latest(
            "v1.6.3",
            RELEASE_SHA,
            "test-token",
            runner=runner,
            latest_tag_exists=lambda _tag: True,
            order_check=lambda _tag, _token: None,
        )

        pushes = [command[1] for command in commands if command[0] == "push"]
        self.assertEqual(result, "promoted")
        self.assertEqual(pushes, ["webyhomelab/ufw-gui:latest"])

    def test_invalid_release_identity_fails_before_docker_commands(self):
        runner, commands = docker_runner({})

        with self.assertRaises(DockerTagPromotionError):
            promote_version_tags("v1.6.3-rc.1", RELEASE_SHA, (), runner=runner)

        self.assertEqual(commands, [])

    def test_missing_or_non_boolean_preflight_outputs_fail_closed(self):
        for environment in (
            {"RELEASE_TAG": "v1.6.3", "EXISTING_VERSION_TAG": "false"},
            {
                "RELEASE_TAG": "v1.6.3",
                "EXISTING_VERSION_TAG": "yes",
                "EXISTING_V_VERSION_TAG": "false",
            },
        ):
            with (
                self.subTest(environment=environment),
                self.assertRaisesRegex(DockerTagPromotionError, "preflight outputs"),
            ):
                _existing_tags_from_environment(environment)

    def test_existing_tags_on_first_attempt_or_without_recorded_digest_are_rejected(
        self,
    ):
        runner, commands = docker_runner({})
        with self.assertRaisesRegex(DockerTagPromotionError, "first release attempt"):
            promote_version_tags("v1.6.3", RELEASE_SHA, ("1.6.3",), runner=runner)
        with self.assertRaisesRegex(
            DockerTagPromotionError, "first attempt's verified"
        ):
            promote_version_tags(
                "v1.6.3", RELEASE_SHA, ("1.6.3",), run_attempt=2, runner=runner
            )
        self.assertEqual(commands, [])

    def test_retry_requires_digest_from_immutable_first_attempt_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            identity_file = Path(temp_dir) / "release-image-identity.txt"
            identity_file.write_text(
                f"v1.6.3\n{RELEASE_SHA}\n{REMOTE_IMAGE_ID}\n", encoding="utf-8"
            )

            expected = _load_expected_image_id(identity_file, "v1.6.3", RELEASE_SHA)

            self.assertEqual(expected, REMOTE_IMAGE_ID)

    def test_retry_identity_rejects_wrong_sha_or_malformed_digest(self):
        for content in (
            f"v1.6.3\n{'0' * 40}\n{REMOTE_IMAGE_ID}\n",
            f"v1.6.3\n{RELEASE_SHA}\nsha256:bad\n",
            f"v1.6.3\n{RELEASE_SHA}\n{REMOTE_IMAGE_ID}\nextra\n",
        ):
            with (
                self.subTest(content=content),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                identity_file = Path(temp_dir) / "release-image-identity.txt"
                identity_file.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(DockerTagPromotionError, "identity"):
                    _load_expected_image_id(identity_file, "v1.6.3", RELEASE_SHA)


if __name__ == "__main__":
    unittest.main()
