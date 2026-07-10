# CI vendor directory

Standalone GitHub Actions for this public repo cannot read the private
`RazorBackRoar/razorcore` repository. CI installs razorcore from the pinned
wheel in this directory via `UV_FIND_LINKS`.

Local development still uses the editable sibling at `../.razorcore`.

When bumping the `razorcore>=…` requirement in `pyproject.toml`, rebuild and
refresh the wheel:

```bash
cd ../.razorcore
uv build
cp dist/razorcore-<version>-py3-none-any.whl ../Nexus/ci/vendor/
```
