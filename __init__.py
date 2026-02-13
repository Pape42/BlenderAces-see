bl_info = {
    "name": "Acces'see (Accessibility Pack)",
    "author": "TEAM 6",
    "version": (4, 1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > AccessHelper",
    "description": "Daltonism highlight modes, UI brightness, UI scale, arrow navigation (F + arrows) with ▶ indicator, optional font size presets + reset, help popup.",
    "category": "Interface",
}

import bpy
import json

# ------------------------------------------------------------
# Backups / keymaps
# ------------------------------------------------------------
THEME_BACKUP_KEY = "accesshelper_theme_backup_v17"
STYLE_BACKUP_KEY = "accesshelper_ui_styles_backup_v12"
addon_keymaps = []

# ------------------------------------------------------------
# Theme targets
# ------------------------------------------------------------
WIDGETS = ["wcol_regular", "wcol_menu", "wcol_tooltip", "wcol_text", "wcol_list_item"]
WCOL_FIELDS = ["inner", "inner_sel", "item", "outline", "text", "text_sel"]

EDITORS = ["properties", "view_3d", "outliner"]
EDITOR_FIELDS = [("space", "text")]

GLOBAL_UI_ATTRS = ["widget_text", "text", "text_hi"]

# ------------------------------------------------------------
# Daltonism modes
# ------------------------------------------------------------
MODE_ITEMS = [
    ("OFF",   "TURN OFF",        "Retour au thème Blender normal"),
    ("PROT",  "Protanopie",      "Vision rouge déficiente"),
    ("PROTA", "Protanomalie",    "Protanomalie (rouge)"),
    ("DEUT",  "Deutéranopie",    "Vision vert déficiente"),
    ("DEUTA", "Deutéranomalie",  "Deutéranomalie (vert)"),
    ("TRIT",  "Tritanopie",      "Vision bleu déficiente"),
    ("TRITA", "Tritanomalie",    "Tritanomalie (bleu)"),
    ("ACHRO", "Achromatopsie",   "Mode gris"),
]

# Couleurs très visibles (pas orange)
HILITE_COLOR_BY_MODE = {
    "PROT":  (0.20, 0.80, 1.00),  # cyan/bleu
    "PROTA": (0.30, 0.95, 0.85),  # teal
    "DEUT":  (0.95, 0.95, 0.20),  # jaune
    "DEUTA": (0.20, 0.95, 0.40),  # vert
    "TRIT":  (1.00, 0.35, 0.85),  # magenta
    "TRITA": (0.70, 0.70, 1.00),  # bleu-violet
}

# ------------------------------------------------------------
# Font size presets (optional)
# ------------------------------------------------------------
FONT_PRESETS = [
    ("DEFAULT", "Default", "Aucun changement (Blender)"),
    ("COMFORT", "Comfort", "+1 pt"),
    ("LARGE", "Large", "+2 pt"),
    ("XL", "Extra Large", "+3 pt"),
]
UI_STYLE_KEYS = ["widget", "panel_title", "panel_title_sel", "widget_label", "widget_label_sel"]

# ------------------------------------------------------------
# Navigation items
# ------------------------------------------------------------
NAV_ITEMS = [
    "MODE",
    "MODE_INTENSITY",
    "BRIGHTNESS",
    "UI_SCALE",
    "FONT_PRESET",
    "HELP_POPUP",
]

NAV_LABELS = {
    "MODE": "Mode Daltonisme",
    "MODE_INTENSITY": "Intensité",
    "BRIGHTNESS": "Luminosité UI",
    "UI_SCALE": "UI Scale",
    "FONT_PRESET": "Taille texte",
    "HELP_POPUP": "Centre d’aide",
}

# ------------------------------------------------------------
# Utils
# ------------------------------------------------------------
def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def vec_to_list(v):
    return [float(v[i]) for i in range(len(v))]

def set_vec(target, values):
    n = min(len(target), len(values))
    for i in range(n):
        target[i] = float(values[i])

def force_ui_redraw():
    wm = bpy.context.window_manager
    for w in wm.windows:
        scr = w.screen
        if not scr:
            continue
        for area in scr.areas:
            area.tag_redraw()

def set_status(context, text: str | None):
    try:
        context.workspace.status_text_set(text)
    except Exception:
        pass

def to_gray(rgb):
    r, g, b = rgb
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (y, y, y)

def adjust_brightness_rgb(rgb, amount: float):
    """amount in [-1..+1] : -1->black, +1->white"""
    r, g, b = rgb
    if amount > 0.0:
        t = clamp01(amount)
        return (lerp(r, 1.0, t), lerp(g, 1.0, t), lerp(b, 1.0, t))
    if amount < 0.0:
        t = clamp01(-amount)
        return (lerp(r, 0.0, t), lerp(g, 0.0, t), lerp(b, 0.0, t))
    return (r, g, b)

# ------------------------------------------------------------
# Theme backup / restore
# ------------------------------------------------------------
def ensure_theme_backup():
    wm = bpy.context.window_manager
    if THEME_BACKUP_KEY in wm:
        return

    prefs = bpy.context.preferences
    if not prefs.themes:
        return
    theme = prefs.themes[0]
    ui = theme.user_interface

    data = {"widgets": {}, "editors": {}, "globals": {}}

    for wcol_name in WIDGETS:
        if not hasattr(ui, wcol_name):
            continue
        wcol = getattr(ui, wcol_name)
        dump = {}
        for f in WCOL_FIELDS:
            if hasattr(wcol, f):
                v = getattr(wcol, f)
                if hasattr(v, "__iter__"):
                    dump[f] = vec_to_list(v)
        if dump:
            data["widgets"][wcol_name] = dump

    for editor_name in EDITORS:
        if not hasattr(theme, editor_name):
            continue
        editor = getattr(theme, editor_name)
        ed_dump = {}
        for a, b in EDITOR_FIELDS:
            if hasattr(editor, a):
                sub = getattr(editor, a)
                if hasattr(sub, b):
                    v = getattr(sub, b)
                    if hasattr(v, "__iter__"):
                        ed_dump[f"{a}.{b}"] = vec_to_list(v)
        if ed_dump:
            data["editors"][editor_name] = ed_dump

    for attr in GLOBAL_UI_ATTRS:
        if hasattr(ui, attr):
            v = getattr(ui, attr)
            if hasattr(v, "__iter__"):
                data["globals"][attr] = vec_to_list(v)

    wm[THEME_BACKUP_KEY] = json.dumps(data)

def restore_theme_backup():
    wm = bpy.context.window_manager
    if THEME_BACKUP_KEY not in wm:
        force_ui_redraw()
        return

    raw = wm.get(THEME_BACKUP_KEY)
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        try: del wm[THEME_BACKUP_KEY]
        except Exception: pass
        force_ui_redraw()
        return

    prefs = bpy.context.preferences
    if not prefs.themes:
        try: del wm[THEME_BACKUP_KEY]
        except Exception: pass
        force_ui_redraw()
        return

    theme = prefs.themes[0]
    ui = theme.user_interface

    for wcol_name, fields_dump in data.get("widgets", {}).items():
        if not hasattr(ui, wcol_name):
            continue
        wcol = getattr(ui, wcol_name)
        for f, values in fields_dump.items():
            if hasattr(wcol, f):
                v = getattr(wcol, f)
                if hasattr(v, "__iter__"):
                    set_vec(v, values)

    for editor_name, ed_dump in data.get("editors", {}).items():
        if not hasattr(theme, editor_name):
            continue
        editor = getattr(theme, editor_name)
        for path, values in ed_dump.items():
            try: a, b = path.split(".")
            except Exception: continue
            if hasattr(editor, a):
                sub = getattr(editor, a)
                if hasattr(sub, b):
                    v = getattr(sub, b)
                    if hasattr(v, "__iter__"):
                        set_vec(v, values)

    for attr, values in data.get("globals", {}).items():
        if hasattr(ui, attr):
            v = getattr(ui, attr)
            if hasattr(v, "__iter__"):
                set_vec(v, values)

    try: del wm[THEME_BACKUP_KEY]
    except Exception: pass
    force_ui_redraw()

# ------------------------------------------------------------
# UI Styles (size) backup / apply
# ------------------------------------------------------------
def ensure_style_backup():
    wm = bpy.context.window_manager
    if STYLE_BACKUP_KEY in wm:
        return

    prefs = bpy.context.preferences
    styles = getattr(prefs, "ui_styles", None)
    if not styles or len(styles) == 0:
        return

    style = styles[0]
    dump = {}
    for k in UI_STYLE_KEYS:
        if hasattr(style, k):
            fs = getattr(style, k)
            if hasattr(fs, "points"):
                dump[k] = int(fs.points)

    wm[STYLE_BACKUP_KEY] = json.dumps(dump)

def restore_style_backup():
    wm = bpy.context.window_manager
    if STYLE_BACKUP_KEY not in wm:
        return

    raw = wm.get(STYLE_BACKUP_KEY)
    try:
        dump = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        try: del wm[STYLE_BACKUP_KEY]
        except Exception: pass
        return

    prefs = bpy.context.preferences
    styles = getattr(prefs, "ui_styles", None)
    if not styles or len(styles) == 0:
        try: del wm[STYLE_BACKUP_KEY]
        except Exception: pass
        return

    style = styles[0]
    for k, pts in dump.items():
        if hasattr(style, k):
            fs = getattr(style, k)
            if hasattr(fs, "points"):
                fs.points = int(pts)

    try: del wm[STYLE_BACKUP_KEY]
    except Exception: pass
    force_ui_redraw()

def apply_font_preset(preset_id: str):
    ensure_style_backup()

    prefs = bpy.context.preferences
    styles = getattr(prefs, "ui_styles", None)
    if not styles or len(styles) == 0:
        return

    if preset_id == "DEFAULT":
        restore_style_backup()
        return

    wm = bpy.context.window_manager
    try:
        base = json.loads(wm.get(STYLE_BACKUP_KEY, "{}"))
    except Exception:
        base = {}

    delta = {"COMFORT": 1, "LARGE": 2, "XL": 3}.get(preset_id, 0)
    style = styles[0]
    for k, base_pts in base.items():
        if hasattr(style, k):
            fs = getattr(style, k)
            if hasattr(fs, "points"):
                fs.points = int(base_pts) + int(delta)

    force_ui_redraw()

class ACCESSHELPER_OT_reset_fonts(bpy.types.Operator):
    bl_idname = "accesshelper.reset_fonts"
    bl_label = "Reset Fonts"
    bl_description = "Remet la taille de police Blender"

    def execute(self, context):
        props = context.scene.access_helper
        props.font_preset = "DEFAULT"
        restore_style_backup()
        return {'FINISHED'}

# ------------------------------------------------------------
# UI scale (0..2, applied min 0.25 for safety)
# ------------------------------------------------------------
def apply_ui_scale(props):
    prefs = bpy.context.preferences
    view = getattr(prefs, "view", None)
    if not view or not hasattr(view, "ui_scale"):
        return

    props.ui_scale = clamp(props.ui_scale, 0.0, 2.0)

    applied = max(0.25, props.ui_scale)
    view.ui_scale = applied

    if abs(props.ui_scale - applied) > 1e-6:
        props.ui_scale = applied

    force_ui_redraw()

# ------------------------------------------------------------
# Apply effects (daltonism + brightness)
# ------------------------------------------------------------
def apply_effects(props):
    ensure_theme_backup()
    wm = bpy.context.window_manager
    if THEME_BACKUP_KEY not in wm:
        return

    try:
        base = json.loads(wm[THEME_BACKUP_KEY])
    except Exception:
        return

    prefs = bpy.context.preferences
    if not prefs.themes:
        return

    theme = prefs.themes[0]
    ui = theme.user_interface

    mode = props.mode
    intensity = clamp01(props.mode_intensity)
    brightness = clamp(props.ui_brightness, -1.0, 1.0)
    hilite_rgb = HILITE_COLOR_BY_MODE.get(mode, (1.0, 1.0, 1.0))

    for wcol_name, fields_dump in base.get("widgets", {}).items():
        if not hasattr(ui, wcol_name):
            continue
        wcol = getattr(ui, wcol_name)

        for field, base_values in fields_dump.items():
            if not hasattr(wcol, field):
                continue
            v = getattr(wcol, field)
            if not hasattr(v, "__iter__"):
                continue

            target = base_values[:]

            # daltonism highlight
            if mode != "OFF" and intensity > 0.0 and field in {"inner_sel", "item", "outline", "text_sel"}:
                if mode == "ACHRO":
                    g = to_gray((target[0], target[1], target[2]))
                    target[0] = lerp(target[0], g[0], intensity)
                    target[1] = lerp(target[1], g[1], intensity)
                    target[2] = lerp(target[2], g[2], intensity)
                else:
                    target[0] = lerp(target[0], hilite_rgb[0], intensity)
                    target[1] = lerp(target[1], hilite_rgb[1], intensity)
                    target[2] = lerp(target[2], hilite_rgb[2], intensity)

            # brightness
            if brightness != 0.0 and field in {"inner", "inner_sel", "item", "outline", "text", "text_sel"}:
                r, g, b = adjust_brightness_rgb((target[0], target[1], target[2]), brightness)
                target[0], target[1], target[2] = r, g, b

            set_vec(v, target)

    # editor text brightness
    for editor_name, ed_dump in base.get("editors", {}).items():
        if not hasattr(theme, editor_name):
            continue
        editor = getattr(theme, editor_name)
        for path, base_values in ed_dump.items():
            try: a, b = path.split(".")
            except Exception: continue
            if hasattr(editor, a):
                sub = getattr(editor, a)
                if hasattr(sub, b):
                    v = getattr(sub, b)
                    if hasattr(v, "__iter__"):
                        target = base_values[:]
                        if brightness != 0.0:
                            r, g, bb = adjust_brightness_rgb((target[0], target[1], target[2]), brightness)
                            target[0], target[1], target[2] = r, g, bb
                        set_vec(v, target)

    # global brightness
    for attr, base_values in base.get("globals", {}).items():
        if hasattr(ui, attr):
            v = getattr(ui, attr)
            if hasattr(v, "__iter__"):
                target = base_values[:]
                if brightness != 0.0:
                    r, g, bb = adjust_brightness_rgb((target[0], target[1], target[2]), brightness)
                    target[0], target[1], target[2] = r, g, bb
                set_vec(v, target)

    force_ui_redraw()

# ------------------------------------------------------------
# Update callback
# ------------------------------------------------------------
def on_any_update(self, context):
    props = context.scene.access_helper

    apply_ui_scale(props)
    apply_font_preset(props.font_preset)

    if props.mode == "OFF" and abs(props.ui_brightness) < 1e-6:
        restore_theme_backup()
    else:
        apply_effects(props)

# ------------------------------------------------------------
# Properties
# ------------------------------------------------------------
class ACCESSHELPER_Props(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode Daltonisme",
        items=MODE_ITEMS,
        default="OFF",
        update=on_any_update
    )
    mode_intensity: bpy.props.FloatProperty(
        name="Intensité",
        min=0.0, max=1.0,
        default=0.85,
        subtype="FACTOR",
        update=on_any_update
    )
    ui_brightness: bpy.props.FloatProperty(
        name="Luminosité UI",
        min=-1.0, max=1.0,
        default=0.0,
        subtype="FACTOR",
        update=on_any_update
    )
    ui_scale: bpy.props.FloatProperty(
        name="UI Scale",
        min=0.0, max=2.0,
        default=1.0,
        update=on_any_update
    )

    font_preset: bpy.props.EnumProperty(
        name="Taille texte",
        items=FONT_PRESETS,
        default="DEFAULT",
        update=lambda s, c: apply_font_preset(c.scene.access_helper.font_preset)
    )

    nav_enabled: bpy.props.BoolProperty(name="Nav", default=False)
    nav_index: bpy.props.IntProperty(name="Nav Index", default=0, min=0, max=len(NAV_ITEMS)-1)
    nav_step: bpy.props.FloatProperty(name="Step", default=0.05, min=0.01, max=0.50, subtype="FACTOR")

# ------------------------------------------------------------
# Help popup
# ------------------------------------------------------------
class ACCESSHELPER_OT_help_popup(bpy.types.Operator):
    bl_idname = "accesshelper.help_popup"
    bl_label = "AccessHelper — Aide"
    bl_description = "Aide rapide"

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=520)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        layout.label(text="Centre d’aide — AccessHelper", icon="INFO")
        layout.separator()

        box = layout.box()
        box.label(text="Touches", icon="EVENT_K")
        col = box.column(align=False)
        col.label(text="F : activer la navigation")
        col.separator()
        col.label(text="↑/↓ : changer d’option")
        col.separator()
        col.label(text="←/→ : modifier la valeur")
        col.separator()
        col.label(text="Q ou ESC : quitter")
        layout.separator()
        layout.label(text="▶ indique l’option sélectionnée.")

    def execute(self, context):
        return {'FINISHED'}

# ------------------------------------------------------------
# Keyboard navigation
# ------------------------------------------------------------
class ACCESSHELPER_OT_toggle_nav(bpy.types.Operator):
    bl_idname = "accesshelper.toggle_nav"
    bl_label = "Toggle Keyboard Nav"

    def execute(self, context):
        props = context.scene.access_helper
        props.nav_enabled = not props.nav_enabled
        if props.nav_enabled:
            bpy.ops.accesshelper.keyboard_nav('INVOKE_DEFAULT')
        else:
            set_status(context, None)
            force_ui_redraw()
        return {'FINISHED'}

class ACCESSHELPER_OT_keyboard_nav(bpy.types.Operator):
    bl_idname = "accesshelper.keyboard_nav"
    bl_label = "AccessHelper Keyboard Navigation"
    bl_options = {'REGISTER'}

    _timer = None

    def _status_text(self, context):
        p = context.scene.access_helper
        item = NAV_ITEMS[p.nav_index]
        label = NAV_LABELS.get(item, item)
        if item == "MODE":
            val = p.mode
        elif item == "MODE_INTENSITY":
            val = f"{p.mode_intensity:.2f}"
        elif item == "BRIGHTNESS":
            val = f"{p.ui_brightness:+.2f}"
        elif item == "UI_SCALE":
            val = f"{p.ui_scale:.2f}"
        elif item == "FONT_PRESET":
            val = p.font_preset
        else:
            val = ""
        return f"▶ {label}: {val} | ↑↓ / ←→ | Q"

    def modal(self, context, event):
        p = context.scene.access_helper

        if not p.nav_enabled:
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
            set_status(context, None)
            return {'CANCELLED'}

        if event.type in {'Q', 'ESC'} and event.value == 'PRESS':
            p.nav_enabled = False
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
            set_status(context, None)
            force_ui_redraw()
            return {'CANCELLED'}

        if event.value != 'PRESS':
            return {'PASS_THROUGH'}

        if event.type == 'UP_ARROW':
            p.nav_index = (p.nav_index - 1) % len(NAV_ITEMS)
            set_status(context, self._status_text(context))
            force_ui_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'DOWN_ARROW':
            p.nav_index = (p.nav_index + 1) % len(NAV_ITEMS)
            set_status(context, self._status_text(context))
            force_ui_redraw()
            return {'RUNNING_MODAL'}

        item = NAV_ITEMS[p.nav_index]

        if event.type in {'LEFT_ARROW', 'RIGHT_ARROW'}:
            sgn = -1 if event.type == 'LEFT_ARROW' else 1

            if item == "MODE":
                order = ["OFF", "PROT", "PROTA", "DEUT", "DEUTA", "TRIT", "TRITA", "ACHRO"]
                idx = order.index(p.mode) if p.mode in order else 0
                p.mode = order[(idx + sgn) % len(order)]
                on_any_update(p, context)

            elif item == "MODE_INTENSITY":
                if p.mode == "OFF":
                    p.mode = "DEUT"
                p.mode_intensity = clamp01(p.mode_intensity + p.nav_step * sgn)
                on_any_update(p, context)

            elif item == "BRIGHTNESS":
                step = max(0.02, min(0.10, p.nav_step))
                p.ui_brightness = clamp(p.ui_brightness + step * sgn, -1.0, 1.0)
                on_any_update(p, context)

            elif item == "UI_SCALE":
                p.ui_scale = clamp(p.ui_scale + 0.05 * sgn, 0.0, 2.0)
                apply_ui_scale(p)

            elif item == "FONT_PRESET":
                ids = [x[0] for x in FONT_PRESETS]
                idx = ids.index(p.font_preset) if p.font_preset in ids else 0
                p.font_preset = ids[(idx + sgn) % len(ids)]
                apply_font_preset(p.font_preset)

            elif item == "HELP_POPUP":
                bpy.ops.accesshelper.help_popup('INVOKE_DEFAULT')

            set_status(context, self._status_text(context))
            force_ui_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            if item == "HELP_POPUP":
                bpy.ops.accesshelper.help_popup('INVOKE_DEFAULT')
                set_status(context, self._status_text(context))
                force_ui_redraw()
                return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        p = context.scene.access_helper
        p.nav_enabled = True
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        set_status(context, self._status_text(context))
        force_ui_redraw()
        return {'RUNNING_MODAL'}

# ------------------------------------------------------------
# Panel
# ------------------------------------------------------------
class ACCESSHELPER_PT_panel(bpy.types.Panel):
    bl_label = "AccessHelper"
    bl_idname = "ACCESSHELPER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AccessHelper"

    def _box(self, layout, props, key, title):
        box = layout.box()
        focused = props.nav_enabled and NAV_ITEMS[props.nav_index] == key
        if focused:
            box.label(text=f"▶ {title}", icon="DECORATE_KEYFRAME")
        else:
            box.label(text=title)
        return box

    def draw(self, context):
        layout = self.layout
        p = context.scene.access_helper

        header = layout.box()
        row = header.row(align=True)
        row.prop(p, "nav_enabled", text="Nav")
        row.operator("accesshelper.toggle_nav", text="F")
        row.operator("accesshelper.help_popup", text="", icon="INFO")

        box = self._box(layout, p, "MODE", "Mode Daltonisme")
        box.prop(p, "mode", text="")

        box = self._box(layout, p, "MODE_INTENSITY", "Intensité")
        box.prop(p, "mode_intensity", text="", slider=True)

        box = self._box(layout, p, "BRIGHTNESS", "Luminosité UI")
        box.prop(p, "ui_brightness", text="", slider=True)

        box = self._box(layout, p, "UI_SCALE", "UI Scale")
        box.prop(p, "ui_scale", text="", slider=True)

        box = self._box(layout, p, "FONT_PRESET", "Taille texte")
        row = box.row(align=True)
        row.prop(p, "font_preset", text="")
        row.operator("accesshelper.reset_fonts", text="", icon="LOOP_BACK")

        box = self._box(layout, p, "HELP_POPUP", "Centre d’aide")
        box.operator("accesshelper.help_popup", text="Ouvrir")

        layout.separator()
        layout.label(text="Raccourcis :", icon="KEYINGSET")
        layout.label(text="F = navigation | Ctrl+Alt+H = aide")

# ------------------------------------------------------------
# Keymaps
# ------------------------------------------------------------
def register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    km = kc.keymaps.new(name="Window", space_type="EMPTY")

    def add(op, key, ctrl=False, alt=False, shift=False):
        kmi = km.keymap_items.new(op, type=key, value="PRESS", ctrl=ctrl, alt=alt, shift=shift)
        addon_keymaps.append((km, kmi))

    add("accesshelper.toggle_nav", "F")
    add("accesshelper.help_popup", "H", ctrl=True, alt=True)

def unregister_keymaps():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    addon_keymaps.clear()

# ------------------------------------------------------------
# Register / Unregister
# ------------------------------------------------------------
classes = (
    ACCESSHELPER_Props,
    ACCESSHELPER_OT_reset_fonts,
    ACCESSHELPER_OT_help_popup,
    ACCESSHELPER_OT_toggle_nav,
    ACCESSHELPER_OT_keyboard_nav,
    ACCESSHELPER_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.access_helper = bpy.props.PointerProperty(type=ACCESSHELPER_Props)
    register_keymaps()

def unregister():
    try:
        scn = bpy.context.scene
        if hasattr(scn, "access_helper"):
            props = scn.access_helper
            props.nav_enabled = False
            set_status(bpy.context, None)
            restore_theme_backup()
            restore_style_backup()
    except Exception:
        pass

    unregister_keymaps()

    if hasattr(bpy.types.Scene, "access_helper"):
        del bpy.types.Scene.access_helper

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
