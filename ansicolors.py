__version__ = "0.1"
__author__ = "Matteo Delton"


class Foreground:
    BLACK = "\x1b[30m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    WHITE = "\x1b[37m"
    DEFAULT = "\x1b[39m"

    BRIGHT_BLACK = "\x1b[90m"
    BRIGHT_RED = "\x1b[91m"
    BRIGHT_GREEN = "\x1b[92m"
    BRIGHT_YELLOW = "\x1b[93m"
    BRIGHT_BLUE = "\x1b[94m"
    BRIGHT_MAGENTA = "\x1b[95m"
    BRIGHT_CYAN = "\x1b[96m"
    BRIGHT_WHITE = "\x1b[97m"

    @classmethod
    def rgb(cls, r, g, b):
        return f"\x1b[38;2;{r};{g};{b}m"

    @classmethod
    def black(cls, text):
        return f"{cls.BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def red(cls, text):
        return f"{cls.RED}{text}{cls.DEFAULT}"

    @classmethod
    def green(cls, text):
        return f"{cls.GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def yellow(cls, text):
        return f"{cls.YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def blue(cls, text):
        return f"{cls.BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def magenta(cls, text):
        return f"{cls.MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def cyan(cls, text):
        return f"{cls.CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def white(cls, text):
        return f"{cls.WHITE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_black(cls, text):
        return f"{cls.BRIGHT_BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def bright_red(cls, text):
        return f"{cls.BRIGHT_RED}{text}{cls.DEFAULT}"

    @classmethod
    def bright_green(cls, text):
        return f"{cls.BRIGHT_GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_yellow(cls, text):
        return f"{cls.BRIGHT_YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def bright_blue(cls, text):
        return f"{cls.BRIGHT_BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_magenta(cls, text):
        return f"{cls.BRIGHT_MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def bright_cyan(cls, text):
        return f"{cls.BRIGHT_CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_white(cls, text):
        return f"{cls.BRIGHT_WHITE}{text}{cls.DEFAULT}"


class Background:
    BLACK = "\x1b[40m"
    RED = "\x1b[41m"
    GREEN = "\x1b[42m"
    YELLOW = "\x1b[43m"
    BLUE = "\x1b[44m"
    MAGENTA = "\x1b[45m"
    CYAN = "\x1b[46m"
    WHITE = "\x1b[47m"
    DEFAULT = "\x1b[49m"

    BRIGHT_BLACK = "\x1b[100m"
    BRIGHT_RED = "\x1b[101m"
    BRIGHT_GREEN = "\x1b[102m"
    BRIGHT_YELLOW = "\x1b[103m"
    BRIGHT_BLUE = "\x1b[104m"
    BRIGHT_MAGENTA = "\x1b[105m"
    BRIGHT_CYAN = "\x1b[106m"
    BRIGHT_WHITE = "\x1b[107m"

    @classmethod
    def rgb(cls, r, g, b):
        return f"\x1b[48;2;{r};{g};{b}m"

    @classmethod
    def black(cls, text):
        return f"{cls.BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def red(cls, text):
        return f"{cls.RED}{text}{cls.DEFAULT}"

    @classmethod
    def green(cls, text):
        return f"{cls.GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def yellow(cls, text):
        return f"{cls.YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def blue(cls, text):
        return f"{cls.BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def magenta(cls, text):
        return f"{cls.MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def cyan(cls, text):
        return f"{cls.CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def white(cls, text):
        return f"{cls.WHITE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_black(cls, text):
        return f"{cls.BRIGHT_BLACK}{text}{cls.DEFAULT}"

    @classmethod
    def bright_red(cls, text):
        return f"{cls.BRIGHT_RED}{text}{cls.DEFAULT}"

    @classmethod
    def bright_green(cls, text):
        return f"{cls.BRIGHT_GREEN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_yellow(cls, text):
        return f"{cls.BRIGHT_YELLOW}{text}{cls.DEFAULT}"

    @classmethod
    def bright_blue(cls, text):
        return f"{cls.BRIGHT_BLUE}{text}{cls.DEFAULT}"

    @classmethod
    def bright_magenta(cls, text):
        return f"{cls.BRIGHT_MAGENTA}{text}{cls.DEFAULT}"

    @classmethod
    def bright_cyan(cls, text):
        return f"{cls.BRIGHT_CYAN}{text}{cls.DEFAULT}"

    @classmethod
    def bright_white(cls, text):
        return f"{cls.BRIGHT_WHITE}{text}{cls.DEFAULT}"


class Style:
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    ITALIC = "\x1b[3m"
    UNDERLINE = "\x1b[4m"
    BLINK = "\x1b[5m"
    INVERTED = "\x1b[7m"
    HIDDEN = "\x1b[8m"

    NORMAL = "\x1b[22m"
    STRAIGHT = "\x1b[23m"
    NOT_UNDERLINED = "\x1b[24m"
    BLINK_OFF = "\x1b[25m"
    INVERTED_OFF = "\x1b[27m"
    REVEAL = "\x1b[28m"

    RESET_ALL = "\x1b[0m"

    @classmethod
    def bold(cls, text):
        return f"{cls.BOLD}{text}{cls.NORMAL}"

    @classmethod
    def dim(cls, text):
        return f"{cls.DIM}{text}{cls.NORMAL}"

    @classmethod
    def italic(cls, text):
        return f"{cls.ITALIC}{text}{cls.STRAIGHT}"

    @classmethod
    def underline(cls, text):
        return f"{cls.UNDERLINE}{text}{cls.NOT_UNDERLINED}"

    @classmethod
    def blink(cls, text):
        return f"{cls.BLINK}{text}{cls.BLINK_OFF}"

    @classmethod
    def inverted(cls, text):
        return f"{cls.INVERTED}{text}{cls.INVERTED_OFF}"

    @classmethod
    def hidden(cls, text):
        return f"{cls.HIDDEN}{text}{cls.RESET}"

    @classmethod
    def reset_all(cls, text):
        return f"{text}{cls.RESET_ALL}"
