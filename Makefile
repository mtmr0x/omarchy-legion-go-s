.PHONY: release

# Tag a new version and publish it as a GitHub release. Interactive.
release:
	@scripts/release.sh
