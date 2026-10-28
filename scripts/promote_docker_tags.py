"""Resume immutable Docker Hub aliases only from an exact-release image."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
VERSION_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
IMAGE_ID_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
REPOSITORY = "webyhomelab/ufw-gui"
LOCAL_CANDIDATE = "local/ufw-gui:release-candidate"
REVISION_LABEL = "org.opencontainers.image.revision"
VERSION_LABEL = "org.opencontainers.image.version"


def _numeric_version_order(version: str) -> tuple[tuple[int, str], ...]:
    """Compare arbitrarily long canonical numeric components without int conversion."""
    return tuple((len(part), part) for part in version.split("."))


class DockerTagPromotionError(RuntimeError):
    """Raised when an immutable image alias cannot be safely resumed."""


def _load_expected_image_id(
    identity_file: str | Path, release_tag: str, release_sha: str
) -> str:
    try:
        fields = Path(identity_file).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise DockerTagPromotionError(
            "release image identity artifact is unavailable"
        ) from None
    if (
        len(fields) != 3
        or fields[0] != release_tag
        or fields[1] != release_sha
        or not IMAGE_ID_PATTERN.fullmatch(fields[2])
    ):
        raise DockerTagPromotionError("release image identity artifact is invalid")
    return fields[2]


def _docker(args: Sequence[str], runner: Callable = subprocess.run) -> str:
    try:
        result = runner(["docker", *args], check=False, capture_output=True, text=True)
    except OSError as exc:
        raise DockerTagPromotionError(
            f"Docker command could not run ({type(exc).__name__})"
        ) from None
    if result.returncode != 0:
        operation = args[0] if args else "command"
        raise DockerTagPromotionError(f"Docker {operation} failed")
    return result.stdout.strip()


def _inspect(reference: str, format_string: str, runner: Callable) -> str:
    return _docker(["image", "inspect", "--format", format_string, reference], runner)


def _verify_release_image(
    reference: str, release_sha: str, version: str, runner: Callable
) -> str:
    image_id = _inspect(reference, "{{.Id}}", runner)
    revision = _inspect(
        reference,
        f'{{{{ index .Config.Labels "{REVISION_LABEL}" }}}}',
        runner,
    )
    image_version = _inspect(
        reference,
        f'{{{{ index .Config.Labels "{VERSION_LABEL}" }}}}',
        runner,
    )
    if not IMAGE_ID_PATTERN.fullmatch(image_id):
        raise DockerTagPromotionError("Docker image returned an invalid config digest")
    if revision != release_sha:
        raise DockerTagPromotionError(
            f"Docker image {reference} has the wrong source revision label"
        )
    if image_version != version:
        raise DockerTagPromotionError(
            f"Docker image {reference} has the wrong version label"
        )
    return image_id


def promote_version_tags(
    release_tag: str,
    release_sha: str,
    existing_tags: Sequence[str],
    *,
    run_attempt: int = 1,
    expected_image_id: str | None = None,
    runner: Callable = subprocess.run,
) -> str:
    """Push only missing aliases; verify existing aliases by image config digest."""
    if not SHA_PATTERN.fullmatch(release_sha):
        raise DockerTagPromotionError("release SHA must be a full lowercase commit SHA")
    if not release_tag.startswith("v"):
        raise DockerTagPromotionError("release tag must use vMAJOR.MINOR.PATCH")
    version = release_tag[1:]
    if not VERSION_PATTERN.fullmatch(version):
        raise DockerTagPromotionError("release tag must use vMAJOR.MINOR.PATCH")
    if (
        not isinstance(run_attempt, int)
        or isinstance(run_attempt, bool)
        or run_attempt < 1
    ):
        raise DockerTagPromotionError("release run attempt must be a positive integer")

    allowed_tags = (version, release_tag)
    if len(set(existing_tags)) != len(existing_tags) or any(
        tag not in allowed_tags for tag in existing_tags
    ):
        raise DockerTagPromotionError("Docker Hub preflight returned invalid tag state")
    existing = set(existing_tags)
    if existing and run_attempt == 1:
        raise DockerTagPromotionError(
            "first release attempt cannot resume pre-existing immutable tags"
        )
    if existing and (
        expected_image_id is None or not IMAGE_ID_PATTERN.fullmatch(expected_image_id)
    ):
        raise DockerTagPromotionError(
            "retry requires the first attempt's verified image digest"
        )

    local_image = f"local/ufw-gui:{release_sha}"
    candidate_image_id = _verify_release_image(
        local_image, release_sha, version, runner
    )
    canonical_image = local_image
    canonical_image_id = candidate_image_id
    existing_image_found = False

    for tag in allowed_tags:
        if tag not in existing:
            continue
        reference = f"{REPOSITORY}:{tag}"
        _docker(["pull", reference], runner)
        image_id = _verify_release_image(reference, release_sha, version, runner)
        if image_id != expected_image_id:
            raise DockerTagPromotionError(
                "existing immutable release tag does not match the recorded image digest"
            )
        if not existing_image_found:
            canonical_image = reference
            canonical_image_id = image_id
            existing_image_found = True

    _docker(["tag", canonical_image, LOCAL_CANDIDATE], runner)
    for tag in allowed_tags:
        if tag in existing:
            continue
        reference = f"{REPOSITORY}:{tag}"
        _docker(["tag", LOCAL_CANDIDATE, reference], runner)
        _docker(["push", reference], runner)

    return canonical_image_id


def _existing_tags_from_environment(environment: Mapping[str, str]) -> tuple[str, ...]:
    values = (
        environment.get("EXISTING_VERSION_TAG"),
        environment.get("EXISTING_V_VERSION_TAG"),
    )
    if any(value not in {"true", "false"} for value in values):
        raise DockerTagPromotionError(
            "Docker Hub preflight outputs are missing or invalid"
        )
    release_tag = environment.get("RELEASE_TAG", "")
    version = release_tag.removeprefix("v")
    tags = []
    if values[0] == "true":
        tags.append(version)
    if values[1] == "true":
        tags.append(f"v{version}")
    return tuple(tags)


def promote_latest(
    release_tag: str,
    release_sha: str,
    token: str,
    *,
    runner: Callable = subprocess.run,
    latest_tag_exists: Callable[[str], bool] | None = None,
    order_check: Callable[[str, str], None] | None = None,
) -> str:
    """Promote latest only when neither release history nor registry is newer."""
    if not token:
        raise DockerTagPromotionError("GitHub token is required for latest promotion")
    if not release_tag.startswith("v") or not VERSION_PATTERN.fullmatch(
        release_tag[1:]
    ):
        raise DockerTagPromotionError("release tag must use vMAJOR.MINOR.PATCH")
    version = release_tag[1:]
    if not SHA_PATTERN.fullmatch(release_sha):
        raise DockerTagPromotionError("release SHA must be a full lowercase commit SHA")

    if order_check is None:
        from scripts.check_release_gates import check_release_order

        order_check = check_release_order
    try:
        order_check(release_tag, token)
    except RuntimeError:
        raise DockerTagPromotionError(
            "release-order gate rejected latest promotion"
        ) from None

    if latest_tag_exists is None:
        from scripts.check_docker_tags import _tag_exists

        latest_tag_exists = _tag_exists
    try:
        existing_latest = latest_tag_exists("latest")
    except RuntimeError:
        raise DockerTagPromotionError(
            "Docker Hub latest-tag status could not be verified"
        ) from None

    candidate = "local/ufw-gui:release-candidate"
    candidate_id = _verify_release_image(candidate, release_sha, version, runner)
    if existing_latest:
        latest = f"{REPOSITORY}:latest"
        _docker(["pull", latest], runner)
        latest_id = _inspect(latest, "{{.Id}}", runner)
        latest_revision = _inspect(
            latest,
            f'{{{{ index .Config.Labels "{REVISION_LABEL}" }}}}',
            runner,
        )
        latest_version = _inspect(
            latest,
            f'{{{{ index .Config.Labels "{VERSION_LABEL}" }}}}',
            runner,
        )
        if (
            not IMAGE_ID_PATTERN.fullmatch(latest_id)
            or not SHA_PATTERN.fullmatch(latest_revision)
            or not VERSION_PATTERN.fullmatch(latest_version)
        ):
            raise DockerTagPromotionError(
                "Docker Hub latest image has invalid release identity metadata"
            )
        current_version = _numeric_version_order(latest_version)
        candidate_version = _numeric_version_order(version)
        if current_version > candidate_version:
            raise DockerTagPromotionError(
                "Docker Hub latest tag is newer than this release"
            )
        if current_version == candidate_version:
            if latest_id != candidate_id or latest_revision != release_sha:
                raise DockerTagPromotionError(
                    "Docker Hub latest tag has a conflicting image for this version"
                )
            return "already-current"

    _docker(["tag", candidate, f"{REPOSITORY}:latest"], runner)
    _docker(["push", f"{REPOSITORY}:latest"], runner)
    return "promoted"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--latest", action="store_true", help="safely promote the mutable latest alias"
    )
    args = parser.parse_args(argv)
    try:
        release_tag = os.environ.get("RELEASE_TAG", "")
        release_sha = os.environ.get("RELEASE_SHA", "")
        if args.latest:
            result = promote_latest(
                release_tag, release_sha, os.environ.get("GH_TOKEN", "")
            )
            print(f"Docker Hub latest alias status: {result}")
            return 0
        attempt_text = os.environ.get("RELEASE_RUN_ATTEMPT", "")
        if not attempt_text.isdecimal():
            raise DockerTagPromotionError("release run attempt is missing or invalid")
        run_attempt = int(attempt_text)
        existing_tags = _existing_tags_from_environment(os.environ)
        expected_image_id = None
        if existing_tags:
            identity_file = os.environ.get("RELEASE_IMAGE_IDENTITY_FILE", "")
            if not identity_file:
                raise DockerTagPromotionError(
                    "release image identity artifact is unavailable"
                )
            expected_image_id = _load_expected_image_id(
                identity_file, release_tag, release_sha
            )
        promote_version_tags(
            release_tag,
            release_sha,
            existing_tags,
            run_attempt=run_attempt,
            expected_image_id=expected_image_id,
        )
    except DockerTagPromotionError as exc:
        print(f"Docker tag promotion failed: {exc}", file=sys.stderr)
        return 1
    print(f"Docker Hub version aliases are consistent for {release_tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
