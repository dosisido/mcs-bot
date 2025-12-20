

def _ansi_escape(s: str, code: int) -> str:
    return f"\033[{code}m{s}\033[0m"

def _ansi_escape_rgb(s: str, r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m{s}\033[0m"


# Value	Color
# \e[0;90m	Black
# \e[0;91m	Red
# \e[0;92m	Green
# \e[0;93m	Yellow
# \e[0;94m	Blue
# \e[0;95m	Purple
# \e[0;96m	Cyan
# \e[0;97m	White

def blackify(s: str) -> str: return _ansi_escape(s, 90)
def redify(s: str) -> str: return _ansi_escape(s, 91)
def greenify(s: str) -> str: return _ansi_escape(s, 92)
def yellowify(s: str) -> str: return _ansi_escape(s, 93)
def blueify(s: str) -> str: return _ansi_escape(s, 94)
def purpleify(s: str) -> str: return _ansi_escape(s, 95)
def cyanify(s: str) -> str: return _ansi_escape(s, 96)
def whiteify(s: str) -> str: return _ansi_escape(s, 97)


# Convenience: programmatic access by name
_colors = {
    "black": 90,
    "red": 91,
    "green": 92,
    "yellow": 93,
    "blue": 94,
    "purple": 95,
    "cyan": 96,
    "white": 97,
}


def colorize(s: str, name: str) -> str:
    """Return s wrapped in ANSI color by name (black, red, ...)."""
    code = _colors.get(name.lower())
    if code is None:
        raise ValueError(f"unknown color: {name}")
    return _ansi_escape(s, code)


__all__ = [
    "blackify",
    "redify",
    "greenify",
    "yellowify",
    "blueify",
    "purpleify",
    "cyanify",
    "whiteify",
    "colorize",
]