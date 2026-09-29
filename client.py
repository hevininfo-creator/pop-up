import ctypes

ctypes.windll.user32.MessageBoxW(
    0,
    "Hello World",
    "Notice",
    0x0 | 0x40 | 0x40000,
)