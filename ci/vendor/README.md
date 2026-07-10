# CI vendor directory

Standalone GitHub Actions for this public repo cannot read the private
`RazorBackRoar/razorcore` repository. CI installs razorcore from the pinned
wheel in this directory via `UV_FIND_LINKS`.

Local development still uses the editable sibling at `../.razorcore`.

## Automatic refresh

From the Apps workspace root, after saving or bumping `.razorcore`:

```bash
razorvendor
```

`save .razorcore` and razorcore version bumps run this automatically when
they change the library.

## Manual refresh

```bash
cd ../.razorcore
uv build
razorvendor
```
