import time
import sys
import shutil

# --- ANSI Color Constants ---
class ANSIColors:
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_WHITE = '\033[47m'
    
    # Styles
    BRIGHT = '\033[1m'
    RESET = '\033[0m'

# --- Color Map ---
COLOR_MAP = {
    'INFO': ANSIColors.CYAN,
    'DEBUG': ANSIColors.BLUE,
    'WARN': ANSIColors.YELLOW,
    'ERROR': ANSIColors.RED,
    'FATAL': ANSIColors.RED + ANSIColors.BG_WHITE + ANSIColors.BRIGHT,
    'SUCCESS': ANSIColors.GREEN,
    'FAILURE': ANSIColors.MAGENTA,
    'TIMEOUT': ANSIColors.YELLOW + ANSIColors.BRIGHT,
    'CLEANUP': ANSIColors.MAGENTA
}

def _clear_line():
    """Move to line start and clear terminal line so logs always start at col 0."""
    cols = shutil.get_terminal_size((80, 20)).columns
    sys.stdout.write('\r' + ' ' * cols + '\r')
    sys.stdout.flush()

def log(message: str, level: str = "INFO"):
    _clear_line()
    """Log message with timestamp and color."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    color = COLOR_MAP.get(level, ANSIColors.WHITE)
    print(f"{ANSIColors.WHITE}[{timestamp}]{ANSIColors.RESET} {color}[{level:^7}]{ANSIColors.RESET} {message}")

def log_separator(char='=', length=80, color=ANSIColors.CYAN):
    _clear_line()
    """Print a visual separator."""
    print(f"{color}{char * length}{ANSIColors.RESET}")

def log_output(stdout: str, stderr: str, return_code: int):
    _clear_line()
    """Detailed logging of command output."""
    log_separator('─', 80, ANSIColors.YELLOW)
    
    if stdout:
        log(f"STDOUT ({len(stdout)} chars):", "DEBUG")
        print(f"{ANSIColors.WHITE}{stdout}{ANSIColors.RESET}")
    else:
        log("STDOUT: <empty>", "DEBUG")
    
    if stderr:
        log(f"STDERR ({len(stderr)} chars):", "ERROR")
        print(f"{ANSIColors.RED}{stderr}{ANSIColors.RESET}")
    else:
        log("STDERR: <empty>", "DEBUG")
    
    log(f"Return Code: {return_code}", "DEBUG" if return_code == 0 else "ERROR")
    log_separator('─', 80, ANSIColors.YELLOW)
