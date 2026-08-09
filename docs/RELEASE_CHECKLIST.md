# Release checklist

## Before tag

- [ ] `VERSION` matches `APP_VERSION`
- [ ] `CHANGELOG.md` contains the release
- [ ] release notes exist under `docs/RELEASE_NOTES_vX.Y.Z.md`
- [ ] `./scripts/check_release.sh` passes
- [ ] real hardware smoke test completed where relevant
- [ ] no personal logs, profiles, secrets or proprietary assets added
- [ ] CI on `main` is green

## Release

- [ ] create annotated `vX.Y.Z` tag
- [ ] push tag
- [ ] release workflow succeeds
- [ ] Linux ZIP, source TAR.GZ and `SHA256SUMS` are attached
- [ ] release notes are correct

## After release

- [ ] install the published ZIP once on a clean/test user environment if possible
- [ ] verify checksum
- [ ] verify Issues templates and Security policy
- [ ] update roadmap only for genuinely planned work
