// hyprconf2lua WebAssembly In-Browser Runner using Pyodide
(() => {
  "use strict";

  // Elements
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const inputEditor = document.getElementById("input-editor");
  const outputEditor = document.getElementById("output-editor");
  const inputGutter = document.getElementById("input-gutter");
  const outputGutter = document.getElementById("output-gutter");
  const inputStats = document.getElementById("input-stats");
  const errorBanner = document.getElementById("error-banner");
  const errorMessage = document.getElementById("error-message");
  const valTranslated = document.getElementById("val-translated");
  const valPassthrough = document.getElementById("val-passthrough");
  const valFlagged = document.getElementById("val-flagged");
  const sampleBtn = document.getElementById("sample-btn");
  const fileUpload = document.getElementById("file-upload");
  const clearBtn = document.getElementById("clear-btn");
  const copyBtn = document.getElementById("copy-btn");
  const downloadBtn = document.getElementById("download-btn");
  const divider = document.getElementById("divider");
  const toast = document.getElementById("toast");

  let pyodideInstance = null;
  let convertFn = null;
  let debounceTimer = null;

  const SAMPLE_CONFIG = `# Hyprland 0.56+ showcase configuration
# Transpiled in-browser with hyprconf2lua

$mainMod = SUPER
$terminal = kitty
$menu = rofi -show drun

# Monitors (including monitorv2 block syntax)
monitor = DP-1, 2560x1440@165, 0x0, 1
monitor = HDMI-A-1, 1920x1080@60, 2560x0, 1

monitorv2 {
    output = eDP-1
    mode = 1920x1080@144
    position = auto
    scale = 1
    vrr = 1
    disabled = 0
    reserved = 10 20 10 20
}

# General configuration
general {
    gaps_in = 5
    gaps_out = 15
    border_size = 2
    layout = dwindle
    allow_tearing = false
}

# Decoration & blur
decoration {
    rounding = 8
    active_opacity = 1.0
    inactive_opacity = 0.85
    blur {
        enabled = true
        size = 4
        passes = 2
    }
}

# Permissions sandbox
permission = ^(/usr/lib/xdg-desktop-portal-hyprland)$, screencopy, allow
permission = /usr/bin/grim, screencopy, allow

# Keybindings (with bindd descriptions and flags)
bindd = $mainMod, Return, Open terminal, exec, $terminal
bindd = $mainMod, Space, Open app launcher, exec, $menu
bindd = $mainMod, Q, Close active window, killactive
bindd = $mainMod, F, Toggle floating, togglefloating

# Dispatcher simplification (exec, hyprctl dispatch -> native hl.dsp)
bind = $mainMod, 1, exec, hyprctl dispatch workspace 1
bind = $mainMod, 2, exec, hyprctl dispatch workspace 2

# Media keys with flags
bindle = , XF86AudioRaiseVolume, exec, wpctl set-volume 5%+
bindle = , XF86AudioLowerVolume, exec, wpctl set-volume 5%-
bindl = , XF86AudioMute, exec, wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle

# Mouse binds with aspect ratio modes
bindm = $mainMod, mouse:272, movewindow
bindm = $mainMod, mouse:273, resizewindow 1
`;

  // Show Toast
  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 2200);
  }

  // Update Line Gutters
  function updateGutter(editor, gutter) {
    const lines = editor.value.split("\n").length;
    let gutterHtml = "";
    for (let i = 1; i <= lines; i++) {
      gutterHtml += `<span class="gutter-num">${i}</span>`;
    }
    gutter.innerHTML = gutterHtml;
  }

  function syncScroll(editor, gutter) {
    gutter.scrollTop = editor.scrollTop;
  }

  // Live Transpilation
  function triggerConversion() {
    if (!convertFn) return;

    const source = inputEditor.value;
    updateGutter(inputEditor, inputGutter);
    inputStats.textContent = `${source.split("\n").length} lines`;

    if (!source.trim()) {
      outputEditor.value = "";
      updateGutter(outputEditor, outputGutter);
      valTranslated.textContent = "0";
      valPassthrough.textContent = "0";
      valFlagged.textContent = "0";
      errorBanner.style.display = "none";
      return;
    }

    try {
      const rawJson = convertFn(source);
      const result = JSON.parse(rawJson);

      if (result.success) {
        errorBanner.style.display = "none";
        outputEditor.value = result.lua;
      } else {
        errorBanner.style.display = "flex";
        errorMessage.textContent = result.errors && result.errors.length > 0 
          ? result.errors.join("; ") 
          : "Conversion failed. Please review input syntax.";
        outputEditor.value = result.lua || "-- Error occurred during conversion.";
      }

      if (result.report) {
        valTranslated.textContent = result.report.translated || 0;
        valPassthrough.textContent = result.report.passthrough || 0;
        valFlagged.textContent = result.report.flagged || 0;
      }
    } catch (err) {
      errorBanner.style.display = "flex";
      errorMessage.textContent = String(err);
      outputEditor.value = `-- Internal runtime error:\n-- ${err}`;
    }

    updateGutter(outputEditor, outputGutter);
  }

  function debouncedConversion() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(triggerConversion, 120);
  }

  // Initialize Pyodide & Engine
  async function initPyodide() {
    try {
      statusDot.className = "status-dot loading";
      statusText.textContent = "Loading WebAssembly Python engine...";

      pyodideInstance = await loadPyodide();

      statusText.textContent = "Mounting hyprconf2lua modules...";

      // Create package directory in Pyodide virtual filesystem
      pyodideInstance.FS.mkdir("/home/pyodide/hyprconf2lua");

      // Write bundled files
      if (window.HYPRCONF2LUA_BUNDLE) {
        for (const [filename, content] of Object.entries(window.HYPRCONF2LUA_BUNDLE)) {
          pyodideInstance.FS.writeFile(`/home/pyodide/hyprconf2lua/${filename}`, content);
        }
      }

      // Initialize Python bridge
      pyodideInstance.runPython(`
import sys
sys.path.insert(0, '/home/pyodide')
import json
from hyprconf2lua.converter import convert

def convert_bridge(source_code):
    res = convert(source_code)
    return json.dumps({
        "success": res.success,
        "lua": res.lua,
        "report": res.report,
        "errors": res.errors,
    })
`);

      convertFn = pyodideInstance.globals.get("convert_bridge");

      statusDot.className = "status-dot ready";
      statusText.textContent = "Engine Ready (Pyodide WebAssembly)";

      // Initial conversion if input has content
      if (inputEditor.value) {
        triggerConversion();
      } else {
        // Auto-load sample for instant delight
        inputEditor.value = SAMPLE_CONFIG;
        triggerConversion();
      }
    } catch (err) {
      console.error("Failed to initialize Pyodide:", err);
      statusDot.className = "status-dot error";
      statusText.textContent = "Failed to load Python engine";
      errorBanner.style.display = "flex";
      errorMessage.textContent = `Initialization Error: ${err.message || err}`;
    }
  }

  // Event Listeners
  inputEditor.addEventListener("input", debouncedConversion);
  inputEditor.addEventListener("scroll", () => syncScroll(inputEditor, inputGutter));
  outputEditor.addEventListener("scroll", () => syncScroll(outputEditor, outputGutter));

  // Tab Key indentation handling
  inputEditor.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const start = inputEditor.selectionStart;
      const end = inputEditor.selectionEnd;
      inputEditor.value = inputEditor.value.substring(0, start) + "    " + inputEditor.value.substring(end);
      inputEditor.selectionStart = inputEditor.selectionEnd = start + 4;
      debouncedConversion();
    }
  });

  // Load Sample
  sampleBtn.addEventListener("click", () => {
    inputEditor.value = SAMPLE_CONFIG;
    triggerConversion();
    showToast("Sample configuration loaded");
  });

  // File Upload
  fileUpload.addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      inputEditor.value = event.target.result;
      triggerConversion();
      showToast(`Loaded ${file.name}`);
    };
    reader.readAsText(file);
    fileUpload.value = "";
  });

  // Clear
  clearBtn.addEventListener("click", () => {
    inputEditor.value = "";
    triggerConversion();
    showToast("Input cleared");
  });

  // Copy Output
  copyBtn.addEventListener("click", async () => {
    if (!outputEditor.value) return;
    try {
      await navigator.clipboard.writeText(outputEditor.value);
      showToast("Lua config copied to clipboard! 📋");
    } catch (err) {
      outputEditor.select();
      document.execCommand("copy");
      showToast("Copied to clipboard! 📋");
    }
  });

  // Download Output
  downloadBtn.addEventListener("click", () => {
    if (!outputEditor.value) return;
    const blob = new Blob([outputEditor.value], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "hyprland.lua";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Downloaded hyprland.lua ⬇️");
  });

  // Draggable Split Divider
  let isDragging = false;
  divider.addEventListener("mousedown", (e) => {
    isDragging = true;
    divider.classList.add("active");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const mainRect = document.querySelector("main").getBoundingClientRect();
    const minWidth = 260;
    const totalWidth = mainRect.width;

    let leftWidth = e.clientX - mainRect.left;
    if (leftWidth < minWidth) leftWidth = minWidth;
    if (leftWidth > totalWidth - minWidth) leftWidth = totalWidth - minWidth;

    const inputPane = document.querySelector(".input-pane");
    const outputPane = document.querySelector(".output-pane");

    inputPane.style.flex = "none";
    inputPane.style.width = `${leftWidth}px`;
    outputPane.style.flex = "1";
  });

  document.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      divider.classList.remove("active");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
  });

  // Start initialization
  initPyodide();
})();
