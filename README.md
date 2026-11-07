# ClickMorph

> iLovePDF-style file tools, right in the Windows Explorer menu. Right-click → pick an
> action → done.

**Status: work in progress.** Nothing here is ready for everyday use yet. Follow
[ROADMAP.md](ROADMAP.md) to see what's being built and in what order.

<!-- Screenshot / demo GIF goes here once the context menu works. -->

## Why

Merging two PDFs or shrinking a photo to fit an upload limit shouldn't mean uploading
your files to a website or opening a heavy app. ClickMorph adds those tools to the
Explorer right-click menu, the way 7-Zip does for archives:

- **No dialogs by default.** The result appears next to the original, and a toast tells
  you it's done.
- **Only relevant actions.** The menu shows what fits the files you selected.
- **Your originals are never touched.** Outputs get safe names like
  `report-compressed.pdf` or `report-compressed (1).pdf`.
- **Offline and private.** Everything runs on your PC.
- **Light.** Nothing heavy runs in the background, and optional engines are downloaded
  only when you first need them.
- **Free and open source** under GPL-3.0.

## Planned features

**PDF**
- Merge, split (every page or by range), extract, delete and reorder pages
- Compress (low / medium / high)
- Rotate 90° / 180° / 270°
- Images → single PDF, PDF → PNG / JPG
- Lock with a password / unlock

**Images**
- Convert between JPG, PNG, WebP, AVIF, HEIC, BMP, TIFF and ICO
- Resize presets (50%, 1080p, 720p, custom)
- Strip metadata (EXIF / GPS)

**Fit to size:** shrink an image or PDF to 100 KB, 200 KB, 500 KB, 1 MB or 2 MB, for
upload forms with strict limits.

**Later:** Office → PDF, audio and video presets, undo, a native Windows 11 menu,
chained "recipes", and OCR for scanned PDFs.

## Command line

Every action will also be available from the `cm` command (planned syntax):

```console
cm pdf merge a.pdf b.pdf
cm img convert photo.heic --to jpg
cm fit 200kb scan.jpg
```

## Development

Requires [uv](https://docs.astral.sh/uv/).

```console
uv sync
uv run cm --version
uv run ruff check
uv run ruff format --check
uv run pytest
uv run pre-commit install
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

[GPL-3.0](LICENSE)
