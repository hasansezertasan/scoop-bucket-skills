# Manifest scaffolding

How the `scoop-add` scaffolder turns a GitHub release into a Scoop manifest for a bucket.

## Language

**Token**:
The manifest's name: the lowercase, hyphen-separated filename stem of `bucket/<token>.json`.
_Avoid_: Version token, manifest id

**Tag prefix**:
The text of a release tag before its first digit, such as `release-` in `release-1.2.3` or `release/v` in `release/v1.0.0`.
_Avoid_: Tag stem

**Version**:
The text of a release tag from its first digit onward, stored in the manifest's `version` field.
_Avoid_: Tag (when only the numeric part is meant)

**Version slot**:
A place in an autoupdate URL, `extract_dir` or `bin` where the literal version is replaced by `$version`.
_Avoid_: Version token, version placeholder

**Architecture class**:
One of `64bit`, `32bit` or `arm64`: the kind of machine a release asset targets, taken from the asset's name.
_Avoid_: Platform
