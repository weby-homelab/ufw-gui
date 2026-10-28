"""Validate immutable Docker Hub policy and inspect version aliases safely."""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.check_versions import (
    PROJECT_ROOT,
    VERSION_PATTERN,
    VersionConsistencyError,
    check_versions,
)

DOCKER_HUB_TAG_URL = (
    "https://hub.docker.com/v2/repositories/webyhomelab/ufw-gui/tags/{}"
)
DOCKER_HUB_REPOSITORY_URL = (
    "https://hub.docker.com/v2/repositories/webyhomelab/ufw-gui/"
)
VERSION_TAGS_PATTERN = r"^v?[0-9]+\.[0-9]+\.[0-9]+$"


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _docker_hub_urlopen(request: Request, timeout: int = 20):
    """Keep registry preflight HTTPS-only and fail closed on redirects."""
    return build_opener(_RejectRedirects()).open(request, timeout=timeout)


class TagAvailabilityError(RuntimeError):
    """Raised when registry policy or tag state is unsafe or unknown."""


def _http_status(url: str, opener=_docker_hub_urlopen) -> int:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=20) as response:
            return response.status
    except HTTPError as exc:
        status = exc.code
        exc.close()
        return status
    except (URLError, TimeoutError, OSError) as exc:
        raise TagAvailabilityError(
            f"Docker Hub tag lookup failed ({type(exc).__name__})"
        ) from None


def _tag_exists(tag: str, opener=_docker_hub_urlopen) -> bool:
    url = DOCKER_HUB_TAG_URL.format(quote(tag, safe="")) + "/"
    status = _http_status(url, opener=opener)
    if status == 404:
        return False
    if 200 <= status < 300:
        return True
    raise TagAvailabilityError(f"Docker Hub tag lookup failed with HTTP {status}")


def _repository_metadata(opener=_docker_hub_urlopen) -> dict:
    request = Request(DOCKER_HUB_REPOSITORY_URL, headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=20) as response:
            if not 200 <= response.status < 300:
                raise TagAvailabilityError(
                    f"Docker Hub repository lookup failed with HTTP {response.status}"
                )
            metadata = json.load(response)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise TagAvailabilityError(
            f"Docker Hub repository lookup failed with HTTP {status}"
        ) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise TagAvailabilityError(
            f"Docker Hub repository lookup failed ({type(exc).__name__})"
        ) from None
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        raise TagAvailabilityError(
            "Docker Hub returned invalid repository metadata"
        ) from None
    if not isinstance(metadata, dict):
        raise TagAvailabilityError("Docker Hub returned invalid repository metadata")
    return metadata


def _validate_immutable_tag_policy(metadata: dict) -> None:
    settings = metadata.get("immutable_tags_settings")
    if not isinstance(settings, dict) or settings.get("enabled") is not True:
        raise TagAvailabilityError("Docker Hub immutable-tag policy is not enabled")
    rules = settings.get("rules")
    if not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules):
        raise TagAvailabilityError(
            "Docker Hub immutable-tag rules are missing or invalid"
        )
    if rules != [VERSION_TAGS_PATTERN]:
        raise TagAvailabilityError(
            "Docker Hub immutable-tag rules must be exactly the canonical stable-version pattern"
        )


def check_tags_available(
    version: str,
    opener=_docker_hub_urlopen,
    *,
    allow_existing: bool = False,
) -> tuple[str, ...]:
    """Check policy and report existing aliases for verified retry recovery."""
    if not VERSION_PATTERN.fullmatch(version):
        raise TagAvailabilityError(
            "only stable MAJOR.MINOR.PATCH versions are supported"
        )

    metadata = _repository_metadata(opener=opener)
    _validate_immutable_tag_policy(metadata)

    existing_tags: list[str] = []
    for tag in (version, f"v{version}"):
        if _tag_exists(tag, opener=opener):
            if not allow_existing:
                raise TagAvailabilityError(
                    f"Docker Hub tag {tag} already exists; refusing overwrite"
                )
            existing_tags.append(tag)
    return tuple(existing_tags)


def _write_github_output(version: str, existing_tags: tuple[str, ...]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        raise TagAvailabilityError(
            "GitHub output file is required for resumable preflight"
        )
    existing = set(existing_tags)
    try:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"version_tag_exists={str(version in existing).lower()}\n")
            output.write(
                f"v_version_tag_exists={str(f'v{version}' in existing).lower()}\n"
            )
    except OSError as exc:
        raise TagAvailabilityError("could not record Docker Hub tag preflight") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="report existing immutable aliases for digest-verified retry recovery",
    )
    args = parser.parse_args(argv)
    try:
        version = check_versions(PROJECT_ROOT)
        existing_tags = check_tags_available(
            version, allow_existing=args.allow_existing
        )
        if args.allow_existing or os.environ.get("GITHUB_OUTPUT"):
            _write_github_output(version, existing_tags)
    except (TagAvailabilityError, VersionConsistencyError) as exc:
        print(f"Docker release preflight failed: {exc}", file=sys.stderr)
        return 1
    print(f"Docker Hub immutable-tag policy is valid for {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
