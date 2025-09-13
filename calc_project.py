import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math
import os
from datetime import datetime

HISTORY_FILE = "history.txt"
# ---------- Safe eval environment ----------
SAFE_NAMES = {
    k: getattr(math, k) for k in dir(math) if not k.startswith("__")
}
# add some aliases and built-ins we want to allow
SAFE_NAMES.update({
    "pi": math.pi,
    "e": math.e,
    "sqrt": math.sqrt,
    "ln": math.log,
    "log": lambda x, base=10: math.log(x, base),
    "fact": math.factorial,
    "factorial": math.factorial,
    "abs": abs,
    "pow": pow
})
def safe_eval(expr):
    """Evaluate a numeric expression safely using math namespace."""
    try:
        # Replace some visible operator notations if needed
        expr = expr.replace("^", "**")
        value = eval(expr, {"__builtins__": {}}, SAFE_NAMES)
        return value
    except Exception as e:
        raise
# ---------- Unit conversion data ----------
# A selection of conversion factors (base units and conversion lambdas)
UNIT_CATEGORIES = {
    "Length": {
        "base": "meter",
        "units": {
            "meter": 1.0,
            "kilometer": 1000.0,
            "centimeter": 0.01,
            "millimeter": 0.001,
            "mile": 1609.344,
            "yard": 0.9144,
            "foot": 0.3048,
            "inch": 0.0254
        }
    },
    "Area": {
        "base": "square_meter",
        "units": {
            "square_meter": 1.0,
            "square_kilometer": 1_000_000.0,
            "square_centimeter": 0.0001,
            "square_mile": 2_589_988.110336,
            "acre": 4046.8564224,
            "hectare": 10000.0
        }
    },
    "Volume": {
        "base": "liter",
        "units": {
            "liter": 1.0,
            "milliliter": 0.001,
            "cubic_meter": 1000.0,
            "cubic_centimeter": 0.001,
            "gallon_us": 3.785411784,
            "pint_us": 0.473176473
        }
    },
    "Weight": {
        "base": "kilogram",
        "units": {
            "kilogram": 1.0,
            "gram": 0.001,
            "milligram": 1e-6,
            "tonne": 1000.0,
            "pound": 0.45359237,
            "ounce": 0.028349523125
        }
    },
    "Temperature": {
        "units": ["celsius", "fahrenheit", "kelvin"]  # special handling
    },
    "Speed": {
        "base": "m/s",
        "units": {
            "m/s": 1.0,
            "km/h": 1/3.6,
            "mph": 0.44704,
            "knot": 0.514444444
        }
    },
    "Pressure": {
        "base": "pascal",
        "units": {
            "pascal": 1.0,
            "kpa": 1000.0,
            "bar": 100000.0,
            "atm": 101325.0,
            "psi": 6894.757293168
        }
    },
    "Power": {
        "base": "watt",
        "units": {
            "watt": 1.0,
            "kilowatt": 1000.0,
            "megawatt": 1_000_000.0,
            "horsepower": 745.69987158227
        }
    }
}
# Currency omitted because rates vary; if you want add static rates or fetch via API.
# ---------- App ----------
class CalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calculator + Unit Converter")
        self.geometry("920x600")
        self.resizable(False, False)
        self._create_widgets()
        self.history = []
        self.load_history()
        self.is_deg = True  # degree mode for trig
        self.update_mode_indicator()
    def _create_widgets(self):
        # Use a Notebook: Calculator | Unit converter
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        calc_frame = ttk.Frame(notebook)
        conv_frame = ttk.Frame(notebook)
        notebook.add(calc_frame, text="Calculator")
        notebook.add(conv_frame, text="Unit converter")
        # Left: Calculator and keypad
        left_frame = ttk.Frame(calc_frame)
        left_frame.pack(side="left", fill="both", expand=False, padx=(8,4), pady=8)
        self.display_var = tk.StringVar()
        display = tk.Entry(left_frame, textvariable=self.display_var, font=("Helvetica", 20), justify="right", bd=4, relief="sunken")
        display.grid(row=0, column=0, columnspan=6, sticky="we", padx=6, pady=6)
        display.bind("<Return>", lambda e: self.evaluate())
        # Mode indicator row
        self.mode_label = tk.Label(left_frame, text="", anchor="e")
        self.mode_label.grid(row=1, column=0, columnspan=6, sticky="we")
        btns = [
            ["sin","cos","tan","rad","deg","("],
            ["log","ln","!","AC","%)",")"],
            ["^","7","8","9","/","⌫"],
            ["sqrt","4","5","6","*","-"],
            ["π","1","2","3","+","="],
            ["e","00","0",".","",""]
        ]
        # map label to command
        for r, row in enumerate(btns, start=2):
            for c, label in enumerate(row):
                if label == "":
                    continue
                b = tk.Button(left_frame, text=label, width=6, height=2, font=("Helvetica", 12),command=lambda l=label: self.on_button(l))
                b.grid(row=r, column=c, padx=4, pady=4)
        # Right: History panel
        right_frame = ttk.Frame(calc_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(4,8), pady=8)
        ttk.Label(right_frame, text="History", font=("Helvetica", 14)).pack(anchor="nw", padx=6, pady=(6,0))
        self.history_box = tk.Listbox(right_frame, height=20)
        self.history_box.pack(fill="both", expand=True, padx=6, pady=6)
        self.history_box.bind("<Double-Button-1>", self.on_history_double)
        h_buttons = ttk.Frame(right_frame)
        h_buttons.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(h_buttons, text="Save history", command=self.save_history).pack(side="left")
        ttk.Button(h_buttons, text="Clear history", command=self.clear_history).pack(side="left", padx=6)
        # -------- Unit converter UI --------
        conv_top = ttk.Frame(conv_frame)
        conv_top.pack(fill="x", padx=8, pady=8)
        ttk.Label(conv_top, text="Category:").grid(row=0, column=0, sticky="w")
        self.category_var = tk.StringVar(value="Length")
        category_box = ttk.Combobox(conv_top, textvariable=self.category_var, values=list(UNIT_CATEGORIES.keys()), state="readonly")
        category_box.grid(row=0, column=1, sticky="w", padx=6)
        category_box.bind("<<ComboboxSelected>>", lambda e: self.build_converter())
        ttk.Label(conv_top, text="From:").grid(row=1, column=0, sticky="w")
        self.from_unit = tk.StringVar()
        self.from_box = ttk.Combobox(conv_top, textvariable=self.from_unit, state="readonly")
        self.from_box.grid(row=1, column=1, sticky="w", padx=6)
        ttk.Label(conv_top, text="To:").grid(row=1, column=2, sticky="w", padx=(12,0))
        self.to_unit = tk.StringVar()
        self.to_box = ttk.Combobox(conv_top, textvariable=self.to_unit, state="readonly")
        self.to_box.grid(row=1, column=3, sticky="w", padx=6)
        ttk.Label(conv_top, text="Value:").grid(row=2, column=0, sticky="w", pady=(8,0))
        self.conv_value = tk.StringVar()
        ttk.Entry(conv_top, textvariable=self.conv_value).grid(row=2, column=1, sticky="w", padx=6, pady=(8,0))
        ttk.Button(conv_top, text="Convert", command=self.convert_value).grid(row=2, column=2, padx=8, pady=(8,0))
        self.conv_result_var = tk.StringVar()
        ttk.Label(conv_top, textvariable=self.conv_result_var, font=("Helvetica", 12)).grid(row=2, column=3, sticky="w")
        # Conversion history within converter
        ttk.Label(conv_frame, text="Conversion history", font=("Helvetica", 12)).pack(anchor="nw", padx=8)
        self.conv_hist = tk.Listbox(conv_frame, height=10)
        self.conv_hist.pack(fill="both", expand=True, padx=8, pady=8)
        self.build_converter()
    # ---------- Calculator logic ----------
    def on_button(self, label):
        if label == "AC":
            self.display_var.set("")
            return
        if label == "clear":
            self.display_var.set(self.display_var.get()[:-1])
            return
        if label == "=":
            self.evaluate()
            return
        if label == "rad":
            self.is_deg = False
            self.update_mode_indicator()
            return
        if label == "deg":
            self.is_deg = True
            self.update_mode_indicator()
            return
        if label == "π" or label == "pi":
            self.display_var.set(self.display_var.get() + "pi")
            return
        if label == "e":
            self.display_var.set(self.display_var.get() + "e")
            return
        if label == "sqrt":
            self.display_var.set(self.display_var.get() + "sqrt(")
            return
        if label == "^":
            self.display_var.set(self.display_var.get() + "**")
            return
        if label == "%)":
            # small convenience: percent of previous expression? We'll append '%' and handle it on eval
            # but Python doesn't have '%' operator for percent; handle by replacing 'x%' with '(x/100)'
            self.display_var.set(self.display_var.get() + "%")
            return
        if label == "!":
            self.display_var.set(self.display_var.get() + "factorial(")
            return
        # trig and logs
        if label in ("sin", "cos", "tan"):
            self.display_var.set(self.display_var.get() + f"{label}(")
            return
        if label == "ln":
            self.display_var.set(self.display_var.get() + "ln(")
            return
        if label == "log":
            self.display_var.set(self.display_var.get() + "log(")
            return
        # default: append label
        self.display_var.set(self.display_var.get() + label)
    def update_mode_indicator(self):
        self.mode_label.config(text=("Mode: Degrees" if self.is_deg else "Mode: Radians"))
    def evaluate(self):
        expr = self.display_var.get().strip()
        if not expr:
            return
        # pre-process percent occurrences: replace number% with (number/100)
        import re
        expr = re.sub(r'(\d+(\.\d+)?)\%', r'(\1/100)', expr)
        # trig handling: if in degree mode convert degrees to radians for sin/cos/tan calls
        if self.is_deg:
            # wrap trig functions so they convert degrees to radians
            for fn in ("sin", "cos", "tan"):
                expr = expr.replace(f"{fn}(", f"{fn}(radians=")  # placeholder unlikely, fix below
            # safer approach: when calling sin(x) we transform to sin(math.radians(x))
            expr = expr.replace("sin(", "sin(radians(")
            expr = expr.replace("cos(", "cos(radians(")
            expr = expr.replace("tan(", "tan(radians(")
            # ensure a mapping to actual functions: define 'radians' in SAFE_NAMES as math.radians
            SAFE_NAMES.setdefault("radians", math.radians)
        else:
            # ensure trig functions get regular values; remove custom replacements if any
            expr = expr.replace("sin(radians(", "sin(")
            expr = expr.replace("cos(radians(", "cos(")
            expr = expr.replace("tan(radians(", "tan(")

        # Provide factorial alias
        SAFE_NAMES.setdefault("factorial", math.factorial)
        try:
            # Evaluate
            result = safe_eval(expr)
            # Format result nicely
            if isinstance(result, float):
                disp = str(round(result, 12)).rstrip('0').rstrip('.') if '.' in str(result) else str(result)
            else:
                disp = str(result)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hist_entry = f"{timestamp} | {self.display_var.get()} = {disp}"
            self.add_history(hist_entry)
            self.display_var.set(disp)
        except Exception as e:
            messagebox.showerror("Error", f"Could not evaluate expression\n{e}")
    # ---------- History ----------
    def add_history(self, text):
        self.history.insert(0, text)
        self.history_box.insert(0, text)
        # also save to disk
        self.save_history()
        # keep length reasonable
        if len(self.history) > 500:
            self.history = self.history[:500]
            self.history_box.delete(500, tk.END)
    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                # show newest first
                for ln in reversed(lines):
                    self.history_box.insert(0, ln)
                    self.history.append(ln)
            except Exception:
                pass
    def save_history(self):
        try:
            # write newest last so file reads chronological (old -> new)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                for ln in reversed(self.history_box.get(0, tk.END)):
                    f.write(ln + "\n")
            messagebox.showinfo("Saved", f"History saved to {HISTORY_FILE}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save history: {e}")
    def clear_history(self):
        if messagebox.askyesno("Clear history", "Clear all history?"):
            self.history_box.delete(0, tk.END)
            self.history = []
            try:
                if os.path.exists(HISTORY_FILE):
                    os.remove(HISTORY_FILE)
            except:
                pass
    def on_history_double(self, event):
        sel = self.history_box.curselection()
        if not sel:
            return
        text = self.history_box.get(sel[0])
        # Expect format "timestamp | expr = result"
        if "|" in text:
            parts = text.split("|", 1)[1].strip()
            # place expression back into display if present
            if "=" in parts:
                expr = parts.split("=", 1)[0].strip()
                self.display_var.set(expr)
    # ---------- Converter ----------
    def build_converter(self):
        cat = self.category_var.get()
        cfg = UNIT_CATEGORIES.get(cat, {})
        # special: temperature
        if cat == "Temperature":
            units = cfg["units"]
            self.from_box.config(values=units)
            self.to_box.config(values=units)
            self.from_unit.set(units[0])
            self.to_unit.set(units[1])
        else:
            units = list(cfg.get("units", {}).keys())
            self.from_box.config(values=units)
            self.to_box.config(values=units)
            if units:
                self.from_unit.set(units[0])
                self.to_unit.set(units[1] if len(units) > 1 else units[0])
    def convert_value(self):
        cat = self.category_var.get()
        val_str = self.conv_value.get().strip()
        if not val_str:
            messagebox.showwarning("Input", "Enter a value to convert")
            return
        try:
            value = float(val_str)
        except:
            messagebox.showerror("Input", "Value must be numeric")
            return
        if cat == "Temperature":
            from_u = self.from_unit.get()
            to_u = self.to_unit.get()
            result = self.convert_temperature(value, from_u, to_u)
        else:
            cfg = UNIT_CATEGORIES.get(cat)
            if not cfg:
                messagebox.showerror("Error", "Category not supported")
                return
            units = cfg["units"]
            from_u = self.from_unit.get()
            to_u = self.to_unit.get()
            if from_u not in units or to_u not in units:
                messagebox.showerror("Error", "Invalid units selected")
                return
            base_val = value * units[from_u]  # to base
            result = base_val / units[to_u]
        res_text = f"{value} {from_u} = {result} {to_u}"
        self.conv_result_var.set(res_text)
        # add to converter history
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conv_hist.insert(0, f"{ts} | {res_text}")
    @staticmethod
    def convert_temperature(val, frm, to):
        # convert from source to Celsius first
        def to_c(v, u):
            u = u.lower()
            if u == "celsius" or u == "c":
                return v
            if u == "fahrenheit" or u == "f":
                return (v - 32) * 5.0/9.0
            if u == "kelvin" or u == "k":
                return v - 273.15
            raise ValueError("Unknown temperature unit")
        def from_c(v, u):
            u = u.lower()
            if u == "celsius" or u == "c":
                return v
            if u == "fahrenheit" or u == "f":
                return v * 9.0/5.0 + 32
            if u == "kelvin" or u == "k":
                return v + 273.15
            raise ValueError("Unknown temperature unit")
        c = to_c(val, frm)
        return from_c(c, to)
if __name__ == "__main__":
    app = CalculatorApp()
    app.mainloop()