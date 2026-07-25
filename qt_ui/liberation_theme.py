import json
import logging
import os
from typing import Dict

global __theme_index

THEME_PREFERENCES_FILE_PATH = "liberation_theme.json"

DEFAULT_THEME_INDEX = 1


# new themes can be added here.
#
# Index 1 is the shipped default and is *generated* from the design tokens in
# qt_ui/theme/ rather than read from a stylesheet file. It deliberately keeps
# index 1 so existing installs — whose liberation_theme.json already stores 1 —
# pick up the redesign on launch instead of staying on the old sheet. The
# previous hand-written sheet is preserved at index 2 as an escape hatch.
THEMES: Dict[int, Dict[str, str]] = {
    0: {
        "themeName": "Vanilla",
        "themeFile": "windows-style.css",
        "themeIcons": "medium",
        "themeSource": "file",
    },
    1: {
        "themeName": "Retribution",
        "themeFile": "",
        "themeIcons": "light",
        "themeSource": "generated",
    },
    2: {
        "themeName": "DCS World (legacy)",
        "themeFile": "style-dcs.css",
        "themeIcons": "light",
        "themeSource": "file",
    },
}


def init():
    global __theme_index

    __theme_index = DEFAULT_THEME_INDEX

    if os.path.isfile(THEME_PREFERENCES_FILE_PATH):
        try:
            with open(THEME_PREFERENCES_FILE_PATH) as prefs:
                pref_data = json.loads(prefs.read())
                __theme_index = pref_data["theme_index"]
                # A stale config naming a theme that no longer exists used to
                # crash later, at the first get_theme_* call.
                if __theme_index not in THEMES:
                    logging.warning(
                        "Saved theme index %s is unknown; using the default.",
                        __theme_index,
                    )
                    __theme_index = DEFAULT_THEME_INDEX
                set_theme_index(__theme_index)
                save_theme_config()
        except:
            # is this necessary?
            set_theme_index(DEFAULT_THEME_INDEX)
            logging.exception("Unable to change theme")
    else:
        # is this necessary?
        set_theme_index(DEFAULT_THEME_INDEX)
        logging.error(
            f"Using default theme because {THEME_PREFERENCES_FILE_PATH} "
            "does not exist"
        )


# set theme index then use save_theme_config to save to file
def set_theme_index(x):
    global __theme_index
    __theme_index = x


# get theme index to reference other theme properties(themeName, themeFile, themeIcons)
def get_theme_index():
    global __theme_index
    return __theme_index


# get theme name based on current index
def get_theme_name():
    theme_name = THEMES[get_theme_index()]["themeName"]
    return theme_name


# get theme icon sub-folder name based on current index
def get_theme_icons():
    theme_icons = THEMES[get_theme_index()]["themeIcons"]
    return str(theme_icons)


# get theme stylesheet css based on current index
def get_theme_css_file():
    theme_file = THEMES[get_theme_index()]["themeFile"]
    return str(theme_file)


def theme_is_generated() -> bool:
    """True when the current theme is built from the design tokens.

    A generated theme has no stylesheet file; the caller asks
    qt_ui.theme.qss.build_stylesheet() for the sheet instead.
    """
    return THEMES[get_theme_index()].get("themeSource") == "generated"


# save current theme index to json file
def save_theme_config():
    pref_data = {"theme_index": get_theme_index()}
    with open(THEME_PREFERENCES_FILE_PATH, "w") as prefs:
        prefs.write(json.dumps(pref_data))
