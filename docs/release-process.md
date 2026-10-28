# Release process

## Docker Hub tag policy

The Docker publish workflow refuses to build unless the `webyhomelab/ufw-gui`
repository reports immutable-tag rules covering both `MAJOR.MINOR.PATCH` and
`vMAJOR.MINOR.PATCH`, while leaving `latest` mutable. Configure Docker Hub under
**Repositories → ufw-gui → Settings → General → Tag mutability settings** with
**Specific tags are immutable** and this Go/RE2-compatible expression:

```text
^v?[0-9]+\.[0-9]+\.[0-9]+$
```

The first workflow attempt requires both target version tags to be absent and
fails closed on registry errors. A rerun may encounter one or both tags from a
partial prior push; it resumes only if the existing image's Docker config digest
matches the first attempt's immutable Actions artifact and the image labels match
the release SHA and version. Missing or mismatched retry evidence blocks
publication. The first-attempt identity artifact is retained for 90 days. This
checks the image config digest, not the registry manifest digest or byte identity
with the Ubuntu integration image. Docker Hub's immutable-tag policy remains the
control against concurrent overwrite; `latest` intentionally remains mutable.

Stable Docker publishes are globally serialized, and the gate compares the
candidate against the highest published stable semver GitHub release. Before
promoting `latest`, the workflow checks release order again and refuses to
replace a registry `latest` image whose version is newer (or whose same-version
digest conflicts). The workflow builds locally without registry credentials,
records the first-attempt config digest, pushes the immutable version tags, then
checks ordering and the current `latest` image before promotion. Do not create or
publish another stable GitHub Release until the current stable Docker publish
workflow finishes.

Before a release, configure repository rulesets so `main` requires reviewed PRs
and cannot be force-pushed or deleted, and tags matching `v*` cannot be updated
or deleted (with no bypass actors). These controls close the interval between
the workflow's final Git-ref check and Docker publication. Do not create the
version tag or GitHub Release until the exact-SHA checks and Ubuntu 26 integration
below have passed. The release workflow loads its credential-bearing gate
verifier, registry preflight, and promotion code from the protected `main` ref,
not from the
detached release checkout; its `GITHUB_TOKEN` is read-only for Actions
runs/checks and repository contents. CI and integration share a SHA-scoped
cancellation group, which also cancels an in-progress publish if fresh evidence
for that SHA is started. Docker publishes additionally use their own global FIFO
queue. Exact-SHA gates and Docker Hub policy are checked again before registry
authentication.

The Dockerfile currently uses moving base-image tags and Debian package indexes.
The integration gate verifies a working Docker/UFW build from the exact source
SHA, but the later publish job rebuilds it; this is not a byte-identical digest
promotion guarantee. Do not claim the published image digest is identical to the
integration runner's image. If artifact identity becomes a release requirement,
publish and promote the exact OCI digest tested by integration instead.

## Release gates

1. Merge the signed release-preparation PR. CI also runs on the resulting `main`
   commit; wait for all five project checks to pass on that exact SHA.
2. Dispatch **Ubuntu 26 Docker and host UFW integration** from `main`, supplying
   the same full SHA. The required `host-ufw` check is attached to that commit;
   its result is successful only if tests and strict runner cleanup complete.
3. Only after both gates pass, create a signed `vMAJOR.MINOR.PATCH` tag at that
   SHA and publish the GitHub Release. The Docker publish workflow checks the
   event's immutable SHA, its tag and
   `main` ancestry, all required CI checks, and the provenance of the successful
   Ubuntu 26 workflow run before registry authentication. It then validates
   Docker Hub immutability and tag availability before image publication.
   The `published` event is the sole Docker publish trigger; a tag push alone
   does not publish.
4. Verify the release workflow and the `MAJOR.MINOR.PATCH`, `vMAJOR.MINOR.PATCH`,
   and mutable `latest` Docker Hub tags.

Automatic firewall rollback remains disabled and is not covered by the
integration workflow.
