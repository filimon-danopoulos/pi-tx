# Codebase Review TODO (pi_tx)

Comprehensive review of `pi_tx/` focusing on Python quality, Kivy/KivyMD practices, architecture, duplication, naming, resiliency, and performance. Items grouped by priority.

## Legend
- [ ] Open
- [x] Done (mark when completed)
- P1 = High impact / correctness or major UX
- P2 = Medium improvement / maintainability
- P3 = Nice to have / polish

---
## P1 – Correctness, Stability, Architecture
- [ ] Centralize exception logging (currently many bare `except Exception` with silent passes) – introduce `log.py` helper. (gui/gui.py, value_store_tab, models_tab, etc.)
- [ ] Replace `print` statements with structured logging (standard `logging` module) and levels (INFO/WARN/ERROR/DEBUG).
- [ ] Add type hints for public methods missing annotations (e.g. many callbacks, `get_actions` returns `list[dict[str, Any]]`).
- [ ] Consolidate repeated model loading logic (`ModelManager`, `ModelRepository`, ad‑hoc in tests) – ensure single source of truth for autoload / save.
- [ ] Guard thread safety around bind process (model SettingsTab) – ensure UI state changes only via Clock; audit potential race (multiple binds).
- [ ] Ensure file path handling uses `Path` consistently instead of mixing `os.path` (model_repo.py uses os, others use Path partially).
- [ ] Validate JSON schema on model load (missing / malformed fields should not crash silently). Add a light schema validator (custom or `pydantic` optional dependency).
- [ ] Add unit tests for `FileCache.save_file` dirty vs immediate behavior (currently only load path obviously used). Confirm final persistence on shutdown (weakref finalizer may not run in abrupt termination).
- [ ] Add graceful error messaging for missing hardware / UART (currently prints only). Surface to UI (snackbar / dialog).
- [ ] Introduce configuration abstraction (currently config path building scattered in value_store, etc.).
- [ ] Audit magic numbers (e.g. scheduling frequencies: 100Hz, 20Hz) – move to constants with rationale.
- [ ] Add bounds checking & validation when manipulating channels and values (some conversions assume `var` naming, failures just pass).

## P1 – UI / KivyMD Specific
- [ ] Refactor global FAB action assembly into a dedicated service or mixin to reduce logic inside `PiTxApp` (SRP).
- [ ] Provide deterministic menu rebuild on tab change (currently only on open; actions could be stale if state changed). Bind to tab switch events.
- [ ] Confirm that ActionMenuItem icon integration works across theme palette changes – may need kv rule to enforce padding / size.
- [ ] Replace manual `pos_hint` FAB positioning with an anchored layout (e.g. container BoxLayout + MDAnchorLayout) for responsive resizing.

## P2 – Performance & Efficiency
- [ ] Avoid repeated JSON disk scans for models (cache model list with invalidation on create/delete). (models_tab/model_repo)
- [ ] ValueStore recomputation: `_recompute()` called on many single updates; consider batching or deferring to next frame via Clock.schedule_once.
- [ ] Channel table rebuild always recreates MDDataTable; diff update strategy could reduce widget churn.
- [ ] Reduce repeated creation of identical dialog objects (cache instance? reuse content) if dialogs are shown frequently.
- [ ] Optimize snapshot comparison in `_poll_store_and_refresh` – currently clones list each time (`snap[:]`). If snapshot is large, use tuple hashing or a version counter.

## P2 – Code Organization
- [ ] Extract dialog classes / builders to dedicated module (already partially done but logic still interspersed in tabs).
- [ ] Move duplicated channel formatting code into utility (channel name, device_display logic appears in multiple areas).
- [ ] Standardize naming: methods like `_refresh_table`, `refresh_table`, `_refresh_content` – converge on a consistent prefix (internal vs public).
- [ ] Consolidate action icon naming scheme (currently mix of `plus`, `plus-box`, `delete`, `delete-forever`). Decide on filled vs outline pattern.
- [ ] Introduce dataclass or small object for menu actions instead of loose dict to avoid key typos.
- [ ] Provide a base TabActionProvider mixin to enforce `get_actions()` signature and maybe enable/disable logic.

## P2 – Testing Gaps
- [ ] Add tests for value reversing logic (bipolar vs unipolar) – edge cases at boundaries (0, 1, -1).
- [ ] Test `FileCache` dirty write path (immediate=False) – ensure flush on finalize (simulate finalize or expose explicit flush method).
- [ ] Add tests for model bind timestamp persistence (SettingsTab) – ensure saving and display formatting.
- [ ] Test autoload last model path (simulate file absence, corrupt json, permissions errors).
- [ ] Add tests for action aggregation uniqueness and presence across all tabs.

## P2 – Developer Experience
- [ ] Add CONTRIBUTING.md with style guide (type hints, logging, error handling conventions, commit style).
- [ ] Enforce formatting (black/ruff or ruff only) and static type checking (mypy) in CI.
- [ ] Provide Makefile or task script for common flows (test, lint, run, package).
- [ ] Add pre-commit hooks (ruff, mypy, pytest minimal subset).

## P3 – UX / Polish
- [ ] Animate FAB show/hide on scroll or tab changes (subtle scale/opacity).
- [ ] Add keyboard shortcuts to global actions (and show in labels, e.g., `Values: Add (A)`).
- [ ] Provide tooltips on FAB & action menu entries.
- [ ] Persist last selected tab and reopen on restart.
- [ ] Provide dark/light theme toggle in General tab (store in config).
- [ ] Add snackbar confirmations for destructive actions (remove model/value) instead of only prints.
- [ ] Replace raw prints in dialogs with user-facing feedback components.

## P3 – Documentation
- [ ] Expand README with architecture diagram (domain vs gui vs infrastructure).
- [ ] Document file cache lifecycle & expected usage patterns (when to call save_file vs relying on auto-save).
- [ ] Add docstrings to all public classes (ChannelPanel, InputEventPump, etc.) – many are missing or minimal.
- [ ] Provide sample model JSON schemas with explanations in docs/models.md.

## Security / Robustness
- [ ] Sanitize model names on save (prevent path traversal or invalid filesystem characters).
- [ ] Handle concurrent writes (if future multi-process) – maybe advisory file lock (fcntl on posix) in FileCache save.
- [ ] Consider fallback / recovery for partially written JSON (write temp file then atomic rename).
- [ ] Validate numeric ranges (channels expected 0–15 / 1–N) centrally to avoid scattered implicit assumptions.

## Observed Repetition / Candidates for DRY
- Channel row formatting logic (device_display resolution) duplicated across model & live contexts.
- Rebuilding tables shares patterns (clear, recompute, replace) – unify with helper.
- Many `if hasattr(obj, 'method')` checks – could use defined interfaces / abstract base classes.
- Pattern of scheduling initial refresh with `Clock.schedule_once(lambda *_: ...)` repeated; wrap in helper `run_next_frame(fn, *args)`.

## Kivy/KivyMD Specific Recommendations
- [ ] Move custom widget classes (e.g., ActionMenuItem) into a widgets module + kv definition to centralize styling.
- [ ] Consider using `.kv` language for static layout instead of Python-only composition for large UI blocks (improves readability & separation).
- [ ] Avoid large synchronous file IO inside UI callbacks; offload heavy operations to threads with safe UI updates via Clock.
- [ ] Use theming variables (self.theme_cls) instead of hard-coded RGBA tuples for consistent palette changes.
- [ ] Prefer `MDIconButton` inside lists where only an icon is needed; current ActionMenuItem could optionally support right-side icon actions (edit/delete) if expanded.

## Performance Micro-Optimizations (Low Priority)
- [ ] Replace repeated string splits in channel path parsing with cached results.
- [ ] Precompile any frequent regex (if added later) at module load.
- [ ] Use tuple for immutable constant lists (e.g., _column_widths can remain tuple).

## Cleanup / Dead Code
- [ ] Remove commented or placeholder prints after adding logging.
- [ ] Eliminate leftover placeholder no-op methods for removed FAB logic if no longer needed.

## Proposed Refactors (Epic Level)
- [ ] Introduce domain events or signal bus (model_selected, values_changed) instead of polling & manual snapshot diff.
- [ ] Introduce ViewModel layer to decouple UI widgets from domain stores, enabling headless tests.
- [ ] Migrate configuration & persistence to a unified service (models, system values, stick mapping).
- [ ] Consider plugin system for processors (dynamic discovery of channel processors).

## Immediate Low-Risk Wins (Good First Issues)
- [ ] Add logging setup module and replace prints in 5–10 key files.
- [ ] Add type hints to action provider `get_actions` methods.
- [ ] Create utility for `var` parsing (shared by reverse & value loading functions).
- [ ] Add constant definitions for schedule rates (INPUT_PUMP_HZ, UI_REFRESH_HZ).
- [ ] Add icons consistently (decide style set) & centralize in `icons.py` mapping for maintainability.

---
## Suggested Folder Additions
- `pi_tx/logging/` (logger config)
- `pi_tx/gui/widgets/` (custom KivyMD widgets + kv)
- `docs/architecture.md`

---
## Tracking
Update this file as items are completed; group related tasks into PRs to keep changes reviewable.
