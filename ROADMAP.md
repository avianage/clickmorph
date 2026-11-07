# Right-Click Converter — Roadmap

> iLovePDF-level tools, 7-Zip-style: right-click → convert → done. Offline, open source (GPL-3.0), fast on low-end PCs.

**Core principles**

- Zero dialogs by default — result appears next to the original + a toast
- Context-aware menu — only show actions that fit the current selection
- Never overwrite originals; collision-safe output names
- Nothing heavy stays in memory; engines downloaded only when first needed
- Never breaks — out-of-process worker, built-in `repair`

---

## Phase 0 — Foundation

- [x] Pick the final name; check GitHub, PyPI, winget and domain availability
- [x] Create GitHub repo with GPL-3.0 license
- [x] Add README (pitch, planned features, screenshot placeholder)
- [ ] Install CLA Assistant so you stay sole copyright holder
- [x] Set up Python 3.12 + `uv`
- [x] Add `ruff`, `pytest`, `pre-commit`
- [ ] GitHub Actions CI on `windows-latest` + `ubuntu-latest`
- [x] Create folder layout: `core/`, `cli/`, `shell/`, `native/`, `installer/`, `tests/`
- [x] Add CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue/PR templates
- [ ] Set up GitHub Sponsors / Buy Me a Coffee link

## Phase 1 — Core engine + CLI

### Architecture

- [ ] Design the **operation registry** (inputs accepted, single vs multi-file, default options, output naming, heavy/light flag for future remote engine)
- [ ] Output naming helper (`file-compressed.pdf`, `file (1).pdf` on collision)
- [ ] Job log (inputs → outputs) to enable undo later
- [ ] Natural sort for multi-file ordering (`page2` before `page10`)

### PDF operations (pikepdf, pypdfium2)

- [ ] Merge selected PDFs
- [ ] Split — every page / by range
- [ ] Compress — low / medium / high
- [ ] Rotate 90° / 180° / 270°
- [ ] Images → single PDF
- [ ] PDF → PNG / JPG (per page)
- [ ] Lock (add password) / unlock
- [ ] Extract / delete / reorder pages

### Image operations (Pillow, pillow-heif)

- [ ] Convert between JPG, PNG, WebP, AVIF, HEIC, BMP, TIFF, ICO
- [ ] Resize presets (50%, 1080p, 720p, custom)
- [ ] Strip metadata (EXIF / GPS)

### Headline feature

- [ ] **Fit-to-size** — binary search on quality + scale to hit target (100 KB / 200 KB / 500 KB / 1 MB / 2 MB) for images
- [ ] Fit-to-size for PDFs (recompress embedded images)

### CLI (Typer)

- [ ] `<cli> pdf merge|split|compress|rotate|lock|unlock`
- [ ] `<cli> img convert|resize`
- [ ] `<cli> fit 200kb <files>`
- [ ] `--output`, `--overwrite-never` default, `--quiet`, progress bar

### Tests

- [ ] Sample fixture files (PDFs, scanned PDF, HEIC, large JPGs)
- [ ] Unit test per operation
- [ ] Fit-to-size accuracy tests (output always ≤ target)

## Phase 2 — Windows right-click (classic menu) → **v0.1**

- [ ] Single-instance daemon with named pipe; ~300 ms batching window
- [ ] Daemon auto-exits after idle (low RAM use)
- [ ] Run jobs at low priority, limited parallelism
- [ ] HKCU registry writer (no admin needed)
- [ ] Cascading "Convert ▸" submenus per file type via `ExtendedSubCommandsKey`
- [ ] Multi-select handling (`MultiSelectModel=Player`) — test with 1, 15, 16, 100, 500 files
- [ ] Toast notifications: done / failed / "Open folder"
- [ ] `install`, `uninstall`, `repair` commands
- [ ] Package with Nuitka or PyInstaller
- [ ] Inno Setup installer
- [ ] Test on Windows 10 and Windows 11 (Shift+right-click / Show more options)
- [ ] Tag **v0.1** release

## Phase 3 — More engines → **v0.2**

- [ ] On-demand engine downloader (with checksum verification)
- [ ] Office → PDF via MS Office COM when installed
- [ ] Office → PDF via LibreOffice headless fallback (DOCX, XLSX, PPTX, ODT)
- [ ] FFmpeg presets: MP4→MP3, compress video, video→GIF, audio convert
- [ ] Hardware encoding detection (Quick Sync / AMF / NVENC)
- [ ] Progress + cancel for long jobs
- [ ] "Undo last conversion"
- [ ] Tag **v0.2** release

## Phase 4 — Native Windows 11 menu → **v0.3**

- [ ] Rust DLL (`windows-rs`) implementing `IExplorerCommand`
- [ ] Dynamic menu: `GetState` + `EnumSubCommands` based on selection
- [ ] DLL forwards `IShellItemArray` paths to daemon over named pipe
- [ ] AppxManifest with `windows.fileExplorerContextMenus`
- [ ] Sparse MSIX package (`makeappx`)
- [ ] Self-signed cert for development
- [ ] Azure Trusted Signing for releases
- [ ] Installer registers sparse package; keeps registry fallback for Win10
- [ ] Test on new Oct 2026 Win11 menu; pin under Settings → Context menu → App extensions
- [ ] Tag **v0.3** release

## Phase 5 — Launch

- [ ] Demo GIF in README (right-click → result in 2 s)
- [ ] GitHub Releases with signed installer
- [ ] winget manifest
- [ ] Scoop manifest
- [ ] Docs page (GitHub Pages)
- [ ] List on AlternativeTo (as alternative to PDF24, File Converter, iLovePDF)
- [ ] Post on r/windows, r/opensource, r/software, Hacker News (Show HN)

## Phase 6 — Power features

- [ ] Recipes — user-defined chained operations (e.g. photos → PDF → fit 2 MB)
- [ ] OCR for scanned PDFs (Tesseract)
- [ ] Small settings UI (defaults, output folder, menu items on/off)
- [ ] Optional remote engine — send heavy jobs (Office, video) to your own server
- [ ] macOS Quick Actions
- [ ] Linux Nautilus / Dolphin integration
- [ ] Paid Microsoft Store build (optional)
