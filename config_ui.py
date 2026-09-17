import os
import sys
import json
import base64
from pathlib import Path
from nicegui import ui, app

current_dir = os.path.dirname(os.path.abspath(__file__))
model_utils = os.path.abspath(os.path.join(current_dir, "model_utils"))
if model_utils not in sys.path:
    sys.path.insert(0, model_utils)

from model_utils.env_config import EnvironmentConfig

DEFAULT_ICON = "icon.png"

def get_crest_base64() -> str:
    candidates = [
        Path("icon.png"),
        Path(__file__).resolve().parent / "icon.png",
        Path("Mia"),
        Path(__file__).resolve().parent / "Mia",
        Path("bg_removal__00008.jpg"),
        Path(__file__).resolve().parent / "bg_removal__00008.jpg",
    ]
    for p in candidates:
        if p.is_file():
            try:
                raw = p.read_bytes()
                # Check magic bytes to set exact mime type
                mime = "image/png" if raw.startswith(b"\x89PNG") else "image/jpeg"
                return f"data:{mime};base64,{base64.b64encode(raw).decode('utf-8')}"
            except Exception:
                continue
    return ""

def get_icon_source(icon_name: str = DEFAULT_ICON) -> str:
  # Check current directory and project root
  for path in [
      Path(icon_name),
      Path(__file__).resolve().parent / icon_name,
      Path("Mia"),
      Path("bg_removal__00008.jpg"),
  ]:
    if path.is_file():
      encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
      return f"data:image/png;base64,{encoded}"
  return ""


# Default Base Paths
DEFAULT_CACHE_DIR = str(Path("~/.cache/AmNanotech/nanovault_downloads").expanduser().resolve())
DEFAULT_NANOVAULT_DIR = str(
    Path("~/.sovereign-ai/NanoVault").expanduser().resolve()
    if Path("~/.sovereign-ai/NanoVault").expanduser().exists()
    else Path.cwd().resolve()
)

# Theme Palette
COLOR_BG = "#0a0d12"
COLOR_CARD = "#111823"
COLOR_BORDER = "#1e293b"
COLOR_CYAN = "#00e5ff"
COLOR_MUTED = "#64748b"

def detect_comfyui_path() -> str:
  """Check for standard sibling installation '../ComfyUI' first,

  falling back to common paths if not found.
  """
  # 1. Primary check: Standard sibling directory
  sibling_target = (Path.cwd() / ".." / "ComfyUI").resolve()
  if sibling_target.is_dir() and (sibling_target / "models").is_dir():
    return str(sibling_target)

  # 2. Case-insensitive fallback for the sibling directory
  parent = Path.cwd().parent
  if parent.is_dir():
    for item in parent.iterdir():
      if (
          item.is_dir()
          and item.name.lower() == "comfyui"
          and (item / "models").is_dir()
      ):
        return str(item.resolve())

  # 3. Known common base locations
  fallbacks = [
      Path.home() / "ComfyUI",
      Path("/workspace/ComfyUI"),
      Path("/opt/ComfyUI"),
      Path("C:/ComfyUI_windows_portable/ComfyUI"),
  ]
  for target in fallbacks:
    if target.is_dir() and (target / "models").is_dir():
      return str(target.resolve())

  return ""

def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

class ServerFolderDialog:
    """In-app server directory navigator with strict vertical clamping."""
    def __init__(self, title: str, on_select_callback):
        self.title = title
        self.on_select_callback = on_select_callback
        self.current_dir = Path.home()
        self.show_hidden = False

        if not self.current_dir.exists():
            self.current_dir = Path("/").resolve()

        # Dialog card clamped to fixed width with forced column direction
        with ui.dialog() as self.dialog, ui.card().classes(
            "w-[680px] max-w-[95vw] bg-[#111823] text-slate-100 border border-slate-700 shadow-2xl p-4 flex flex-col gap-3 no-wrap"
        ):
            # 1. Header & Hidden Toggle
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                ui.label(self.title).classes("text-sm font-bold text-[#00e5ff] tracking-wider truncate")
                self.hidden_checkbox = ui.checkbox(
                    "Show dotfiles (.)",
                    value=self.show_hidden,
                    on_change=self.toggle_hidden
                ).classes("text-xs text-slate-400 shrink-0")

            # 2. Current Path Bar (Strictly clamped & truncated to prevent horizontal expansion)
            with ui.row().classes("w-full bg-[#0c1017] p-2 rounded border border-slate-800 items-center no-wrap overflow-hidden"):
                ui.icon("folder", color="cyan").classes("text-sm mr-2 shrink-0")
                self.path_display = ui.label(str(self.current_dir)).classes(
                    "text-xs font-mono text-slate-300 truncate w-full"
                )

            # 3. Directory List Viewport (Strict vertical scroll only)
            self.folder_container = ui.column().classes(
                "w-full h-72 overflow-y-auto overflow-x-hidden bg-[#0c1017] p-2 rounded border border-slate-800 gap-1 flex flex-col no-wrap"
            )

            # 4. Action Buttons (Stacked at bottom, never pushed off-screen)
            with ui.row().classes("w-full items-center justify-between pt-1 no-wrap border-t border-slate-800"):
                ui.button("⮥ Up One Level", on_click=self.go_up).classes(
                    "bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1 shrink-0"
                )
                with ui.row().classes("gap-2 items-center shrink-0"):
                    ui.button("Cancel", on_click=self.dialog.close).classes(
                        "bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-1"
                    )
                    ui.button("Select Folder", on_click=self.confirm_selection).classes(
                        "bg-[#007a8a] hover:bg-[#00e5ff] hover:text-black text-white text-xs font-bold px-4 py-1"
                    )

    def toggle_hidden(self, e):
        self.show_hidden = e.value
        self.refresh_folders()

    def refresh_folders(self):
        self.path_display.text = str(self.current_dir)
        self.folder_container.clear()
        with self.folder_container:
            try:
                subdirs = []
                for p in sorted(self.current_dir.iterdir(), key=lambda x: x.name.lower()):
                    if p.is_dir():
                        if not self.show_hidden and p.name.startswith("."):
                            continue
                        subdirs.append(p)

                if not subdirs:
                    ui.label("(No visible directories here)").classes("text-xs text-slate-500 italic p-2")

                for sub in subdirs:
                    def make_handler(target_dir=sub):
                        return lambda: self.navigate_to(target_dir)

                    # Directory item row locked against horizontal wrapping
                    with ui.row().classes(
                        "w-full items-center justify-between hover:bg-slate-800/80 p-1.5 rounded cursor-pointer transition-colors no-wrap"
                    ).on("click", make_handler()):
                        with ui.row().classes("items-center gap-2 min-w-0 truncate no-wrap"):
                            is_dot = sub.name.startswith(".")
                            icon_color = "amber" if is_dot else "cyan"
                            ui.icon("folder", color=icon_color).classes("text-sm shrink-0")
                            ui.label(sub.name).classes("text-xs font-mono text-slate-200 truncate")

                        badges = []
                        if (sub / "models" / "diffusion_models").is_dir() or (sub / "models").is_dir():
                            badges.append(("ComfyUI Root", "cyan"))
                        if is_dot:
                            badges.append(("Hidden", "grey"))

                        with ui.row().classes("gap-1 shrink-0"):
                            for text, col in badges:
                                ui.badge(text, color=col).classes("text-[10px] text-black font-bold")

            except PermissionError:
                ui.label("Permission Denied").classes("text-xs text-rose-400 italic p-2")

    def navigate_to(self, path: Path):
        if path.is_dir():
            self.current_dir = path
            self.refresh_folders()

    def go_up(self):
        if self.current_dir.parent != self.current_dir:
            self.current_dir = self.current_dir.parent
            self.refresh_folders()

    def open(self, initial_path: str = ""):
        if initial_path:
            clean = Path(os.path.expanduser(initial_path)).resolve()
            if clean.is_dir():
                self.current_dir = clean
                if any(part.startswith(".") for part in clean.parts):
                    self.show_hidden = True
                    self.hidden_checkbox.value = True
        self.refresh_folders()
        self.dialog.open()

    def confirm_selection(self):
        self.on_select_callback(str(self.current_dir))
        self.dialog.close()

class NanoVaultConfigApp:
    def __init__(self):
        self.is_validated = True
        self.model_data = []

        self.comfyui_path = detect_comfyui_path()
        self.download_cache_path = DEFAULT_CACHE_DIR
        self.nanovault_path = DEFAULT_NANOVAULT_DIR

        self.hf_token = ""
        self.civitai_token = ""
        self.fast_hash = True
        self.saved_excluded_models = set()

        self.load_config()
        self.build_ui()

    def mark_dirty(self, _=None):
        self.is_validated = False
        self.status_indicator.text = "● UNSAVED MODIFICATIONS"
        self.status_indicator.classes(remove="text-[#00e5ff] text-slate-400", add="text-amber-400")

    def build_ui(self):
        # 1. Force strict column layout on the entire viewport and NiceGUI/Quasar roots
        ui.query("body").style(
            f"background-color: {COLOR_BG}; color: #e2e8f0; font-family: 'Segoe UI', Inter, sans-serif; margin: 0; padding: 0;"
        )
        ui.query(".q-page").style(
            "display: flex; flex-direction: column; width: 100%; min-height: 100vh; align-items: center;"
        )

        ui.add_head_html("""
            <style>
                #q-app, .q-layout, .q-page-container, .nicegui-content {
                    display: flex !important;
                    flex-direction: column !important;
                    width: 100% !important;
                    max-width: 100vw !important;
                    box-sizing: border-box !important;
                }
            </style>
            <script>
            window.isDirty = false;
            window.addEventListener('beforeunload', (event) => {
                if (window.isDirty) {
                    event.preventDefault();
                    event.returnValue = 'Unsaved configuration. Are you sure you want to exit?';
                }
            });
            </script>
        """)

        # Main Vertical Spine: Strict flex-col, fills vertical viewport, stacks cards vertically
        with ui.column().classes("w-full max-w-[1240px] mx-auto min-h-screen p-4 gap-4 flex flex-col items-stretch no-wrap"):

            # -------------------------------------------------------------
            # 1. Header (MIA Crest strictly bound + horizontal title lock)
            # -------------------------------------------------------------
            with ui.row().classes("w-full items-center justify-between pb-3 border-b border-slate-800 no-wrap shrink-0"):
                with ui.row().classes("items-center gap-4 no-wrap"):
                    crest_uri = get_crest_base64()
                    if crest_uri:
                        with ui.element("div").classes("w-[128px] h-[64px] flex items-center justify-center shrink-0 overflow-hidden rounded border border-slate-800 bg-[#0c1017]"):
                            ui.html(f'<img src="{crest_uri}" style="max-width: 128px; max-height: 64px; object-fit: contain;" />')
                    else:
                        with ui.card().classes("w-[128px] h-[64px] bg-[#0c1017] border border-[#00e5ff] items-center justify-center shrink-0"):
                            ui.label("MIA CREST").classes("text-xs font-bold text-[#00e5ff]")

                    with ui.column().classes("gap-0.5 min-w-0"):
                        ui.label("NANOVAULT // SYSTEM MATRIX").classes("text-lg font-black text-[#00e5ff] tracking-widest truncate")
                        ui.label("Tri-Directory Routing & Stasis Eviction Protocol").classes("text-xs text-slate-400 truncate")

                with ui.column().classes("items-end gap-1 shrink-0"):
                    self.status_indicator = ui.label("SYSTEM STABLE").classes("text-xs font-mono text-[#00e5ff] tracking-wider")

            # -------------------------------------------------------------
            # 2. Directory Routing Section (Full width stacked pane)
            # -------------------------------------------------------------
            with ui.card().classes("w-full bg-[#111823] border border-slate-800 p-4 gap-2 flex flex-col shrink-0"):
                ui.label("DIRECTORY ALLOCATION").classes("text-xs font-bold text-slate-400 tracking-wider")

                with ui.row().classes("w-full items-center gap-2 no-wrap"):
                    self.comfy_input = ui.input(
                        label="1. ComfyUI Folder (Auto-detected)",
                        value=self.comfyui_path,
                        on_change=lambda e: self.on_comfy_path_changed(e.value)
                    ).classes("flex-grow bg-[#0c1017]").props("dark outlined dense")

                    self.comfy_dialog = ServerFolderDialog("SELECT COMFYUI ROOT DIRECTORY", on_select_callback=self.on_comfy_selected)
                    ui.button("Browse...", icon="folder_open", on_click=lambda: self.comfy_dialog.open(self.comfy_input.value))\
                        .classes("bg-slate-800 text-[#00e5ff] border border-slate-700 h-[40px] text-xs font-bold shrink-0")

                with ui.row().classes("w-full items-center gap-2 no-wrap"):
                    self.cache_input = ui.input(
                        label="2. Download Cache Folder (Expanded Default)",
                        value=self.download_cache_path,
                        on_change=self.mark_dirty
                    ).classes("flex-grow bg-[#0c1017]").props("dark outlined dense")

                    self.cache_dialog = ServerFolderDialog("SELECT DOWNLOAD CACHE DIRECTORY", on_select_callback=self.on_cache_selected)
                    ui.button("Browse...", icon="folder_open", on_click=lambda: self.cache_dialog.open(self.cache_input.value))\
                        .classes("bg-slate-800 text-[#00e5ff] border border-slate-700 h-[40px] text-xs font-bold shrink-0")

                with ui.row().classes("w-full items-center gap-2 no-wrap"):
                    self.nanovault_input = ui.input(
                        label="3. NanoVault Stasis Root Folder",
                        value=self.nanovault_path,
                        on_change=self.mark_dirty
                    ).classes("flex-grow bg-[#0c1017]").props("dark outlined dense")

                    self.nanovault_dialog = ServerFolderDialog("SELECT NANOVAULT ROOT DIRECTORY", on_select_callback=self.on_nanovault_selected)
                    ui.button("Browse...", icon="folder_open", on_click=lambda: self.nanovault_dialog.open(self.nanovault_input.value))\
                        .classes("bg-slate-800 text-[#00e5ff] border border-slate-700 h-[40px] text-xs font-bold shrink-0")

            # -------------------------------------------------------------
            # 3. Parameters Panel (Full width stacked pane)
            # -------------------------------------------------------------
            with ui.card().classes("w-full bg-[#111823] border border-slate-800 p-4 gap-2 flex flex-col shrink-0"):
                with ui.row().classes("w-full items-center gap-4 no-wrap"):
                    self.hf_input = ui.input(
                        label="HF_TOKEN (Hugging Face Auth)",
                        password=True,
                        value=self.hf_token,
                        on_change=self.mark_dirty
                    ).classes("flex-1 bg-[#0c1017]").props("dark outlined dense")

                    self.civitai_input = ui.input(
                        label="CIVITAI_TOKEN (Civitai API)",
                        password=True,
                        value=self.civitai_token,
                        on_change=self.mark_dirty
                    ).classes("flex-1 bg-[#0c1017]").props("dark outlined dense")

                with ui.row().classes("w-full items-center justify-between pt-1 no-wrap"):
                    self.hash_checkbox = ui.checkbox(
                        "Enable Fast Hashing (XXH64 Sample Verification)",
                        value=self.fast_hash,
                        on_change=self.mark_dirty
                    ).classes("text-xs text-slate-300")

                    ui.button("↻ Rescan Models", on_click=self.populate_models)\
                        .classes("bg-slate-800 text-slate-300 text-xs border border-slate-700 px-3 shrink-0")

            # -------------------------------------------------------------
            # 4. Model Registry Table (Stacked below, expands vertically)
            # -------------------------------------------------------------
            with ui.column().classes("w-full flex-grow bg-[#111823] border border-slate-800 p-4 rounded min-h-[380px] flex flex-col"):
                with ui.row().classes("w-full items-center justify-between mb-2 no-wrap shrink-0"):
                    ui.label("MODEL WEIGHTS (CHECK TO PIN FROM EVICTION)").classes("text-xs font-bold text-slate-400 tracking-wider")
                    self.lock_count_label = ui.label("0 / 0 Pinned").classes("text-xs font-mono text-[#00e5ff]")

                columns = [
                    {"name": "name", "label": "Model Weight Name", "field": "name", "align": "left", "sortable": True},
                    {"name": "subfolder", "label": "Subfolder", "field": "subfolder", "align": "left", "sortable": True},
                    {"name": "size_bytes", "label": "Size", "field": "size_bytes", "align": "right", "sortable": True, ":format": 'val => (val ? (val / (1024*1024*1024)).toFixed(2) + " GB" : "0 GB")'},
                ]

                self.table = ui.table(
                    columns=columns,
                    rows=[],
                    row_key="name",
                    selection="multiple",
                    pagination={"rowsPerPage": 12},
                    on_select=self.on_selection_changed
                ).classes("w-full h-full bg-transparent text-slate-200 border-none").props("dark flat dense")

            # -------------------------------------------------------------
            # 5. Action Footer (Pinned at the base)
            # -------------------------------------------------------------
            with ui.row().classes("w-full items-center justify-between py-2 border-t border-slate-800 no-wrap shrink-0"):
                ui.label("NanoVault Console Daemon // Active").classes("text-[11px] font-mono text-slate-500")

                with ui.row().classes("gap-3 no-wrap"):
                    ui.button("Exit Console", on_click=self.handle_exit)\
                        .classes("bg-slate-800 text-slate-300 text-xs px-5 border border-slate-700")

                    ui.button("Apply Changes", icon="save", on_click=self.apply_configuration)\
                        .classes("bg-[#007a8a] hover:bg-[#00e5ff] hover:text-black text-white text-xs font-bold px-6")

    def on_selection_changed(self, e):
        """Native multi-select listener directly updating pinned set."""
        selected_rows = e.selection
        self.saved_excluded_models = {row["name"] for row in selected_rows}
        self.update_lock_counter()
        self.mark_dirty()

    def update_lock_counter(self):
        pinned = len(self.saved_excluded_models)
        self.lock_count_label.text = f"{pinned} / {len(self.model_data)} Pinned"

    def on_comfy_selected(self, chosen: str):
        self.comfy_input.value = chosen
        self.on_comfy_path_changed(chosen)

    def on_cache_selected(self, chosen: str):
        self.cache_input.value = chosen
        self.mark_dirty()

    def on_nanovault_selected(self, chosen: str):
        self.nanovault_input.value = chosen
        self.mark_dirty()

    def on_comfy_path_changed(self, path: str):
        self.comfyui_path = path
        self.mark_dirty()
        self.populate_models()

    def populate_models(self):
        """Recursively scan models from comfyui_path/models/."""
        self.model_data.clear()
        input_str = self.comfy_input.value.strip() if self.comfy_input.value else ""
        if not input_str:
            self.table.rows = []
            self.table.selected = []
            self.table.update()
            self.update_lock_counter()
            return

        base_dir = Path(os.path.expanduser(input_str))
        models_dir = base_dir / "models" if (base_dir / "models").is_dir() else base_dir

        selected_items = []
        if models_dir.exists() and models_dir.is_dir():
            valid_exts = {".safetensors", ".ckpt", ".pt", ".bin", ".pth", ".onnx", ".gguf"}
            for root, _, files in os.walk(models_dir):
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in valid_exts:
                        full_path = Path(root) / f
                        try:
                            size = full_path.stat().st_size
                        except OSError:
                            size = 0
                        rel_subfolder = str(full_path.parent.relative_to(models_dir))
                        row = {
                            "name": f,
                            "subfolder": rel_subfolder,
                            "size_bytes": size,
                            "size_str": format_size(size)
                        }
                        self.model_data.append(row)
                        if f in self.saved_excluded_models:
                            selected_items.append(row)

        self.table.rows = self.model_data
        self.table.selected = selected_items
        self.table.update()
        self.update_lock_counter()
    
    def load_config(self):
      env_mgr = EnvironmentConfig()
      if not env_mgr:
        return
      try:
        data = env_mgr.get_config()
        paths = data.get("paths", {})

        # 1. Only accept comfy_ui_root from config if that directory actually exists
        saved_comfy = paths.get("comfy_ui_root", "").strip()
        if saved_comfy and Path(os.path.expanduser(saved_comfy)).is_dir():
          self.comfyui_path = saved_comfy
        # Else: keep the live detected path from detect_comfyui_path()

        # 2. Same safeguard for the cache and vault directories
        saved_cache = paths.get("staging_cache", "").strip()
        if saved_cache:
          self.download_cache_path = saved_cache

        saved_vault = paths.get("vault_dir", "").strip()
        if saved_vault:
          self.nanovault_path = saved_vault

        tokens = data.get("tokens", {})
        self.hf_token = tokens.get("HF_TOKEN", "")
        self.civitai_token = tokens.get("CIVITAI_TOKEN", "")
        self.fast_hash = data.get("fast_hash", True)

        self.saved_excluded_models = set(data.get("exclude_from_purge", []))
        self.is_validated = True
      except Exception as e:
        ui.notify(f"Config load failure: {e}", type="negative")

    def apply_configuration(self):
        comfy_dir = Path(os.path.expanduser(self.comfy_input.value.strip()))
        cache_dir = Path(os.path.expanduser(self.cache_input.value.strip()))
        vault_dir = Path(os.path.expanduser(self.nanovault_input.value.strip()))

        if not comfy_dir.exists() or not comfy_dir.is_dir():
            ui.notify(
                "Validation Failure: ComfyUI directory is invalid.",
                type="negative",
            )
            return

        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            vault_dir.mkdir(parents=True, exist_ok=True)
        except Exception as err:
            ui.notify(
                f"Directory creation error: {err}",
                type="negative",
                position="center",
            )
            return

        excluded_list = sorted(list(self.saved_excluded_models))
        tokens = {}
        if self.hf_input.value.strip():
            tokens["HF_TOKEN"] = self.hf_input.value.strip()
        if self.civitai_input.value.strip():
            tokens["CIVITAI_TOKEN"] = self.civitai_input.value.strip()

        env_mgr = EnvironmentConfig()
        try:
            env_mgr.set_config(
                comfy_root=str(comfy_dir.resolve()),
                vault_dir=str(vault_dir.resolve()),
                staging_cache=str(cache_dir.resolve()),
                fast_hash=self.hash_checkbox.value,
                tokens=tokens,
                exclude_from_purge=excluded_list,
            )
            self.is_validated = True
            ui.run_javascript("window.isDirty = false;")
            self.status_indicator.text = "CONFIG IN STASIS (VERIFIED & SAVED)"
            self.status_indicator.classes(
                remove="text-amber-400", add="text-[#00e5ff]"
            )
            ui.notify(
                f"Saved {len(excluded_list)} pinned model(s) to config.json!",
                type="positive",
                position="top",
            )
        except Exception as e:
            ui.notify(
                f"Failed to write config.json: {e}",
                type="negative",
                position="center",
            )

    def handle_exit(self):
        if not self.is_validated:
            with ui.dialog() as exit_dialog, ui.card().classes("bg-[#111823] border border-amber-500 text-slate-100 p-4"):
                ui.label("Unsaved configuration.").classes("text-base font-bold text-amber-400")
                ui.label("Are you sure you want to exit?").classes("text-xs text-slate-300")
                with ui.row().classes("w-full justify-end gap-2 mt-3"):
                    ui.button("No, Return", on_click=exit_dialog.close).classes("bg-slate-800 text-slate-300 text-xs")
                    ui.button("Yes, Exit", on_click=lambda: app.shutdown()).classes("bg-rose-700 text-white text-xs font-bold")
            exit_dialog.open()
        else:
            app.shutdown()


@ui.page("/")
def main():
    NanoVaultConfigApp()


if __name__ == "__main__":
    ui.run(title="NanoVault Config Console", host="0.0.0.0", port=8080, reload=False)