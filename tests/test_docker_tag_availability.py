"""Release tag availability checks fail closed on registry errors."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from scripts.check_docker_tags import (
    VERSION_TAGS_PATTERN,
    TagAvailabilityError,
    _write_github_output,
    check_tags_available,
)


def http_error(url: str, status: int) -> HTTPError:
    return HTTPError(url, status, "test response", hdrs=None, fp=None)


class Response:
    status = 200

    def __init__(self, payload=None):
        if payload is None:
            payload = {
                "immutable_tags_settings": {
                    "enabled": True,
                    "rules": [VERSION_TAGS_PATTERN],
                }
            }
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, *_args):
        return self.body


class DockerTagAvailabilityTests(unittest.TestCase):
    def test_missing_version_tags_allow_first_publish(self):
        opener = Mock(
            side_effect=[
                Response(),
                http_error("https://hub.docker.com/", 404),
                http_error("https://hub.docker.com/", 404),
            ]
        )

        check_tags_available("1.6.3", opener=opener)

        requested_urls = [call.args[0].full_url for call in opener.call_args_list]
        self.assertEqual(
            requested_urls,
            [
                "https://hub.docker.com/v2/repositories/webyhomelab/ufw-gui/",
                "https://hub.docker.com/v2/repositories/webyhomelab/ufw-gui/tags/1.6.3/",
                "https://hub.docker.com/v2/repositories/webyhomelab/ufw-gui/tags/v1.6.3/",
            ],
        )

    def test_existing_version_tag_blocks_overwrite(self):
        opener = Mock(side_effect=[Response(), Response()])

        with self.assertRaisesRegex(TagAvailabilityError, "already exists"):
            check_tags_available("1.6.3", opener=opener)

        self.assertEqual(opener.call_count, 2)

    def test_existing_v_prefixed_version_tag_blocks_overwrite(self):
        opener = Mock(
            side_effect=[
                Response(),
                http_error("https://hub.docker.com/", 404),
                Response(),
            ]
        )

        with self.assertRaisesRegex(TagAvailabilityError, "tag v1.6.3 already exists"):
            check_tags_available("1.6.3", opener=opener)

        self.assertEqual(opener.call_count, 3)

    def test_existing_tags_are_reported_for_digest_verified_resume(self):
        opener = Mock(
            side_effect=[
                Response(),
                Response(),
                http_error("https://hub.docker.com/", 404),
            ]
        )

        existing = check_tags_available("1.6.3", opener=opener, allow_existing=True)

        self.assertEqual(existing, ("1.6.3",))
        self.assertEqual(opener.call_count, 3)

    def test_existing_tags_still_block_non_resumable_preflight(self):
        opener = Mock(side_effect=[Response(), Response()])

        with self.assertRaisesRegex(TagAvailabilityError, "already exists"):
            check_tags_available("1.6.3", opener=opener)

    def test_github_outputs_report_each_existing_immutable_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "github-output"
            output_path.touch()

            with unittest.mock.patch.dict(
                "os.environ", {"GITHUB_OUTPUT": str(output_path)}
            ):
                _write_github_output("1.6.3", ("1.6.3",))

            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "version_tag_exists=true\nv_version_tag_exists=false\n",
            )

    def test_registry_errors_block_publishing(self):
        for failure in (
            http_error("https://hub.docker.com/", 404),
            http_error("https://hub.docker.com/", 429),
            http_error("https://hub.docker.com/", 500),
            URLError("temporary network failure"),
        ):
            with (
                self.subTest(failure=type(failure).__name__),
                self.assertRaises(TagAvailabilityError),
            ):
                check_tags_available("1.6.3", opener=Mock(side_effect=failure))

    def test_redirect_responses_fail_closed(self):
        redirect = HTTPError(
            "https://hub.docker.com/",
            302,
            "redirect",
            hdrs={"Location": "http://attacker.example/collect"},
            fp=None,
        )

        with self.assertRaisesRegex(TagAvailabilityError, "HTTP 302"):
            check_tags_available("1.6.3", opener=Mock(side_effect=redirect))

    def test_tag_lookup_error_blocks_publishing(self):
        opener = Mock(
            side_effect=[Response(), http_error("https://hub.docker.com/", 429)]
        )

        with self.assertRaisesRegex(TagAvailabilityError, "HTTP 429"):
            check_tags_available("1.6.3", opener=opener)

    def test_disabled_immutability_blocks_publishing(self):
        opener = Mock(
            return_value=Response(
                {"immutable_tags_settings": {"enabled": False, "rules": [".*"]}}
            )
        )

        with self.assertRaisesRegex(TagAvailabilityError, "not enabled"):
            check_tags_available("1.6.3", opener=opener)

        opener.assert_called_once()

    def test_immutability_must_cover_both_version_tags(self):
        opener = Mock(
            return_value=Response(
                {"immutable_tags_settings": {"enabled": True, "rules": [r"^1\.6\.3$"]}}
            )
        )

        with self.assertRaisesRegex(TagAvailabilityError, "exactly the canonical"):
            check_tags_available("1.6.3", opener=opener)

        opener.assert_called_once()

    def test_policy_must_cover_all_stable_versions_not_only_current_release(self):
        opener = Mock(
            return_value=Response(
                {
                    "immutable_tags_settings": {
                        "enabled": True,
                        "rules": [r"^1\.6\.3$|^v1\.6\.3$"],
                    }
                }
            )
        )

        with self.assertRaisesRegex(TagAvailabilityError, "canonical stable-version"):
            check_tags_available("1.6.3", opener=opener)

        opener.assert_called_once()

    def test_no_additional_regex_can_make_latest_immutable(self):
        opener = Mock(
            return_value=Response(
                {
                    "immutable_tags_settings": {
                        "enabled": True,
                        "rules": [VERSION_TAGS_PATTERN, "^[[:alpha:]]+$"],
                    }
                }
            )
        )

        with self.assertRaisesRegex(TagAvailabilityError, "exactly the canonical"):
            check_tags_available("1.6.3", opener=opener)

        opener.assert_called_once()

    def test_invalid_version_is_rejected_before_network_access(self):
        opener = Mock()

        with self.assertRaises(TagAvailabilityError):
            check_tags_available("1.6.3-rc.1", opener=opener)

        opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
