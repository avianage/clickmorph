# native

Placeholder for the Windows 11 modern context-menu handler (Roadmap Phase 4).

This will be a Rust DLL built with `windows-rs` that implements `IExplorerCommand`,
builds the menu dynamically from the current selection, and forwards the selected paths
to the ClickMorph daemon over a named pipe. It ships inside a sparse MSIX package.

Nothing is built from this folder yet.
