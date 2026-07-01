import tkinter as tk
import threading
from tkinter import ttk, filedialog, messagebox
import os
import sys
import subprocess
import webbrowser
import ctypes
from JITclass import GlideConfig
from MAIN import glide

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
ICON_FILE = os.path.join(BASE_DIR, "others", "G.ico")
PNG_FILE = os.path.join(BASE_DIR, "others", "G.png")
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
    def show_tip(self, event=None):
        if self.tipwindow:
            return
        x = self.widget.winfo_rootx() + 35
        y = self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left",
            background="#ffffe0", relief="solid", borderwidth=1,
            font=("Arial", 9))
        label.pack(ipadx=4, ipady=2)
    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class GlideGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GLIDE 2.0")
        self._maximize_window()
        self.root.minsize(1200, 780)
        self.root.bind("<F5>", lambda event: self.start()
                       if str(self.start_btn["state"]) != "disabled"
                       else None)
        self.root.bind("<Control-o>", self._shortcut_load_parameters)
        self.root.bind("<Control-O>", self._shortcut_load_parameters)
        self.root.bind("<Control-s>", self._shortcut_save_parameters)
        self.root.bind("<Control-S>", self._shortcut_save_parameters)
        self.vars = {}
        self._setup_style()
        self._build_root_layout()
        self.build_widgets()
    def _setup_style(self):
        style = ttk.Style()
        try: style.theme_use("xpnative")
        except tk.TclError: pass
        style.configure("Header.TLabel", font=("Arial", 18, "bold"))
        style.configure("Subtle.TLabel", foreground="#222")
        style.configure("Section.TLabelframe", padding=10)
        style.configure("Section.TLabelframe.Label", font=("Arial", 11, "bold"))
        style.configure("Run.TButton", font=("Arial", 11, "bold"))

    def _maximize_window(self):
        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                w = self.root.winfo_screenwidth()
                h = self.root.winfo_screenheight()
                self.root.geometry(f"{w}x{h}+0+0")

    def _build_root_layout(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.main = ttk.Frame(self.root, padding=12)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.main.rowconfigure(1, weight=1)
        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)

        header = ttk.Frame(self.main)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)
        
        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=0, sticky="w")
        self.logo_img = None
        try:
            self.logo_img = tk.PhotoImage(file=PNG_FILE)
            self.logo_img = self.logo_img.subsample(4, 4)
        except Exception: pass
        if self.logo_img:
            ttk.Label(title_frame, image=self.logo_img).grid(
                row=0, column=0, rowspan=2, padx=(0, 8))
        ttk.Label(title_frame, text="GLIDE", style="Header.TLabel"
            ).grid(row=0, column=1, sticky="w")
        ttk.Label(title_frame, text=" version 2.0",style="Subtle.TLabel"
            ).grid(row=1, column=1, sticky="w")
        title_frame.columnconfigure(0, weight=1)
        ttk.Label(title_frame, text=" version 2.0", style="Subtle.TLabel")
        btn_frame = ttk.Frame(header)
        btn_frame.grid(row=0, column=1, sticky="e")
        load_btn = ttk.Button(btn_frame, text="Load parameters",
                              command=self.load_parameters)
        load_btn.grid(row=0, column=0, padx=6)
        save_btn = ttk.Button(btn_frame, text="Save parameters",
                              command=self.save_parameters)
        save_btn.grid(row=0, column=1, padx=6)
        ToolTip(load_btn, "Ctrl+O")
        ToolTip(save_btn, "Ctrl+S")
        ttk.Button(btn_frame, text="About", command=self.show_about
            ).grid(row=0, column=3, padx=6)
        
        self.left_panel = ttk.Frame(self.main)
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.left_panel.rowconfigure(0, weight=1)
        self.left_panel.columnconfigure(0, weight=1)
        self.right_panel = ttk.Frame(self.main)
        self.right_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        self.right_panel.rowconfigure(1, weight=1)
        self.right_panel.columnconfigure(0, weight=1)

        self.form_container = ttk.Frame(self.left_panel)
        self.form_container.grid(row=0, column=0, sticky="nsew")
        self.form_container.rowconfigure(0, weight=1)
        self.form_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.form_container, highlightthickness=0)
        self.form_scrollbar = ttk.Scrollbar(
            self.form_container, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.form_scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.form_scrollbar.grid(row=0, column=1, sticky="ns")

        self.form_frame = ttk.Frame(self.canvas)
        self.form_frame.columnconfigure(0, weight=1)
        self.form_window = self.canvas.create_window(
            (0, 0), window=self.form_frame, anchor="nw"
        )

        self.form_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfigure(self.form_window, width=e.width),
        )

        self.canvas.bind("<Enter>", 
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>",
            lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    def build_widgets(self):
        self._build_paths_section()
        self._build_grid_section()
        self._build_prior_section()
        self._build_thermal_section()
        self._build_action_section()
        self._build_log_section()
    def _make_section(self, parent, title, row):
        frame = ttk.LabelFrame(parent, text=title, style="Section.TLabelframe")
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        return frame
    def _add_field(self, parent, row, col, label, key, default="", width=18,
                   browse=None, extra_buttons=None, tooltip=None):
        ttk.Label(parent, text=label).grid(
            row=row, column=col, sticky="w", padx=(2, 8), pady=6)
        var = tk.StringVar(value=default)
        self.vars[key] = var
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 10), pady=6)
        btn_col = col +2
        if browse is not None:
            btn = ttk.Button(parent, text="🔍", width=4, command=browse)
            btn.grid(row=row, column=btn_col, sticky="w", padx=(0, 6),
                pady=6)
            if tooltip: ToolTip(btn, tooltip)
            btn_col += 1
    
        if extra_buttons:
            for text, cmd in extra_buttons:
                ttk.Button(parent, text=text, width=9, command=cmd).grid(
                    row=row, column=btn_col, sticky="w", padx=(0, 6), pady=6
                )
                btn_col += 1

    def _add_pair(self, parent, row, left=None, right=None):
        if left is not None:
            label, key, default, width, browse = left
            self._add_field(parent, row, 0, label, key, default, width, browse)
        if right is not None:
            label, key, default, width, browse = right
            self._add_field(parent, row, 2, label, key, default, width, browse)

    def _build_paths_section(self):
        sec = self._make_section(self.form_frame, "📂 Paths", 0)
        self._add_field(
            sec, 0, 0, "output path (folder)", "run_folder", width=36,
            browse=self.browse_run_folder,
            tooltip="Modeled exhumation rate, reduced variance, time resolution"
                    " & predicted ages will be saved.",
            extra_buttons=[("maps", self.open_mapper_window)]
        )
        self._add_field(
            sec, 1, 0, "topography file (.xyz)", "topofile", width=36,
            browse=self.browse_topofile,
            tooltip="Reading DEM data as .xyz file. See the manual for details",
            extra_buttons=[("download", self.open_dem_window)]
        )
        self._add_field(
            sec, 2, 0, "thermochron data (.csv)", "data_file", width=36,
            tooltip=("For an excel, rows of 'latitude', 'longitude', 'age', "
                     "'std' and 'method' are required.\nSee the maunal for details."),
            browse=self.browse_datafile
        )

    def _build_grid_section(self):
        sec = self._make_section(self.form_frame, "🌍 Grid & Region", 1)
        self._add_pair(sec, 0, ("west boundary (°)", "lon1", "", 14, None),
                       ("east boundary (°)", "lon2", "", 14, None))
        self._add_pair(sec, 1, ("south boundary (°)", "lat1", "", 14, None),
                       ("north boundary (°)", "lat2", "", 14, None))
        self._add_pair(sec, 2, ("spatial resolution (km)", "spacin", "", 14, None), None)

    def _build_prior_section(self):
        sec = self._make_section(self.form_frame, "📈 Prior & Time", 2)
        self._add_pair(sec, 0, ("prior rate (km/Myr)", "edot_mean", "", 14, None),
                       ("one sigma (km/Myr)", "sigma", "", 14, None))
        self._add_pair(sec, 1, ("total time (Myr)", "t_total", "", 14, None),
                       ("time step (Myr)", "deltat", "", 14, None))
        self._add_pair(sec, 2, ("correlation length (km)", "xL", "", 14, None),
                       ("iterations", "iters", "5", 14, None))

    def _build_thermal_section(self):
        sec = self._make_section(self.form_frame, "🔥 Thermal", 3)
        self._add_pair(sec, 0, ("model depth (km)", "zl", "", 14, None),
                       ("T at the sea level (°C)", "Ts", "", 14, None))
        self._add_pair(sec, 1, ("T at the bottom (°C)", "Tb", "", 14, None),
                       ("heat diffusivity (km²/Myr)", "kappa", "", 14, None))
        self._add_pair(sec, 2, ("heat production(°C/Myr)", "hp", "", 14, None), 
                       ("adiabatic rate (°C/km)", "grad", "", 14, None))

    def _build_action_section(self):
        sec = ttk.LabelFrame(self.right_panel, text="🔄 Run Control",
                             style="Section.TLabelframe")
        sec.grid(row=0, column=0, sticky="ew", pady=(8, 0))
        sec.columnconfigure(0, weight=1)
        self.start_btn = ttk.Button(sec, text="Start GLIDE <F5>",
                                    style="Run.TButton", command=self.start)
        self.start_btn.grid(row=0, column=0, sticky="ew")
        self.progress = ttk.Progressbar(
            sec, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self.status_var = tk.StringVar(value="READY")
        self.status_label = tk.Label(sec, textvariable=self.status_var)
        self.status_label.grid(row=3, column=0, pady=(8, 0))

    def _build_log_section(self):
        log_frame = ttk.LabelFrame(self.right_panel, text="📜 Model output",
                                   style="Section.TLabelframe")
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap="word", height=18, font=("Consolas", 11))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def browse_run_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.vars["run_folder"].set(folder)

    def browse_topofile(self):
        filename = filedialog.askopenfilename(
            filetypes=[
                ("XYZ files", "*.xyz"),
                ("All files", "*.*"),
            ]
        )
        if filename:
            self.vars["topofile"].set(filename)

    def browse_datafile(self):
        filename = filedialog.askopenfilename(
            filetypes=[
                ("CSV table files", "*.csv"),
                ("All files", "*.*"),
            ]
        )
        if filename:
            self.vars["data_file"].set(filename)
            
    def _shortcut_load_parameters(self, event=None):
        self.load_parameters()
        return "break"
    def _shortcut_save_parameters(self, event=None):
        self.save_parameters()
        return "break"
    def save_parameters(self):
        try:
            filename = filedialog.asksaveasfilename(
                title="Save parameters", defaultextension=".txt",
                initialfile="parameters.txt", filetypes=[("Text files", "*.txt")])
            if not filename: return
            with open(filename, "w", encoding="utf-8") as f:
                f.write("# output path (folder)\n")
                f.write(self.vars["run_folder"].get().strip() + "\n\n")
                f.write("# topography file (.xyz)\n")
                f.write(self.vars["topofile"].get().strip() + "\n\n")
                f.write("# thermochron data (.csv)\n")
                f.write(self.vars["data_file"].get().strip() + "\n\n")
                f.write("# west / east / south / north boundary (°)\n")
                f.write(f'{self.vars["lon1"].get().strip()} '
                        f'{self.vars["lon2"].get().strip()} '
                        f'{self.vars["lat1"].get().strip()} '
                        f'{self.vars["lat2"].get().strip()}\n\n')
                f.write("# spatial resolution expected for model (km)\n")
                f.write(self.vars["spacin"].get().strip() + "\n\n")
                f.write("# mean prior exhumation rate & one sigma (km/Myr)\n")
                f.write(f'{self.vars["edot_mean"].get().strip()} '
                        f'{self.vars["sigma"].get().strip()}\n\n')
                f.write("# correlation length (km)\n")
                f.write(self.vars["xL"].get().strip() + "\n\n")
                f.write("# time steps & total time (Myr)\n")
                f.write(f'{self.vars["deltat"].get().strip()} '
                        f'{self.vars["t_total"].get().strip()}\n\n')
                f.write("# iterations\n")
                f.write(self.vars["iters"].get().strip() + "\n\n")
                f.write("# model depth (km)\n")
                f.write(self.vars["zl"].get().strip() + "\n\n")
                f.write("# temperature at the sea level & bottom (°C)\n")
                f.write(f'{self.vars["Ts"].get().strip()} '
                        f'{self.vars["Tb"].get().strip()}\n\n')
                f.write("# heat diffusivity (km2/Myr) & heat production(°C/Myr)\n")
                f.write(f'{self.vars["kappa"].get().strip()} '
                        f'{self.vars["hp"].get().strip()}\n\n')
                f.write("# adiabatic rate (°C/km)\n")
                f.write(self.vars["grad"].get().strip() + "\n\n")
            self.write_log(f"Parameters saved to: {filename}")
            messagebox.showinfo("Success", "Parameters saved successfully.")
        except Exception as e:
            messagebox.showerror("Save error", str(e))
            
    def load_parameters(self):
        try:
            filename = filedialog.askopenfilename(
                title="Load parameters",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not filename: return
            values = []
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("#"): continue
                    values.append(line)
            expected = 13
            if len(values) < expected:
                raise ValueError(
                    f"Parameter file incomplete.\n"
                    f"Expected {expected} parameter lines, "
                    f"found {len(values)}."
                )
            self.vars["run_folder"].set(values[0])
            self.vars["topofile"].set(values[1])
            self.vars["data_file"].set(values[2])
            lon1, lon2, lat1, lat2 = values[3].split()
            self.vars["lon1"].set(lon1)
            self.vars["lon2"].set(lon2)
            self.vars["lat1"].set(lat1)
            self.vars["lat2"].set(lat2)
            self.vars["spacin"].set(values[4])
            edot_mean, sigma = values[5].split()
            self.vars["edot_mean"].set(edot_mean)
            self.vars["sigma"].set(sigma)
            self.vars["xL"].set(values[6])
            deltat, t_total = values[7].split()
            self.vars["deltat"].set(deltat)
            self.vars["t_total"].set(t_total)
            self.vars["iters"].set(values[8])
            self.vars["zl"].set(values[9])
            Ts, Tb = values[10].split()
            self.vars["Ts"].set(Ts)
            self.vars["Tb"].set(Tb)
            kappa, hp = values[11].split()
            self.vars["kappa"].set(kappa)
            self.vars["hp"].set(hp)
            self.vars["grad"].set(values[12])
            self.write_log(f"Parameters loaded from: {filename}")
            messagebox.showinfo("Success", "Parameters loaded successfully.")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
    def open_manual(self):
        try:
            manual_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "Manual.pdf")
            if not os.path.exists(manual_path):
                raise FileNotFoundError(f"Cannot find:\n{manual_path}")
            if sys.platform.startswith("win"):
                os.startfile(manual_path)
            elif sys.platform.startswith("darwin"):
                subprocess.call(["open", manual_path])
            else: subprocess.call(["xdg-open", manual_path])
        except Exception as e:
            messagebox.showerror("Manual", str(e))
    def show_about(self):
        win = tk.Toplevel(self.root)
        try: win.iconbitmap(ICON_FILE)
        except Exception: pass
        win.title("About")
        win.geometry("400x300")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="GLIDE Version 2.0", font=("Arial", 16, "bold")
            ).pack(pady=(15,5))
        ttk.Label(frame, text="Proposed by Fox et al., 2014",
            ).pack(pady=(5,2))
        fox_url = ttk.Label(frame,
            text="doi.org/10.5194/esurf-2-47-2014",
            foreground="blue", cursor="hand2")
        fox_url.pack(pady=(0,10))
        fox_url.bind("<Button-1>",
            lambda e: webbrowser.open("doi.org/10.5194/esurf-2-47-2014"))
        ttk.Label(frame, text="Omptimized by Ren et al., 2026",
            ).pack(pady=(5,2))
        url_label = ttk.Label(frame, 
            text="www.google.com",
            foreground="blue", cursor="hand2")
        url_label.pack(pady=(0, 15))
        url_label.bind("<Button-1>",
            lambda e: webbrowser.open("https://www.google.com"))
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=(0, 15))
        ttk.Button(btn_frame, text="Manual", command=self.open_manual,
            width=10).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(btn_frame, text="OK", command=win.destroy, width=10
            ).grid(row=0, column=1,padx=(0, 10))
    def _write_log_impl(self, msg):
        self.log_text.insert(tk.END, str(msg) + "\n")
        self.log_text.see(tk.END)
    def write_log(self, msg):
        self.root.after(0, self._write_log_impl, msg)
    def _update_progress_impl(self, value):
        self.progress["value"] = value
    def update_progress(self, value):
        self.root.after(0, self._update_progress_impl, value)
    def _set_status_impl(self, text):
        self.status_var.set(text)
        if text == "READY": color = "black"
        elif text == "RUNNING": color = "blue"
        elif text == "FINISHED": color = "green"
        elif text == "ERROR": color = "red"
        else: color = "black"
        self.status_label.config(fg=color)
    def set_status(self, text):
        self.root.after(0, self._set_status_impl, text)
    def _parse_int(self, key):
        raw = self.vars[key].get().strip()
        if not raw: raise ValueError("Parameter(s) required")
        return int(raw)
    def _parse_float(self, key):
        raw = self.vars[key].get().strip()
        if not raw:
            raise ValueError("Parameter(s) required")
        return float(raw)

    def collect_config(self):
        run_folder = self.vars["run_folder"].get().strip()
        topofile = self.vars["topofile"].get().strip()
        data_file = self.vars["data_file"].get().strip()

        if not run_folder:
            raise ValueError("Output path is required")
        if not topofile:
            raise ValueError("Topography file is required")
        if not data_file:
            raise ValueError("Thermochron data is required")
        nx, ny = self.get_grid_size_from_xyz(topofile)
        #self.write_log(f"Detected grid size: nx={nx}, ny={ny}")
        return GlideConfig(
            run_folder=run_folder,
            topofile=topofile,
            data_file=data_file,
            nx=nx, ny=ny,
            lon1=self._parse_float("lon1"),
            lon2=self._parse_float("lon2"),
            lat1=self._parse_float("lat1"),
            lat2=self._parse_float("lat2"),
            edot_mean=self._parse_float("edot_mean"),
            sigma=self._parse_float("sigma"),
            xL=self._parse_float("xL"),
            deltat=self._parse_float("deltat"),
            t_total=self._parse_float("t_total"),
            iters=self._parse_float("iters"),
            zl=self._parse_float("zl"),
            Ts=self._parse_float("Ts"),
            Tb=self._parse_float("Tb"),
            kappa=self._parse_float("kappa"),
            hp=self._parse_float("hp"),
            grad=self._parse_float("grad"),
            spacin=self._parse_float("spacin"),
        )

    def run_glide(self, cfg):
        try:
            self.set_status("RUNNING")
            result = glide(cfg, log_callback=self.write_log,
                progress_callback=self.update_progress,
            )
            self.set_status("FINISHED")
            self.write_log("")
            self.write_log("===== Summary =====")
            for k, v in result.items():
                self.write_log(f"{k}: {v}")
            self.root.after(0,
                lambda: messagebox.showinfo("Finished", "GLIDE completed successfully."),
            )
        except Exception as e:
            err_msg = str(e)
            self.write_log("")
            self.write_log("ERROR:")
            self.write_log(str(e))
            self.set_status("ERROR")
            self.root.after(0, messagebox.showerror, "Error", err_msg)
        finally:
            self.root.after(0,lambda: self.start_btn.config(state="normal"))

    def start(self):
        try:
            cfg = self.collect_config()
        except Exception as e:
            messagebox.showerror("Input error", str(e))
            return
        self.progress["value"] = 0
        self.start_btn.config(state="disabled")
        thread = threading.Thread(target=self.run_glide, args=(cfg,), daemon=True)
        thread.start()
        
    def open_dem_window(self):
        self.open_python_file("download.py")
    def open_mapper_window(self):
        self.open_python_file("mapper.py")

    def open_python_file(self, filename):
        try:
            filepath = os.path.join(BASE_DIR, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Cannot find:\n{filepath}")
            if sys.platform.startswith("win"):
                os.startfile(filepath)
            elif sys.platform.startswith("darwin"):
                subprocess.call(["open", filepath])
            else: subprocess.call(["xdg-open", filepath])
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def get_grid_size_from_xyz(self, xyz_file):
        first_lat = None
        nx = 0
        latitudes = set()
        with open(xyz_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2: continue
                lat = float(parts[1])
                if first_lat is None: first_lat = lat
                if lat == first_lat: nx += 1
                latitudes.add(lat)
        ny = len(latitudes)
        return nx, ny

def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GLIDE.2.0")
    except Exception:
        pass
    root = tk.Tk()
    try: root.iconbitmap(ICON_FILE)
    except Exception: pass
    GlideGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()