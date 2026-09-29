# hello.py — runs on Windows, shows Hello World
import tkinter as tk
from tkinter import messagebox

root = tk.Tk()
root.withdraw()                       # hide the main window
messagebox.showinfo("Hello", "Hello World!")
root.destroy()