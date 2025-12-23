import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import requests
import threading
import os
import tempfile
import sys
import ctypes
from datetime import datetime
import json
import webbrowser
import base64

# Version info for auto-updater
try:
    from version import VERSION, BUILD_DATE
except:
    VERSION = "1.0.0"
    BUILD_DATE = "2025-12-21"

# Auto-updater module
try:
    import auto_updater
except:
    auto_updater = None



# --- Constants & Theme ---
class Theme:
    BG_DARK      = "#1e2227"
    BG_SIDEBAR   = "#23272e"
    BG_CARD      = "#2c313a"
    BG_HOVER     = "#3e4451"
    FG_PRIMARY   = "#abb2bf"
    FG_SECONDARY = "#5c6370"
    ACCENT       = "#61afef"
    SUCCESS      = "#98c379"
    WARNING      = "#e5c07b"
    ERROR        = "#e06c75"
    FONT_MAIN    = ("Segoe UI", 10)
    FONT_BOLD    = ("Segoe UI", 10, "bold")
    FONT_HEADER  = ("Segoe UI", 14, "bold")
    FONT_HUGE    = ("Segoe UI", 22, "bold")

REFRESH_RATE_MS = 5000

# --- Helpers ---
def format_time(iso_str):
    try: return datetime.fromisoformat(iso_str).strftime("%d/%m %H:%M")
    except: return "-"

# --- Widgets ---
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=160, height=40, radius=20, bg=Theme.ACCENT, fg="#1e2227"):
        super().__init__(parent, width=width, height=height, bg=parent['bg'], highlightthickness=0)
        self.command = command
        self.bg_hover = "#73bdf7"
        self.bg_disabled = "#4a4a4a"
        self.bg_normal = bg  # Init original bg
        self.fg_normal = fg
        self.fg_disabled = "#888888"
        self.state = "normal"
        
        self.rect = self.round_rect(2, 2, width-2, height-2, radius, fill=bg, outline=bg)
        self.text_obj = self.create_text(width/2, height/2, text=text, fill=fg, font=Theme.FONT_BOLD)
        
        # FIX: Bind clicks to CANVAS ONLY (widget binding covers all items)
        # Removing tag_binds to prevent duplicate event firing (double clicks)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = (x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1)
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_press(self, event):
        if self.state == "normal":
            self.itemconfig(self.rect, fill=self.bg_hover)
            
    def _on_release(self, event):
        if self.state == "normal":
            self.itemconfig(self.rect, fill=self.bg_hover) # Keep hover state
            if self.command:
                try:
                    self.command()
                except Exception as e:
                    messagebox.showerror("Erro no Botão", f"Falha ao executar ação: {e}")

    def _on_enter(self, event):
        if self.state == "normal":
            self.itemconfig(self.rect, fill=self.bg_hover)
            
    def _on_leave(self, event):
        if self.state == "normal":
            self.itemconfig(self.rect, fill=self.bg_normal)

    def set_text(self, text):
        self.itemconfig(self.text_obj, text=text)

    def disable(self, text=None):
        self.state = "disabled"
        self.itemconfig(self.rect, fill=self.bg_disabled)
        self.itemconfig(self.text_obj, fill=self.fg_disabled)
        if text: self.set_text(text)
        
    def enable(self, text=None, command=None):
        self.state = "normal"
        self.itemconfig(self.rect, fill=self.bg_normal)
        self.itemconfig(self.text_obj, fill=self.fg_normal)
        if text: self.set_text(text)
        if command: self.command = command # Allow updating command on enable

class SegmentedButton(tk.Frame):
    def __init__(self, parent, options, command=None):
        super().__init__(parent, bg=Theme.BG_DARK)
        self.options = options
        self.command = command
        self.buttons = {}
        self.current_val = options[0]
        for val in options:
            btn = tk.Label(self, text=val, font=("Segoe UI", 9, "bold"), bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY, padx=20, pady=6, cursor="hand2")
            btn.pack(side="left", padx=1)
            btn.bind("<Button-1>", lambda e, v=val: self.set(v))
            self.buttons[val] = btn
        self.update_styles()

    def set(self, val):
        self.current_val = val
        self.update_styles()
        if self.command: self.command(val)

    def get(self): return self.current_val

    def update_styles(self):
        for val, btn in self.buttons.items():
            btn.configure(bg=Theme.ACCENT if val == self.current_val else Theme.BG_CARD,
                          fg="#1e2227" if val == self.current_val else Theme.FG_PRIMARY)

DEFAULT_ICON_B64 = "AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAABAAABMLAAATCwAAAAAAAAAAAAD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8An///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AJ///wCf////n///AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wAAAAAAAAAA////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////"

# --- App ---
class MirrorMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mirror.ia - Plataforma de Inteligência em Áudio")
        self.geometry("1100x850")
        self.configure(bg=Theme.BG_DARK)
        self.minsize(900, 750)
        
        self._ensure_icon()
        try: self.iconbitmap("icon.ico")
        except: pass
        
        self.api_url = "http://localhost:8000"
        self.token = None
        self.is_admin = False
        self.user_info = {}
        self._real_server_ip = None  # Guarda IP real quando usa nome amigável
        
        self.tasks = []
        self.res_labels = {}
        self.running = True

        self.setup_styles()
        
        # Cleanup old version after update
        try:
            if os.path.exists("Mirror.ia_Monitor.exe.old"):
                os.remove("Mirror.ia_Monitor.exe.old")
        except:
            pass
        
        # Check for updates (silent, in background)
        if auto_updater:
            self.after(2000, lambda: threading.Thread(
                target=lambda: auto_updater.check_for_updates(self, VERSION, Theme), 
                daemon=True
            ).start())
        
        # Create beautiful header bar for branding
        self.header = tk.Frame(self, bg=Theme.BG_SIDEBAR, height=60)
        self.header.pack(side="top", fill="x")
        self.header.pack_propagate(False)
        
        # App icon and branding
        if os.path.exists("icon.png"):
            try:
                from PIL import Image, ImageTk
                icon_pil = Image.open("icon.png").resize((40, 40), Image.Resampling.LANCZOS)
                self.header_icon = ImageTk.PhotoImage(icon_pil)
                tk.Label(self.header, image=self.header_icon, bg=Theme.BG_SIDEBAR).pack(side="left", padx=20)
            except: pass
        
        tk.Label(self.header, text="Mirror.ia", bg=Theme.BG_SIDEBAR, fg=Theme.ACCENT, 
                font=("Segoe UI", 16, "bold")).pack(side="left", padx=5)
        tk.Label(self.header, text="Plataforma de Inteligência em Áudio", bg=Theme.BG_SIDEBAR, 
                fg=Theme.FG_SECONDARY, font=("Segoe UI", 10)).pack(side="left", padx=10)
        
        self.show_login()

    def _ensure_icon(self):
        if not os.path.exists("icon.ico"):
            try:
                with open("icon.ico", "wb") as f:
                    f.write(base64.b64decode(DEFAULT_ICON_B64))
            except: pass
    
    def clear_window(self):
        """Clear all widgets except header"""
        for widget in self.winfo_children():
            if widget != self.header:
                widget.destroy()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('alt')
        style.configure(".", background=Theme.BG_DARK, foreground=Theme.FG_PRIMARY, font=Theme.FONT_MAIN)
        style.configure("TFrame", background=Theme.BG_DARK)
        style.configure("Card.TFrame", background=Theme.BG_CARD)
        style.configure("Treeview", background=Theme.BG_DARK, foreground=Theme.FG_PRIMARY, fieldbackground=Theme.BG_DARK, rowheight=35, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=Theme.BG_CARD, foreground=Theme.FG_PRIMARY, font=Theme.FONT_BOLD, relief="flat", padding=10)
        style.map("Treeview", background=[('selected', Theme.BG_HOVER)])
        style.configure("Modern.TEntry", fieldbackground=Theme.BG_CARD, foreground=Theme.FG_PRIMARY, borderwidth=0, padding=10)
        
        # Tabs (Notebook) - Global Config
        style.configure("TNotebook", background=Theme.BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=Theme.BG_CARD, foreground=Theme.FG_SECONDARY, padding=[15, 5], font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", Theme.ACCENT)], foreground=[("selected", Theme.BG_DARK)])

    # --- Login/Register Toggle ---
    def show_login(self):
        self.clear_window()
        self._login_mode = True  # True = Login, False = Register
        
        # Main container
        f = tk.Frame(self, bg=Theme.BG_DARK)
        f.place(relx=0.5, rely=0.5, anchor="center")
        
        # Logo Image - Circular
        if os.path.exists("icon.png"):
            try:
                from PIL import Image, ImageTk, ImageDraw
                pil_img = Image.open("icon.png").convert("RGBA")
                pil_img = pil_img.resize((120, 120), Image.Resampling.LANCZOS)
                mask = Image.new('L', (120, 120), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 120, 120), fill=255)
                output = Image.new('RGBA', (120, 120), (26, 28, 36, 255))
                output.paste(pil_img, (0, 0))
                output.putalpha(mask)
                logo_img = ImageTk.PhotoImage(output)
                logo_label = tk.Label(f, image=logo_img, bg=Theme.BG_DARK)
                logo_label.image = logo_img
                logo_label.pack(pady=(0, 10))
            except Exception as e:
                print(f"Erro ao carregar logo: {e}")
        
        # Branding
        tk.Label(f, text="Mirror.ia", font=("Segoe UI", 32, "bold"), bg=Theme.BG_DARK, fg=Theme.ACCENT).pack(pady=(0, 5))
        tk.Label(f, text="Plataforma de Inteligência em Áudio", font=("Segoe UI", 12), bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY).pack(pady=(0, 25))
        
        # (Changelog movido para rodapé)
        
        # Toggle Buttons
        toggle_frame = tk.Frame(f, bg=Theme.BG_DARK)
        toggle_frame.pack(pady=(0, 15))
        
        self.btn_login_tab = RoundedButton(toggle_frame, "LOGIN", lambda: self._switch_mode(True), width=150, bg=Theme.ACCENT)
        self.btn_login_tab.pack(side="left", padx=5)
        
        self.btn_register_tab = RoundedButton(toggle_frame, "CRIAR CONTA", lambda: self._switch_mode(False), width=150, bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY)
        self.btn_register_tab.pack(side="left", padx=5)
        
        # Load Config
        import json
        saved_srv, saved_usr, saved_pwd = self.api_url, "admin", ""
        is_saved = False
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as cf:
                    c = json.load(cf)
                    saved_srv = c.get("server", self.api_url)
                    saved_usr = c.get("user", "")
                    saved_pwd = c.get("password", "")
                    is_saved = True
            except: pass
        
        # Form Container (will be switched)
        self.form_container = tk.Frame(f, bg=Theme.BG_DARK)
        self.form_container.pack(fill="both", expand=True)
        
        # Store refs
        self._saved_srv = saved_srv
        self._saved_usr = saved_usr
        self._saved_pwd = saved_pwd
        self._is_saved = is_saved
        self._parent_frame = f
        
        # Initial mode = Login
        self._render_login_form()
        
        # Auto-discover IP on startup
        self._start_connection_check()
            
        # Version Label (Footer Right) - Clicável para Changelog
        ver_lbl = tk.Label(self, text=f"v{VERSION}", bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8), cursor="hand2")
        ver_lbl.place(relx=0.98, rely=0.98, anchor="se")
        ver_lbl.bind("<Button-1>", lambda e: self._show_changelog())
        ver_lbl.bind("<Enter>", lambda e: ver_lbl.config(fg=Theme.ACCENT))
        ver_lbl.bind("<Leave>", lambda e: ver_lbl.config(fg=Theme.FG_SECONDARY))
        
    def _start_connection_check(self):
        """Inicia verificação de conexão"""
        # Sempre executa o auto-discovery no boot, conforme solicitado
        self.after(200, lambda: self.auto_discover_ip(silent=True))

    def _check_connection_thread(self, srv):
        """Thread que verifica conexão e habilita/desabilita botão"""
        try:
            if srv and srv.strip() == "": # Ignora vazios
                 self.after(0, lambda: self.btn_action.enable("VERIFICAR CONEXÃO"))
                 return

            if srv == "Mirror.ia Server" and hasattr(self, '_real_server_ip'):
                srv = self._real_server_ip
            
            if not srv.startswith("http"):
                srv = f"http://{srv}"
            
            # Atualiza UI para 'Verificando...'
            self.after(0, lambda: self.btn_action.disable("VERIFICANDO..."))
            
            # Tenta conectar (health check)
            r = requests.get(f"{srv.rstrip('/')}/health/live", timeout=3)
            
            if r.status_code == 200:
                # SUCESSO!
                # FIX: Explicitly re-bind the correct command on enable
                self.after(0, lambda: self.btn_action.enable("ENTRAR", command=self.do_login))
                self.after(0, lambda: self.lbl_msg.config(text=""))
            else:
                raise Exception(f"Status {r.status_code}")
                
        except Exception as e:
            # FALHA
            def _retry():
                curr_srv = self.ent_srv.get()
                threading.Thread(target=self._check_connection_thread, args=(curr_srv,), daemon=True).start()
            
            self.after(0, lambda: self.btn_action.disable("VERIFICAR CONEXÃO"))
            
            # Habilita botão com cor de alerta para reconectar
            self.after(0, lambda: self.btn_action.enable("RECONECTAR", command=_retry))
            self.after(0, lambda: self.btn_action.itemconfig(self.btn_action.rect, fill="#e67e22"))
            self.after(0, lambda: self.lbl_msg.config(text="⚠️ Servidor inacessível", fg=Theme.ERROR))
    
    def _switch_mode(self, is_login):
        """Switch between login and register mode"""
        if self._login_mode == is_login:
            return  # Same mode, do nothing
        
        self._login_mode = is_login
        
        # Update button styles (usando itemconfig para Canvas)
        if is_login:
            self.btn_login_tab.itemconfig(self.btn_login_tab.rect, fill=Theme.ACCENT)
            self.btn_login_tab.itemconfig(self.btn_login_tab.text_obj, fill="#1e2227")
            self.btn_login_tab.bg_normal = Theme.ACCENT
            
            self.btn_register_tab.itemconfig(self.btn_register_tab.rect, fill=Theme.BG_CARD)
            self.btn_register_tab.itemconfig(self.btn_register_tab.text_obj, fill=Theme.FG_PRIMARY)
            self.btn_register_tab.bg_normal = Theme.BG_CARD
        else:
            self.btn_login_tab.itemconfig(self.btn_login_tab.rect, fill=Theme.BG_CARD)
            self.btn_login_tab.itemconfig(self.btn_login_tab.text_obj, fill=Theme.FG_PRIMARY)
            self.btn_login_tab.bg_normal = Theme.BG_CARD
            
            self.btn_register_tab.itemconfig(self.btn_register_tab.rect, fill=Theme.ACCENT)
            self.btn_register_tab.itemconfig(self.btn_register_tab.text_obj, fill="#1e2227")
            self.btn_register_tab.bg_normal = Theme.ACCENT
        
        # Clear form
        for widget in self.form_container.winfo_children():
            widget.destroy()
        
        # Render appropriate form
        if is_login:
            self._render_login_form()
        else:
            self._render_register_form()
    
    def _render_login_form(self):
        """Render login form fields"""
        f = self.form_container
        
        self.ent_srv = self.create_input(f, "Servidor API", self._saved_srv)
        
        # Auto-discover IP button
        discover_btn = tk.Frame(f, bg=Theme.BG_DARK)
        discover_btn.pack(pady=(5, 0), fill="x")
        auto_discover_link = tk.Label(discover_btn, text="🔍 Buscar IP Automaticamente", 
                                      bg=Theme.BG_DARK, fg=Theme.ACCENT, font=("Segoe UI", 9), cursor="hand2")
        auto_discover_link.pack(side="left")
        auto_discover_link.bind("<Button-1>", lambda e: self.auto_discover_ip())
        self.discover_status = tk.Label(discover_btn, text="", bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8))
        self.discover_status.pack(side="right")
        
        self.ent_usr = self.create_input(f, "Usuário", self._saved_usr)
        self.ent_pwd = self.create_input(f, "Senha", self._saved_pwd, is_pass=True)
        self.ent_pwd.bind("<Return>", lambda e: self.do_login())
        
        # Save Password Checkbox
        self.var_save = tk.BooleanVar(value=self._is_saved)
        chk = tk.Checkbutton(f, text="Salvar dados de acesso", variable=self.var_save, 
                             bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, selectcolor=Theme.BG_DARK, 
                             activebackground=Theme.BG_DARK, activeforeground=Theme.FG_PRIMARY)
        chk.pack(pady=(10, 0), anchor="w")
        
        self.btn_action = RoundedButton(f, "AGUARDE...", self.do_login, width=300, bg=Theme.ACCENT)
        self.btn_action.pack(pady=15)
        self.btn_action.disable()
        
        self.lbl_msg = tk.Label(f, text="", bg=Theme.BG_DARK, fg=Theme.ERROR)
        self.lbl_msg.pack()

        # FIX: Force immediate connection check for the newly created button
        # This prevents the button from getting stuck in "Aguarde..." if a previous check finished
        if self.ent_srv.get().strip():
             threading.Thread(target=self._check_connection_thread, args=(self.ent_srv.get(),), daemon=True).start()
    
    def _render_register_form(self):
        """Render register form fields"""
        f = self.form_container
        
        # Servidor info (apenas texto)
        srv_display = self._saved_srv if self._saved_srv else "Não configurado"
        if srv_display == "Mirror.ia Server": srv_display = "Mirror.ia Server (Conectado)"
        
        tk.Label(f, text=f"Servidor: {srv_display}", bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, 
                font=("Segoe UI", 9)).pack(pady=(0, 10))

        # Register fields
        self.ent_reg_fullname = self.create_input(f, "Nome Completo", "")
        self.ent_reg_email = self.create_input(f, "Email", "")
        self.ent_reg_username = self.create_input(f, "Nome de Usuário", "")
        self.ent_reg_password = self.create_input(f, "Senha", "", is_pass=True)
        self.ent_reg_confirm = self.create_input(f, "Confirmar Senha", "", is_pass=True)
        self.ent_reg_confirm.bind("<Return>", lambda e: self.do_register_inline())
        
        self.btn_reg_action = RoundedButton(f, "CRIAR CONTA", self.do_register_inline, width=300, bg=Theme.SUCCESS)
        self.btn_reg_action.pack(pady=15)
        self.lbl_msg = tk.Label(f, text="", bg=Theme.BG_DARK, fg=Theme.ERROR, wraplength=300)
        self.lbl_msg.pack()
    
    def do_register_inline(self):
        """Handle inline registration"""
        # Validations
        if not all([self.ent_reg_fullname.get(), self.ent_reg_email.get(), 
                   self.ent_reg_username.get(), self.ent_reg_password.get()]):
            self.lbl_msg.config(text="❌ Preencha todos os campos!", fg=Theme.ERROR)
            return
        
        if len(self.ent_reg_username.get()) < 3:
            self.lbl_msg.config(text="❌ Usuário deve ter no mínimo 3 caracteres", fg=Theme.ERROR)
            return
        
        if len(self.ent_reg_password.get()) < 6:
            self.lbl_msg.config(text="❌ Senha deve ter no mínimo 6 caracteres", fg=Theme.ERROR)
            return
        
        if self.ent_reg_password.get() != self.ent_reg_confirm.get():
            self.lbl_msg.config(text="❌ As senhas não coincidem!", fg=Theme.ERROR)
            return
        
        if "@" not in self.ent_reg_email.get():
            self.lbl_msg.config(text="❌ Email inválido!", fg=Theme.ERROR)
            return
        
        # API call
        def _thread():
            try:
                # Usa o servidor salvo/descoberto na tela de login
                srv = self._saved_srv
                if hasattr(self, 'ent_srv') and self.ent_srv.winfo_exists():
                    srv = self.ent_srv.get().strip()
                
                if srv == "Mirror.ia Server" and hasattr(self, '_real_server_ip'):
                    srv = self._real_server_ip
                elif not srv.startswith("http"):
                    srv = f"http://{srv}"
                
                payload = {
                    "username": self.ent_reg_username.get(),
                    "password": self.ent_reg_password.get(),
                    "full_name": self.ent_reg_fullname.get(),
                    "email": self.ent_reg_email.get()
                }
                
                r = requests.post(f"{srv.rstrip('/')}/register", json=payload, timeout=5)
                
                if r.status_code == 200:
                    self.after(0, lambda: self.lbl_msg.config(
                        text="✅ Conta criada! Aguarde aprovação do administrador.", 
                        fg=Theme.SUCCESS))
                    # Clear fields
                    self.after(2000, lambda: self._switch_mode(True))  # Back to login after 2s
                else:
                    error_msg = r.json().get('detail', 'Erro desconhecido')
                    self.after(0, lambda msg=error_msg: self.lbl_msg.config(text=f"❌ {msg}", fg=Theme.ERROR))
            except Exception as e:
                self.after(0, lambda err=str(e): self.lbl_msg.config(text=f"❌ Erro: {err[:50]}", fg=Theme.ERROR))
        
        threading.Thread(target=_thread, daemon=True).start()
    
    def _show_changelog(self):
        """Mostra janela com changelog"""
        try:
            from version import VERSION, CHANGELOG
            
            changelog_win = tk.Toplevel(self)
            changelog_win.title("Novidades - Mirror.ia")
            changelog_win.geometry("600x500")
            changelog_win.configure(bg=Theme.BG_DARK)
            changelog_win.transient(self)
            
            # Center window
            changelog_win.update_idletasks()
            x = (changelog_win.winfo_screenwidth() // 2) - (600 // 2)
            y = (changelog_win.winfo_screenheight() // 2) - (500 // 2)
            changelog_win.geometry(f"600x500+{x}+{y}")
            
            try:
                changelog_win.iconbitmap("icon.ico")
            except:
                pass
            
            # Header
            header = tk.Frame(changelog_win, bg=Theme.BG_CARD, pady=20)
            header.pack(fill="x")
            tk.Label(header, text=f"Mirror.ia v{VERSION}", font=("Segoe UI", 18, "bold"), 
                    bg=Theme.BG_CARD, fg=Theme.ACCENT).pack()
            tk.Label(header, text="Histórico de Alterações", font=("Segoe UI", 10), 
                    bg=Theme.BG_CARD, fg=Theme.FG_SECONDARY).pack(pady=(5, 0))
            
            # Scrollable text
            text_frame = tk.Frame(changelog_win, bg=Theme.BG_DARK)
            text_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side="right", fill="y")
            
            text_widget = tk.Text(text_frame, wrap="word", bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY,
                                 font=("Segoe UI", 10), yscrollcommand=scrollbar.set,
                                 relief="flat", padx=15, pady=15)
            text_widget.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=text_widget.yview)
            
            text_widget.insert("1.0", CHANGELOG)
            text_widget.config(state="disabled")
            
            # Close button
            RoundedButton(changelog_win, "FECHAR", changelog_win.destroy, width=150, bg=Theme.ACCENT).pack(pady=15)
            
        except Exception as e:
            messagebox.showinfo("Changelog", f"Mirror.ia v{VERSION}\n\nVersão atual do sistema.")


    def create_input(self, parent, label, default, is_pass=False):
        parent_bg = parent.cget("bg")
        tk.Label(parent, text=label.upper(), bg=parent_bg, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", pady=(5, 3))
        ent = ttk.Entry(parent, style="Modern.TEntry", show="•" if is_pass else "", width=40)
        ent.pack(fill="x", ipadx=5, ipady=5)
        if default: 
            ent.insert(0, default)
            # Centralizar se for "Mirror.ia Server"
            if default == "Mirror.ia Server":
                ent.configure(justify="center")
        return ent

    def auto_discover_ip(self, silent=False):
        """Tenta descobrir automaticamente o IP do servidor
        
        Args:
            silent: Se True, não mostra status "Buscando..." (para auto-discover no startup)
        """
        if not silent:
            self.discover_status.config(text="Buscando...", fg=Theme.ACCENT)
        
        # Indica visualmente que está trabalhando
        self.btn_action.disable("BUSCANDO IP...")
        
        def _thread():
            try:
                # Opção 1: Tentar último servidor conhecido
                last_server = self.ent_srv.get()
                if last_server and last_server != "http://localhost:8000":
                    try:
                        # Tenta pegar IP do endpoint
                        if not last_server.startswith("http"):
                            last_server = f"http://{last_server}"
                        
                        r = requests.get(f"{last_server.rstrip('/')}/api/public-ip", timeout=3)
                        if r.status_code == 200:
                            new_ip = r.text.strip()
                            new_server = f"http://{new_ip}:8000"
                            self.after(0, lambda: self.ent_srv.delete(0, "end"))
                            self.after(0, lambda: self.ent_srv.insert(0, new_server))
                            self.after(0, lambda: self.discover_status.config(
                                text=f"✓ IP atualizado!", fg=Theme.SUCCESS))
                            return
                    except:
                        pass
                
                # Opção 2: Tentar arquivo estático em servidor conhecido
                known_servers = [
                    last_server,
                    "http://192.168.15.2:8000",
                    "http://192.168.1.2:8000"
                ]
                
                for server in known_servers:
                    if not server:
                        continue
                    try:
                        if not server.startswith("http"):
                            server = f"http://{server}"
                        
                        r = requests.get(f"{server.rstrip('/')}/static/current_ip.txt", timeout=2)
                        if r.status_code == 200:
                            new_ip = r.text.strip()
                            new_server = f"http://{new_ip}:8000"
                            self.after(0, lambda: self.ent_srv.delete(0, "end"))
                            self.after(0, lambda: self.ent_srv.insert(0, new_server))
                            self.after(0, lambda: self.discover_status.config(
                                text=f"✓ IP encontrado!", fg=Theme.SUCCESS))
                            
                            # Dispara verificação para habilitar botão
                            threading.Thread(target=self._check_connection_thread, args=(new_server,), daemon=True).start()
                            return
                    except:
                        continue
                
                # Opção 3: Buscar IP diretamente em URLs públicas conhecidas de Dpaste
                # Esta é a chave: tentamos URLs conhecidas DIRETAMENTE, sem precisar do servidor
                dpaste_urls = [
                    "https://dpaste.com/8SV8XNVGQ.txt",  # URL atual conhecida
                    # Adicionar outras URLs se criar novos pastes
                ]
                
                for paste_url in dpaste_urls:
                    try:
                        r = requests.get(paste_url, timeout=5)
                        if r.status_code == 200:
                            try:
                                data = json.loads(r.text)
                                new_ip = data.get("ip", "").strip()
                                if new_ip:
                                    # Guarda o IP real internamente
                                    self._real_server_ip = f"http://{new_ip}:8000"
                                    
                            # Mostra nome amigável ao usuário
                                    self.after(0, lambda: self.ent_srv.delete(0, "end"))
                                    self.after(0, lambda: self.ent_srv.insert(0, "Mirror.ia Server"))
                                    self.after(0, lambda: self.ent_srv.configure(justify="center")) # FIX: Center text
                                    self._saved_srv = "Mirror.ia Server" # FIX: Persist for Register tab
                                    
                                    self.after(0, lambda: self.discover_status.config(
                                        text=f"✓ Conectado!", fg=Theme.SUCCESS))
                                    
                                    # Dispara verificação para habilitar botão
                                    threading.Thread(target=self._check_connection_thread, args=(self._real_server_ip,), daemon=True).start()
                                    return
                            except:
                                pass
                    except:
                        continue
                
                # Opção 4: Tentar buscar URL do paste do servidor local (se estiver na mesma rede)
                try:
                    for server in known_servers:
                        if not server:
                            continue
                        try:
                            # Busca URL do Dpaste salva no servidor
                            r = requests.get(f"{server.rstrip('/')}/static/paste_raw_url.txt", timeout=2)
                            if r.status_code == 200:
                                paste_url = r.text.strip()
                                
                                # Busca IP do Dpaste
                                r2 = requests.get(paste_url, timeout=5)
                                if r2.status_code == 200:
                                    data = json.loads(r2.text)
                                    new_ip = data.get("ip", "").strip()
                                    if new_ip:
                                        new_server = f"http://{new_ip}:8000"
                                        self.after(0, lambda s=new_server: self.ent_srv.delete(0, "end"))
                                        self.after(0, lambda s=new_server: self.ent_srv.insert(0, s))
                                        self.after(0, lambda: self.discover_status.config(
                                            text=f"✓ IP atualizado!", fg=Theme.SUCCESS))
                                        
                                        # Dispara verificação para habilitar botão
                                        threading.Thread(target=self._check_connection_thread, args=(new_server,), daemon=True).start()
                                        return
                        except:
                            continue
                except:
                    pass
                
                # Opção 5: GitHub Gist (se URL conhecida)
                # TODO: Implementar busca em Gist se necessário
                
                self.after(0, lambda: self.discover_status.config(
                    text="✗ Não encontrado", fg=Theme.ERROR))
                
                # Falha total no discovery: libera botão para tentativa manual ou re-check
                self.after(0, lambda: self.btn_action.enable("VERIFICAR CONEXÃO"))
                def _retry_disc():
                    self.auto_discover_ip()
                self.after(0, lambda: setattr(self.btn_action, 'command', _retry_disc))
                
            except Exception as e:
                self.after(0, lambda: self.discover_status.config(
                    text=f"✗ Erro", fg=Theme.ERROR))
                # Garante que botão seja liberado mesmo em erro fatal
                self.after(0, lambda: self.btn_action.enable("VERIFICAR CONEXÃO"))
        
        threading.Thread(target=_thread, daemon=True).start()


    def do_login(self):
        srv = self.ent_srv.get().strip()
        
        # Se usuário deixou "Mirror.ia Server", usa o IP real guardado
        if srv == "Mirror.ia Server" and hasattr(self, '_real_server_ip'):
            srv = self._real_server_ip
        elif not srv.startswith("http"): 
            srv = f"http://{srv}"
            
        self.api_url = srv.rstrip("/")
        
        def _thread():
            try:
                r = requests.post(f"{self.api_url}/token", data={"username": self.ent_usr.get(), "password": self.ent_pwd.get()}, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    self.token = data['access_token']
                    self.is_admin = data.get('is_admin', False)
                    self.user_info = {'sub': data.get('username', 'User')}
                    
                    # Save Config Logic
                    import json
                    if self.var_save.get():
                        with open("config.json", "w") as cf:
                            json.dump({
                                "server": self.ent_srv.get(),
                                "user": self.ent_usr.get(),
                                "password": self.ent_pwd.get()
                            }, cf)
                    else:
                        if os.path.exists("config.json"): os.remove("config.json")

                    self.after(0, self.setup_main_interface)
                else:
                    self.after(0, lambda: self.lbl_msg.config(text="Credenciais inválidas"))
            except Exception as e:
                self.after(0, lambda: self.lbl_msg.config(text=f"Erro: {e}"))
        threading.Thread(target=_thread, daemon=True).start()

    def show_register(self):
        """Mostra janela de cadastro de novo usuário"""
        w = tk.Toplevel(self)
        w.title("Criar Nova Conta - Mirror.ia")
        w.geometry("450x550")
        w.configure(bg=Theme.BG_DARK)
        w.resizable(False, False)
        
        # Center window
        w.update_idletasks()
        x = (w.winfo_screenwidth() // 2) - (450 // 2)
        y = (w.winfo_screenheight() // 2) - (550 // 2)
        w.geometry(f"450x550+{x}+{y}")
        
        try:
            if os.path.exists("icon.ico"):
                w.iconbitmap("icon.ico")
        except:
            pass
        
        # Header
        header = tk.Frame(w, bg=Theme.BG_CARD, pady=20)
        header.pack(fill="x")
        tk.Label(header, text="Criar Nova Conta", font=("Segoe UI", 18, "bold"), bg=Theme.BG_CARD, fg=Theme.ACCENT).pack()
        tk.Label(header, text="Preencha os dados abaixo", font=("Segoe UI", 10), bg=Theme.BG_CARD, fg=Theme.FG_SECONDARY).pack(pady=(5, 0))
        
        # Form
        form = tk.Frame(w, bg=Theme.BG_DARK, padx=40, pady=20)
        form.pack(fill="both", expand=True)
        
        def _entry(lbl, placeholder=""):
            tk.Label(form, text=lbl.upper(), bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(15, 5))
            e = ttk.Entry(form, style="Modern.TEntry", width=40)
            e.pack(fill="x", ipady=8)
            if placeholder:
                e.insert(0, placeholder)
            return e
        
        ent_fullname = _entry("Nome Completo", "João Silva")
        ent_email = _entry("Email", "joao@exemplo.com")
        ent_username = _entry("Nome de Usuário", "joao.silva")
        ent_password = _entry("Senha")
        ent_password.config(show="•")
        ent_confirm = _entry("Confirmar Senha")
        ent_confirm.config(show="•")
        
        # Status message
        msg_label = tk.Label(form, text="", bg=Theme.BG_DARK, fg=Theme.ERROR, wraplength=350)
        msg_label.pack(pady=(15, 0))
        
        def _register():
            # Validations
            if not all([ent_fullname.get(), ent_email.get(), ent_username.get(), ent_password.get()]):
                msg_label.config(text="❌ Preencha todos os campos!")
                return
            
            if len(ent_username.get()) < 3:
                msg_label.config(text="❌ Usuário deve ter no mínimo 3 caracteres")
                return
            
            if len(ent_password.get()) < 6:
                msg_label.config(text="❌ Senha deve ter no mínimo 6 caracteres")
                return
            
            if ent_password.get() != ent_confirm.get():
                msg_label.config(text="❌ As senhas não coincidem!")
                return
            
            if "@" not in ent_email.get():
                msg_label.config(text="❌ Email inválido!")
                return
            
            # API call
            def _thread():
                try:
                    srv = self.ent_srv.get() if hasattr(self, 'ent_srv') else self.api_url
                    if not srv.startswith("http"):
                        srv = f"http://{srv}"
                    
                    payload = {
                        "username": ent_username.get(),
                        "password": ent_password.get(),
                        "full_name": ent_fullname.get(),
                        "email": ent_email.get()
                    }
                    
                    r = requests.post(f"{srv.rstrip('/')}/register", json=payload, timeout=5)
                    
                    if r.status_code == 200:
                        self.after(0, lambda: messagebox.showinfo(
                            "Sucesso!", 
                            "✅ Conta criada com sucesso!\n\nAguarde a aprovação do administrador.\nVocê receberá um email quando sua conta for ativada.",
                            parent=w
                        ))
                        self.after(0, w.destroy)
                    else:
                        error_msg = r.json().get('detail', 'Erro desconhecido')
                        self.after(0, lambda: msg_label.config(text=f"❌ {error_msg}"))
                except Exception as e:
                    self.after(0, lambda: msg_label.config(text=f"❌ Erro: {str(e)[:50]}"))
            
            threading.Thread(target=_thread, daemon=True).start()
        
        # Buttons
        btn_frame = tk.Frame(form, bg=Theme.BG_DARK)
        btn_frame.pack(pady=(20, 0))
        
        RoundedButton(btn_frame, "CRIAR CONTA", _register, width=180, bg=Theme.ACCENT).pack(side="left", padx=5)
        RoundedButton(btn_frame, "CANCELAR", w.destroy, width=120, bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY).pack(side="left", padx=5)

    # --- Main ---
    def setup_main_interface(self):
        self.clear_window()
        self.title(f"Mirror.ia - {'ADMIN' if self.is_admin else 'USER'} ({self.user_info.get('sub')})")
        try: self.iconbitmap("icon.ico")
        except: pass
        
        self.container = tk.Frame(self, bg=Theme.BG_DARK)
        self.container.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.container, bg=Theme.BG_SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Content
        self.content = tk.Frame(self.container, bg=Theme.BG_DARK)
        self.content.pack(side="right", fill="both", expand=True, padx=30, pady=30)

        self.setup_navigation()
        self.poll_data()
        self.show_dashboard_view()

    def setup_navigation(self):
        tk.Label(self.sidebar, text="Mirror.ia", font=("Segoe UI", 18, "bold"), bg=Theme.BG_SIDEBAR, fg=Theme.ACCENT).pack(pady=(30, 40), padx=20, anchor="w")
        
        self._nav_btn("📊 Visão Geral", self.show_dashboard_view)
        if self.is_admin:
            self._nav_btn("⚙ Admin", self.show_admin_view)
        self._nav_btn("📄 Relatórios", self.show_reports_view)
        self._nav_btn("⌨ Terminal", self.show_terminal_view)
        
        tk.Button(self.sidebar, text="← Sair", command=self.show_login, bg=Theme.BG_SIDEBAR, fg=Theme.FG_SECONDARY, relief="flat").pack(side="bottom", pady=10)

        res_frame = tk.Frame(self.sidebar, bg=Theme.BG_SIDEBAR)

    def _nav_btn(self, text, cmd):
        # Create button with consistent left alignment
        btn = tk.Button(self.sidebar, text=text, command=cmd, bg=Theme.BG_SIDEBAR, fg=Theme.FG_PRIMARY, 
                        bd=0, activebackground=Theme.BG_HOVER, activeforeground=Theme.ACCENT, 
                        font=("Segoe UI", 11), anchor="w", padx=20, pady=8)
        btn.pack(fill="x", pady=2, padx=0)

    # --- Views ---
    def show_dashboard_view(self):
        self._clear_content()
        h = tk.Frame(self.content, bg=Theme.BG_DARK); h.pack(fill="x", pady=(0, 20))
        tk.Label(h, text="Mirror.ia  |  Visão Geral", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(side="left")
        
        RoundedButton(h, "ATUALIZAR", self.fetch_now, width=120, bg=Theme.BG_CARD).pack(side="right", padx=10)
        RoundedButton(h, "NOVA TRANSCRIÇÃO", self.do_upload, width=200, bg="#61afef").pack(side="right")
        
        # Stats Cards
        f_stats = tk.Frame(self.content, bg=Theme.BG_DARK); f_stats.pack(fill="x", pady=(0, 20))
        
        def _card(parent, title, key, color):
            c = ttk.Frame(parent, style="Card.TFrame", padding=20)
            c.pack(side="left", fill="both", expand=True, padx=5)
            tk.Label(c, text=title.upper(), font=("Segoe UI", 8, "bold"), bg=Theme.BG_CARD, fg="#abb2bf").pack(anchor="w")
            l = tk.Label(c, text="0", font=("Segoe UI", 24, "bold"), bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY)
            l.pack(anchor="w")
            self.res_labels[key] = l
            tk.Frame(c, bg=color, height=2).pack(fill="x", pady=(10, 0))
            return c

        _card(f_stats, "Total", "total", "#c678dd")
        _card(f_stats, "Processando", "processing", "#61afef")
        _card(f_stats, "Concluídos", "completed", "#98c379")
        _card(f_stats, "Falhas", "failed", "#e06c75")

        self.create_table(self.content)
        self.fetch_now()

    def show_admin_view(self):
        self._clear_content()
        h = tk.Frame(self.content, bg=Theme.BG_DARK); h.pack(fill="x", pady=(0, 20))
        tk.Label(h, text="Mirror.ia  |  Admin Console", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(side="left")

        # Tabs
        style = ttk.Style()
        style.configure("TNotebook", background=Theme.BG_DARK, borderwidth=0)
        nb = ttk.Notebook(self.content); nb.pack(fill="both", expand=True)

        self.setup_users_tab(nb)
        nb.add(self.users_tab, text="  Usuários  ")
        
        self.setup_system_tab(nb)
        nb.add(self.system_tab, text="  Sistema  ")
        
    def setup_users_tab(self, parent):
        self.users_tab = tk.Frame(parent, bg=Theme.BG_DARK) # Keep reference
        top = tk.Frame(self.users_tab, bg=Theme.BG_DARK); top.pack(fill="x", pady=20)
        
        def _reload_users():
            for i in tree.get_children(): tree.delete(i)
            def _get():
                try:
                    r = requests.get(f"{self.api_url}/api/admin/users", headers={"Authorization": f"Bearer {self.token}"})
                    if r.status_code==200:
                        for u in r.json():
                            tree.insert("","end",values=(u['username'], u['email'], "ADMIN" if u['is_admin'] else "User", "ATIVO" if u['is_active'] else "INATIVO", u['id'], u.get('transcription_limit',0)))
                except: pass
            threading.Thread(target=_get, daemon=True).start()

        def _action(act):
            sel = tree.selection()
            if not sel: return
            uid = tree.item(sel[0])['values'][4]
            url = f"{self.api_url}/api/admin/" + ("approve/" if act == "Aprovar" else "user/") + uid
            try:
                if act == "Deletar": requests.delete(url, headers={"Authorization": f"Bearer {self.token}"})
                else: requests.post(url, headers={"Authorization": f"Bearer {self.token}"})
                _reload_users()
            except Exception as e: messagebox.showerror("Erro", str(e))

        def _edit_user():
            sel = tree.selection()
            if not sel: return
            vals = tree.item(sel[0])['values']
            uid, curr_limit = vals[4], vals[5]
            
            w = tk.Toplevel(self); w.title(f"Editar: {vals[0]}"); w.geometry("400x500"); w.configure(bg=Theme.BG_DARK)
            
            def _entry(lbl, val=""):
                tk.Label(w, text=lbl, bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(pady=(15,5), anchor="w", padx=40)
                e = ttk.Entry(w, width=30); e.pack(); e.insert(0, str(val)); return e
            
            ent_lim = _entry("Limite (min/mês):", curr_limit)
            ent_usr = _entry("Novo Login (Opcional):")
            ent_pwd = _entry("Nova Senha (Opcional):"); ent_pwd.config(show="•")
            
            def _save():
                try:
                    # Update Limit
                    requests.post(f"{self.api_url}/api/admin/user/{uid}/limit", json={"limit": int(ent_lim.get())}, headers={"Authorization": f"Bearer {self.token}"})
                    # Update Creds
                    p = {}
                    if ent_usr.get(): p["username"] = ent_usr.get()
                    if ent_pwd.get(): p["password"] = ent_pwd.get()
                    if p: requests.post(f"{self.api_url}/api/admin/user/{uid}/update", json=p, headers={"Authorization": f"Bearer {self.token}"})
                    
                    messagebox.showinfo("Sucesso", "Atualizado!"); w.destroy(); _reload_users()
                except Exception as e: messagebox.showerror("Erro", str(e))
                
            RoundedButton(w, "SALVAR", _save, width=200, bg=Theme.ACCENT).pack(pady=30)

        def _new_user():
            w = tk.Toplevel(self); w.title("Novo Membro"); w.geometry("400x450"); w.configure(bg=Theme.BG_DARK)
            
            def _entry(lbl, val=""):
                tk.Label(w, text=lbl, bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(pady=(15,5), anchor="w", padx=40)
                e = ttk.Entry(w, width=30); e.pack(); e.insert(0, str(val)); return e

            ent_usr = _entry("Usuário:")
            ent_pwd = _entry("Senha:"); ent_pwd.config(show="•")
            ent_lim = _entry("Limite (min/mês):", "30")

            def _create():
                try:
                    p = {"username": ent_usr.get(), "password": ent_pwd.get(), "limit": int(ent_lim.get())}
                    if len(p["username"]) < 3 or len(p["password"]) < 6: return messagebox.showerror("Erro", "Usuário min 3 chars, Senha min 6 chars.")
                    
                    r = requests.post(f"{self.api_url}/api/admin/users/create", json=p, headers={"Authorization": f"Bearer {self.token}"})
                    if r.status_code == 200: messagebox.showinfo("Sucesso", "Usuário criado!"); w.destroy(); _reload_users()
                    else: messagebox.showerror("Erro", r.json().get('detail', 'Erro ao criar'))
                except Exception as e: messagebox.showerror("Erro", str(e))

            RoundedButton(w, "CRIAR USUÁRIO", _create, width=200, bg=Theme.ACCENT).pack(pady=30)

        # Toolbar - NO REFRESH BUTTON
        bar = tk.Frame(self.users_tab, bg=Theme.BG_DARK); bar.pack(fill="x", pady=(0, 15))
        RoundedButton(bar, "➕ Novo Membro", _new_user, width=140, bg=Theme.ACCENT).pack(side="left", padx=5)
        
        RoundedButton(bar, "🗑️ Excluir", lambda: _action("Deletar"), width=100, bg="#2c313a", fg="#e06c75").pack(side="right", padx=5)
        RoundedButton(bar, "✏️ Editar", _edit_user, width=100, bg="#2c313a", fg="#61afef").pack(side="right", padx=5)
        RoundedButton(bar, "✅ Aprovar", lambda: _action("Aprovar"), width=100, bg="#2c313a", fg="#98c379").pack(side="right", padx=5)

        cols = ("User", "Email", "Role", "Status", "ID"); tree = ttk.Treeview(self.users_tab, columns=cols, show="headings")
        tree.heading("User", text="Usuário"); tree.column("User", width=150)
        tree.heading("Email", text="Email"); tree.column("Email", width=250)
        tree.heading("Role", text="Role"); tree.column("Role", width=80)
        tree.heading("Status", text="Status"); tree.column("Status", width=80)
        tree.column("ID", width=0, stretch=False)
        tree.pack(fill="both", expand=True)
        _reload_users()

    def setup_system_tab(self, parent):
        self.system_tab = tk.Frame(parent, bg=Theme.BG_DARK) # Keep reference
        f = tk.Frame(self.system_tab, bg=Theme.BG_DARK); f.pack(fill="both", expand=True, pady=30, padx=30)
        
        # Combined Cache Button
        def _clear_all_caches():
            urls = ["/api/history/clear", "/api/admin/cache/clear", "/api/admin/diarization/cache/clear"]
            for u in urls:
                try: requests.post(f"{self.api_url}{u}", headers={"Authorization": f"Bearer {self.token}"})
                except: pass
            messagebox.showinfo("Sistema", "Limpeza completa solicitada.")

        def _regen():
            try: requests.post(f"{self.api_url}/api/admin/regenerate-all", headers={"Authorization": f"Bearer {self.token}"}); messagebox.showinfo("Sistema", "Regeneração iniciada.")
            except: pass

        RoundedButton(f, "🧹 LIMPAR TODOS CACHES (GERAL/REDIS/DIAR)", _clear_all_caches, width=400, bg=Theme.WARNING).pack(pady=20)
        RoundedButton(f, "⚡ REGENERAR ANÁLISES", _regen, width=400, bg=Theme.ACCENT).pack(pady=20)

    def show_terminal_view(self):
        self._clear_content()
        h = tk.Frame(self.content, bg=Theme.BG_DARK); h.pack(fill="x", pady=(0,10))
        tk.Label(h, text="Mirror.ia  |  Logs", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(side="left")
        
        def _clear_logs():
            self.term_text.delete("1.0", "end")
            
        def _restart_docker():
            if messagebox.askyesno("Confirmar", "Tem certeza que deseja REINICIAR o sistema? Todos os serviços serão interrompidos por alguns segundos."):
                import subprocess
                try:
                    subprocess.Popen("docker-compose restart", shell=True)
                    messagebox.showinfo("Iniciado", "Comando de restart enviado.")
                except Exception as e:
                    messagebox.showerror("Erro", str(e))

        RoundedButton(h, "REINICIAR SISTEMA", _restart_docker, width=160, bg=Theme.ERROR).pack(side="right", padx=5)
        RoundedButton(h, "LIMPAR TERMINAL", _clear_logs, width=140, bg=Theme.BG_CARD).pack(side="right", padx=5)
        
        self.term_text = tk.Text(self.content, bg="#0e1012", fg="#98c379", font=("Consolas", 10), padx=10, pady=10); self.term_text.pack(fill="both", expand=True)
        self._fetch_logs()

    def show_reports_view(self):
        self._clear_content()
        h = tk.Frame(self.content, bg=Theme.BG_DARK); h.pack(fill="x", pady=(0, 20))
        tk.Label(h, text="Mirror.ia  |  Relatórios", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(side="left")

        f = tk.Frame(self.content, bg=Theme.BG_CARD, padx=30, pady=30); f.pack(fill="x")
        tk.Label(f, text="Exportação Simplificada", font=("Segoe UI", 12, "bold"), bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor="w", pady=(0,10))
        
        tk.Label(f, text="O relatório contém apenas: Nome do Arquivo e Resultado da Análise.", 
                 bg=Theme.BG_CARD, fg=Theme.FG_SECONDARY, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 30))

        def _dl():
            try:
                # No filters, fetch everything
                r = requests.get(f"{self.api_url}/api/export", headers={"Authorization": f"Bearer {self.token}"}, stream=True)
                if r.status_code == 200:
                    fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
                    if fp: 
                        with open(fp, 'wb') as f: 
                            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                        messagebox.showinfo("Sucesso", "Relatório simplificado salvo!"); 
                        try: os.startfile(os.path.dirname(fp))
                        except: pass
                else: messagebox.showerror("Erro", f"Erro: {r.status_code}")
            except Exception as e: messagebox.showerror("Erro", str(e))

        RoundedButton(f, "BAIXAR RELATÓRIO SIMPLIFICADO", _dl, width=280, bg=Theme.ACCENT).pack(pady=10)
        res_frame.pack(side="bottom", fill="x", padx=15, pady=20)
        tk.Label(res_frame, text="RECURSOS", bg=Theme.BG_SIDEBAR, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 10))
        
        for res in ["CPU", "RAM", "GPU"]:
            row = tk.Frame(res_frame, bg=Theme.BG_SIDEBAR)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=res, width=5, bg=Theme.BG_SIDEBAR, fg=Theme.FG_PRIMARY, anchor="w", font=("Segoe UI", 8)).pack(side="left")
            val_lbl = tk.Label(row, text="0%", bg=Theme.BG_SIDEBAR, fg=Theme.ACCENT, font=("Segoe UI", 8, "bold"))
            val_lbl.pack(side="right")
            self.res_labels[res] = val_lbl
            
            bg = tk.Frame(row, bg="#181a1f", height=4)
            bg.pack(fill="x", pady=(2,0))
            fill = tk.Frame(bg, bg=Theme.ACCENT, height=4, width=0)
            fill.pack(side="left")
            self.res_labels[f"{res}_bar"] = fill

    def _nav_btn(self, text, cmd):
        btn = tk.Button(self.sidebar, text=text, command=cmd, bg=Theme.BG_SIDEBAR, fg=Theme.FG_PRIMARY, activebackground=Theme.BG_HOVER, activeforeground=Theme.ACCENT, font=("Segoe UI", 11), bd=0, relief="flat", padx=20, pady=12, anchor="w")
        btn.pack(fill="x")

    def _clear_content(self):
        for w in self.content.winfo_children(): w.destroy()
    def clear_window(self):
        for w in self.winfo_children(): w.destroy()

    # --- Views ---
    def show_dashboard_view(self):
        self._clear_content()
        # Header
        h = tk.Frame(self.content, bg=Theme.BG_DARK)
        h.pack(fill="x", pady=(0, 20))
        tk.Label(h, text="Mirror.ia  |  Visão Geral", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(side="left")
        
        btn_frame = tk.Frame(h, bg=Theme.BG_DARK)
        btn_frame.pack(side="right")
        RoundedButton(btn_frame, "NOVA TRANSCRIÇÃO", self.do_upload, width=180).pack(side="right", padx=5)
        RoundedButton(btn_frame, "ATUALIZAR", self.fetch_now, width=120, bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY).pack(side="right", padx=5)

        # KPIs
        card_row = tk.Frame(self.content, bg=Theme.BG_DARK)
        card_row.pack(fill="x", pady=(0, 25))
        self.lbl_stats_total = self.create_stat_card(card_row, "Total", "0", 0)
        self.lbl_stats_proc  = self.create_stat_card(card_row, "Processando", "0", 1)
        self.lbl_stats_done  = self.create_stat_card(card_row, "Concluídos", "0", 2)
        self.lbl_stats_fail  = self.create_stat_card(card_row, "Falhas", "0", 3)
        
        # Filters Bar
        f_bar = tk.Frame(self.content, bg=Theme.BG_DARK)
        f_bar.pack(fill="x", pady=(0, 10))
        
        # Search
        tk.Label(f_bar, text="BUSCAR:", bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0,5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_table())
        e_search = ttk.Entry(f_bar, textvariable=self.search_var, style="Modern.TEntry", width=30)
        e_search.pack(side="left", padx=(0, 20))
        
        # Status Filter
        tk.Label(f_bar, text="STATUS:", bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0,5))
        self.filter_status_var = tk.StringVar(value="Todos")
        cb_status = ttk.Combobox(f_bar, textvariable=self.filter_status_var, values=["Todos", "Ativos", "Concluídos", "Falhas"], state="readonly", width=15)
        cb_status.pack(side="left", padx=(0, 20))
        cb_status.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())
        
        # Sort
        tk.Label(f_bar, text="ORDENAR:", bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0,5))
        self.sort_var = tk.StringVar(value="Data (Novos)")
        cb_sort = ttk.Combobox(f_bar, textvariable=self.sort_var, values=["Data (Novos)", "Data (Antigos)", "Nome (A-Z)", "Nome (Z-A)"], state="readonly", width=15)
        cb_sort.pack(side="left")
        cb_sort.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())
        
        self.create_table(self.content)
        if self.tasks: self.refresh_table()

    def show_admin_view(self):
        self._clear_content()
        tk.Label(self.content, text="Mirror.ia  |  Administração", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(anchor="w", pady=(0, 20))
        nb = ttk.Notebook(self.content); nb.pack(fill="both", expand=True)
        t_users = ttk.Frame(nb); nb.add(t_users, text=" Membros "); self.setup_users_tab(t_users)
        t_sys = ttk.Frame(nb); nb.add(t_sys, text=" Sistema "); self.setup_system_tab(t_sys)

    def setup_users_tab(self, parent):
        top = tk.Frame(parent, bg=Theme.BG_DARK); top.pack(fill="x", pady=20)
        
        def _reload_users():
            for i in tree.get_children(): tree.delete(i)
            def _get():
                try:
                    r = requests.get(f"{self.api_url}/api/admin/users", headers={"Authorization": f"Bearer {self.token}"})
                    if r.status_code==200:
                        for u in r.json():
                            tree.insert("","end",values=(u['username'], u['email'], "ADMIN" if u['is_admin'] else "User", "ATIVO" if u['is_active'] else "INATIVO", u['id'], u.get('transcription_limit',0)))
                except: pass
            threading.Thread(target=_get, daemon=True).start()

        def _action(act):
            sel = tree.selection()
            if not sel: return
            vals = tree.item(sel[0])['values']
            username = vals[0]
            uid = vals[4]
            
            # Proteção: Não permitir deletar o admin
            if act == "Deletar" and username.lower() == "admin":
                messagebox.showerror("Erro", "❌ O usuário 'admin' não pode ser excluído!")
                return
            
            url = f"{self.api_url}/api/admin/" + ("approve/" if act == "Aprovar" else "user/") + uid
            try:
                if act == "Deletar": requests.delete(url, headers={"Authorization": f"Bearer {self.token}"})
                else: requests.post(url, headers={"Authorization": f"Bearer {self.token}"})
                _reload_users()
            except Exception as e: messagebox.showerror("Erro", str(e))

        def _edit_user():
            sel = tree.selection()
            if not sel: return
            vals = tree.item(sel[0])['values']
            uid, curr_limit = vals[4], vals[5]
            
            w = tk.Toplevel(self); w.title(f"Editar: {vals[0]}"); w.geometry("400x500"); w.configure(bg=Theme.BG_DARK)
            
            def _entry(lbl, val=""):
                tk.Label(w, text=lbl, bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(pady=(15,5), anchor="w", padx=40)
                e = ttk.Entry(w, width=30); e.pack(); e.insert(0, str(val)); return e
            
            ent_lim = _entry("Limite (min/mês):", curr_limit)
            ent_usr = _entry("Novo Login (Opcional):")
            ent_pwd = _entry("Nova Senha (Opcional):"); ent_pwd.config(show="•")
            
            def _save():
                try:
                    # Update Limit
                    requests.post(f"{self.api_url}/api/admin/user/{uid}/limit", json={"limit": int(ent_lim.get())}, headers={"Authorization": f"Bearer {self.token}"})
                    # Update Creds
                    p = {}
                    if ent_usr.get(): p["username"] = ent_usr.get()
                    if ent_pwd.get(): p["password"] = ent_pwd.get()
                    if p: requests.post(f"{self.api_url}/api/admin/user/{uid}/update", json=p, headers={"Authorization": f"Bearer {self.token}"})
                    
                    messagebox.showinfo("Sucesso", "Atualizado!"); w.destroy(); _reload_users()
                except Exception as e: messagebox.showerror("Erro", str(e))
                
            RoundedButton(w, "SALVAR", _save, width=200, bg=Theme.ACCENT).pack(pady=30)

        def _new_user():
            w = tk.Toplevel(self); w.title("Novo Membro"); w.geometry("400x450"); w.configure(bg=Theme.BG_DARK)
            
            def _entry(lbl, val=""):
                tk.Label(w, text=lbl, bg=Theme.BG_DARK, fg=Theme.FG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(pady=(15,5), anchor="w", padx=40)
                e = ttk.Entry(w, width=30); e.pack(); e.insert(0, str(val)); return e

            ent_usr = _entry("Usuário:")
            ent_pwd = _entry("Senha:"); ent_pwd.config(show="•")
            ent_lim = _entry("Limite (min/mês):", "30")

            def _create():
                try:
                    p = {"username": ent_usr.get(), "password": ent_pwd.get(), "limit": int(ent_lim.get())}
                    if len(p["username"]) < 3 or len(p["password"]) < 6: return messagebox.showerror("Erro", "Usuário min 3 chars, Senha min 6 chars.")
                    
                    r = requests.post(f"{self.api_url}/api/admin/users/create", json=p, headers={"Authorization": f"Bearer {self.token}"})
                    if r.status_code == 200: messagebox.showinfo("Sucesso", "Usuário criado!"); w.destroy(); _reload_users()
                    else: messagebox.showerror("Erro", r.json().get('detail', 'Erro ao criar'))
                except Exception as e: messagebox.showerror("Erro", str(e))

            RoundedButton(w, "CRIAR USUÁRIO", _create, width=200, bg=Theme.ACCENT).pack(pady=30)

        def _toggle_admin():
            sel = tree.selection()
            if not sel: return
            vals = tree.item(sel[0])['values']
            uid = vals[4]
            current_role = vals[2] # "ADMIN" or "User"
            username = vals[0]
            
            if username.lower() == "admin":
                 messagebox.showerror("Erro", "O status do super-admin principal não pode ser alterado.")
                 return

            new_status = False if current_role == "ADMIN" else True
            action_name = "Remover Admin" if current_role == "ADMIN" else "Promover a Admin"
            
            if messagebox.askyesno("Confirmar", f"Deseja realmente {action_name} o usuário {username}?"):
                try:
                    requests.post(f"{self.api_url}/api/admin/user/{uid}/update", json={"is_admin": new_status}, headers={"Authorization": f"Bearer {self.token}"})
                    messagebox.showinfo("Sucesso", "Permissões atualizadas com sucesso!")
                    _reload_users()
                except Exception as e:
                    messagebox.showerror("Erro", str(e))

        # Toolbar - NO REFRESH BUTTON
        bar = tk.Frame(parent, bg=Theme.BG_DARK); bar.pack(fill="x", pady=(0, 15))
        RoundedButton(bar, "➕ Novo Membro", _new_user, width=140, bg=Theme.ACCENT).pack(side="left", padx=5)
        
        RoundedButton(bar, "🗑️ Excluir", lambda: _action("Deletar"), width=100, bg="#2c313a", fg="#e06c75").pack(side="right", padx=5)
        RoundedButton(bar, "👑 Promover/Revogar", _toggle_admin, width=160, bg="#2c313a", fg="#e5c07b").pack(side="right", padx=5) # New Button
        RoundedButton(bar, "✏️ Editar", _edit_user, width=100, bg="#2c313a", fg="#61afef").pack(side="right", padx=5)
        RoundedButton(bar, "✅ Aprovar", lambda: _action("Aprovar"), width=100, bg="#2c313a", fg="#98c379").pack(side="right", padx=5)

        cols = ("User", "Email", "Role", "Status", "ID"); tree = ttk.Treeview(parent, columns=cols, show="headings")
        tree.heading("User", text="Usuário"); tree.column("User", width=150)
        tree.heading("Email", text="Email"); tree.column("Email", width=250)
        tree.heading("Role", text="Role"); tree.column("Role", width=80)
        tree.heading("Status", text="Status"); tree.column("Status", width=80)
        tree.column("ID", width=0, stretch=False)
        tree.pack(fill="both", expand=True)
        _reload_users()

    def setup_system_tab(self, parent):
        f = tk.Frame(parent, bg=Theme.BG_DARK); f.pack(fill="both", expand=True, pady=30, padx=30)
        
        # Combined Cache Button
        def _clear_all_caches():
            urls = ["/api/history/clear", "/api/admin/cache/clear", "/api/admin/diarization/cache/clear"]
            for u in urls:
                try: requests.post(f"{self.api_url}{u}", headers={"Authorization": f"Bearer {self.token}"})
                except: pass
            messagebox.showinfo("Sistema", "Limpeza completa solicitada.")

        def _regen():
            try: requests.post(f"{self.api_url}/api/admin/regenerate-all", headers={"Authorization": f"Bearer {self.token}"}); messagebox.showinfo("Sistema", "Regeneração iniciada.")
            except: pass

        RoundedButton(f, "🧹 LIMPAR TODOS CACHES (GERAL/REDIS/DIAR)", _clear_all_caches, width=400, bg=Theme.WARNING).pack(pady=20)
        RoundedButton(f, "⚡ REGENERAR ANÁLISES", _regen, width=400, bg=Theme.ACCENT).pack(pady=20)

    def show_terminal_view(self):
        self._clear_content()
        h = tk.Frame(self.content, bg=Theme.BG_DARK); h.pack(fill="x", pady=(0,10))
        tk.Label(h, text="Mirror.ia  |  Logs", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(side="left")
        
        def _clear_logs():
            self.term_text.delete("1.0", "end")
            
        def _restart_docker():
            if messagebox.askyesno("Confirmar", "Tem certeza que deseja REINICIAR o sistema? Todos os serviços serão interrompidos por alguns segundos."):
                import subprocess
                try:
                    subprocess.Popen("docker-compose restart", shell=True)
                    messagebox.showinfo("Iniciado", "Comando de restart enviado.")
                except Exception as e:
                    messagebox.showerror("Erro", str(e))

        RoundedButton(h, "REINICIAR SISTEMA", _restart_docker, width=160, bg=Theme.ERROR).pack(side="right", padx=5)
        RoundedButton(h, "LIMPAR TERMINAL", _clear_logs, width=140, bg=Theme.BG_CARD).pack(side="right", padx=5)
        
        self.term_text = tk.Text(self.content, bg="#0e1012", fg="#98c379", font=("Consolas", 10), padx=10, pady=10); self.term_text.pack(fill="both", expand=True)
        self._fetch_logs()

    def show_reports_view(self):
        self._clear_content()
        h = tk.Frame(self.content, bg=Theme.BG_DARK); h.pack(fill="x", pady=(0, 20))
        tk.Label(h, text="Mirror.ia  |  Relatórios", font=Theme.FONT_HEADER, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY).pack(side="left")

        f = tk.Frame(self.content, bg=Theme.BG_CARD, padx=30, pady=30); f.pack(fill="x")
        tk.Label(f, text="Exportação de Dados", font=("Segoe UI", 12, "bold"), bg=Theme.BG_CARD, fg=Theme.ACCENT).pack(anchor="w", pady=(0,10))
        
        tk.Label(f, text="O relatório conterá todas as transcrições e análises do sistema.", 
                 bg=Theme.BG_CARD, fg=Theme.FG_SECONDARY, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 30))

        def _dl():
            try:
                # No filters for full report
                r = requests.get(f"{self.api_url}/api/export", headers={"Authorization": f"Bearer {self.token}"}, stream=True)
                if r.status_code == 200:
                    fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
                    if fp: 
                        with open(fp, 'wb') as f: 
                            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                        messagebox.showinfo("Sucesso", "Relatório completo salvo!"); 
                        try: os.startfile(os.path.dirname(fp))
                        except: pass
                else: messagebox.showerror("Erro", f"Erro: {r.status_code}")
            except Exception as e: messagebox.showerror("Erro", str(e))

        RoundedButton(f, "BAIXAR RELATÓRIO COMPLETO (CSV)", _dl, width=280, bg=Theme.ACCENT).pack(pady=10)

    def _fetch_logs(self):
        def _get():
            try:
                r = requests.get(f"{self.api_url}/api/logs", headers={"Authorization": f"Bearer {self.token}"}, timeout=5)
                logs = "".join(r.json().get("logs", []))[-50000:]
                self.after(0, lambda: self.term_text.replace("1.0", "end", logs) if hasattr(self, 'term_text') else None)
            except: pass
        threading.Thread(target=_get, daemon=True).start()

    def clean_filename(self, filename):
        import re
        # Remove extension
        name = os.path.splitext(filename)[0]
        # Remove text inside parentheses (e.g., "(1)", "(Copy)")
        name = re.sub(r'\([^)]*\)', '', name)
        # Normalize spaces
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def show_details(self, data):
        # Use clean name (visual only)
        display_name = self.clean_filename(data['filename'])
        
        w = tk.Toplevel(self); w.title(f"Detalhes: {display_name}"); w.configure(bg=Theme.BG_DARK); w.geometry("1100x800")
        
        try:
            if os.path.exists("icon.png"):
                img = tk.PhotoImage(file="icon.png")
                w.iconphoto(False, img)
            elif os.path.exists("icon.ico"):
                w.iconbitmap("icon.ico")
        except: pass

        top = tk.Frame(w, bg=Theme.BG_CARD, padx=20, pady=20); top.pack(fill="x")
        # FIX: Changed to Entry to allow text selection
        title_entry = tk.Entry(top, font=Theme.FONT_HEADER, bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY, bd=0, highlightthickness=0, width=50)
        title_entry.pack(side="left")
        title_entry.insert(0, display_name)
        title_entry.config(state="readonly", readonlybackground=Theme.BG_CARD)
        
        ctrl = tk.Frame(top, bg=Theme.BG_CARD); ctrl.pack(side="right")
        curr = data.get('analysis_status')
        
        def _set_status(val):
            try:
                requests.post(f"{self.api_url}/api/task/{data['task_id']}/analysis", json={"status": val}, headers={"Authorization": f"Bearer {self.token}"})
                self.fetch_now()
                w.destroy()
            except: pass

        # Minimalist "Ghost" Buttons
        opts = [
            ("✔ PROCEDENTE", "#98c379", "Procedente"),
            ("✖ IMPROCEDENTE", "#e06c75", "Improcedente"),
            ("⚠ INDEFINIDO", "#e5c07b", "Indefinido"),
            ("⚪ OUTROS", "#c678dd", "Sem conclusão")
        ]
        
        for label, color, val in opts:
            is_active = (val == curr)
            
            # Active: Filled | Inactive: Text only (Cleaner)
            bg = color if is_active else Theme.BG_CARD
            fg = "#282c34" if is_active else "#abb2bf" 
            
            l = tk.Label(ctrl, text=label, font=("Segoe UI", 9, "bold"), bg=bg, fg=fg, padx=14, pady=6, cursor="hand2")
            l.pack(side="left", padx=4)
            l.bind("<Button-1>", lambda e, v=val: _set_status(v))
            
            def _enter(e, c=color, act=is_active):
                if not act: 
                    e.widget['fg'] = c
                    e.widget['bg'] = "#2c313a"
            
            def _leave(e, f=fg, b=bg, act=is_active):
                if not act:
                    e.widget['fg'] = f
                    e.widget['bg'] = b

            l.bind("<Enter>", _enter)
            l.bind("<Leave>", _leave)

        # Tabbed Interface
        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=20, pady=10)

        # Tab 1: Resumo AI
        f_res = tk.Frame(nb, bg=Theme.BG_DARK)
        nb.add(f_res, text="  🤖 Resumo e Análise Inteligente  ")
        
        txt_res = tk.Text(f_res, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY, font=("Consolas", 11), padx=20, pady=20, bd=0)
        txt_res.pack(fill="both", expand=True)
        
        summ = data.get('summary')
        if not summ:
            summ = "⚠️ A análise ainda está sendo gerada. Por favor, aguarde alguns instantes."
        
        txt_res.insert("1.0", summ)
        self.highlight_terms(txt_res)

        # Tab 2: Transcrição Full
        f_trans = tk.Frame(nb, bg=Theme.BG_DARK)
        nb.add(f_trans, text="  📝 Transcrição Completa  ")
        
        txt = tk.Text(f_trans, bg=Theme.BG_DARK, fg=Theme.FG_PRIMARY, font=("Consolas", 10), padx=20, pady=20, bd=0)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", data.get('text', ''))
        self.highlight_terms(txt)

    def highlight_terms(self, text_widget):
        # Precise keyword list - Phrases preferred over single generic words to avoid noise
        rules = {
            "pos": {
                "bg": "#2d4f37", "fg": "#98c379",
                "words": [
                    "economia premiável", "economia programada", "título de capitalização", "bradesco capitalização", "capitalização", "título", "títulos",
                    "pé quente", "max prêmios", "megapramios", "clube de vantagens",
                    "60 meses", "sessenta meses", "5 anos", "cinco anos", "carência", "12 meses", "doze meses", "vigência",
                    "sorteio", "sorteios", "número da sorte", "milhões", "mil reais", "contemplado", "contemplação", "loteria federal",
                    "resgate", "resgatar", "resgatável", "cem por cento", "integral",
                    "portal proteção", "0800", "central de atendimento", "assistência", "chaveiro", "encanador", "eletricista", "vidraceiro", "assistência residencial",
                    "não é investimento", "não tem rentabilidade", "sem garantia de lucro", "não rende",
                    "guardar dinheiro", "pé de meia", "disciplina financeira",
                    "aceito", "concordo", "autorizo", "estou ciente", "entendi", "protocolo", "auditoria"
                ]
            },
            "neu": {
                "bg": "#4d4632", "fg": "#e5c07b",
                "words": [
                    "débito na fatura", "débito automático", "conta corrente", "cartão de crédito", "extrato", "lançamento na fatura",
                    "reajuste", "ipca", "taxa referencial", "inflação", "correção monetária",
                    "renovação", "automática", "renova automaticamente", "imposto de renda", "tributação",
                    "vencimento da fatura", "melhor dia",
                    "cancelamento", "cancelar", "desistência", "estorno", "devolução", "reembolso", "7 dias", "arrependimento",
                    "confirmar dados", "atualizar cadastro", "cpf", "rg", "data de nascimento"
                ]
            },
            "neg": {
                "bg": "#4f2d32", "fg": "#e06c75",
                "words": [
                    "investimento", "investir", "investidor",
                    "rendimento", "rentabilidade", "rentável",
                    "aplicação financeira", "aplicar no banco",
                    "poupança", "conta poupança", "poupancinha",
                    "cdb", "lci", "lca", "tesouro direto", "ações", "fundo de investimento", "bolsa de valores", "cdi", "selic",
                    "lucro", "lucrar", "lucratividade", "ganho de capital",
                    "juros", "dobrar o valor", "triplicar", "patrimônio", "valorização",
                    "obrigatório", "tem que fazer", "tem que aceitar", "não pode recusar", "venda casada", "condicionado",
                    "urgente", "só hoje", "última chance", "vai perder", "insistência", "sistema vai cair",
                    "cancelar o cartão", "bloqueio do cartão", "travado", "limite do cartão", "perder a conta",
                    "liquidez diária", "sacar quando quiser", "resgate antecipado", "dinheiro liberado", "vira crédito",
                    "banco central", "bacen", "susep", "procon", "reclame aqui", "ouvidoria", "justiça", "advogado", "processo",
                    "mentira", "enganação", "golpe", "fraude", "cilada", "roubo"
                ]
            }
        }
        
        for tag, style in rules.items():
            text_widget.tag_config(tag, background=style["bg"], foreground=style["fg"])
            for word in style["words"]:
                 # Regex pattern for EXACT word matching using Tcl's \y boundary
                 safe_word = ""
                 for char in word:
                     if char.isalnum() or char == ' ': safe_word += char
                     else: safe_word += f"\\{char}"
                     
                 # \y matches either start or end of word. 
                 # enclosing in \y...\y ensures whole word match.
                 pattern = f"\\y{safe_word}\\y"
                 
                 pos = "1.0"
                 while True:
                     count = tk.IntVar()
                     try:
                        idx = text_widget.search(pattern, pos, stopindex="end", count=count, nocase=True, regexp=True)
                     except: break # Fallback if regexp fails
                     
                     if not idx: break
                     end_idx = f"{idx}+{count.get()}c"
                     text_widget.tag_add(tag, idx, end_idx)
                     pos = end_idx

    # --- Data ---
    def poll_data(self):
        if self.running: self.fetch_now(); self.after(REFRESH_RATE_MS, self.poll_data)
    def fetch_now(self): threading.Thread(target=self._bg_fetch, daemon=True).start()
    def _bg_fetch(self):
        tasks, res = [], {}
        try:
            tasks = requests.get(f"{self.api_url}/api/history?limit=2000&all=true", headers={"Authorization": f"Bearer {self.token}"}, timeout=8).json().get("tasks", [])
            r = requests.get(f"{self.api_url}/api/resources", headers={"Authorization": f"Bearer {self.token}"}, timeout=4)
            if r.status_code == 404: r = requests.get(f"{self.api_url}/api/admin/system/resources", headers={"Authorization": f"Bearer {self.token}"}, timeout=4)
            res = r.json() if r.status_code == 200 else {"error": "ERR"}
        except: res = {"error": "OFF"}
        self.after(0, lambda: self.update_ui(tasks, res))
    def update_ui(self, tasks, res):
        if not self.container.winfo_exists(): return
        self.tasks = tasks
        err = res.get("error")
        for k in ["CPU", "RAM", "GPU"]:
            val_str = str(err if err else res.get(k.lower()))
            is_err = val_str.startswith("E") or val_str in ["OFF", "ERR"]
            num = 100 if is_err else float(val_str.replace("%","").strip()) if not is_err and val_str!="N/A" else 0
            lbl, bar = self.res_labels.get(k), self.res_labels.get(f"{k}_bar")
            if lbl: lbl.config(text=f"{val_str}{'%' if not is_err and '%' not in val_str and val_str!='N/A' else ''}", fg=Theme.ERROR if is_err else Theme.ACCENT)
            if bar: bar.configure(width=int((num/100)*bar.master.winfo_width()) if bar.master.winfo_width()>1 else int(num*2), bg=Theme.ERROR if is_err else Theme.ACCENT)
        if hasattr(self, 'lbl_stats_total') and self.lbl_stats_total.winfo_exists():
            self.lbl_stats_total.config(text=str(len(tasks)))
            self.lbl_stats_proc.config(text=str(sum(1 for t in tasks if t['status'] in ['processing', 'queued'])))
            self.lbl_stats_done.config(text=str(sum(1 for t in tasks if t['status'] == 'completed')))
            self.lbl_stats_fail.config(text=str(sum(1 for t in tasks if t['status'] == 'failed')))
            self.refresh_table()
    def create_stat_card(self, p, t, v, c):
        f = ttk.Frame(p, style="Card.TFrame", padding=15); f.grid(row=0, column=c, sticky="ew", padx=(0,15)); p.columnconfigure(c, weight=1)
        tk.Label(f, text=t.upper(), bg=Theme.BG_CARD, fg=Theme.FG_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        l = tk.Label(f, text=v, bg=Theme.BG_CARD, fg=Theme.FG_PRIMARY, font=Theme.FONT_HUGE); l.pack(anchor="w"); return l
    def create_table(self, p):
        self.tree = ttk.Treeview(p, columns=("id","file","status","prog","date"), show="headings", selectmode="browse")
        sb = ttk.Scrollbar(p, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        
        self.tree.heading("file", text="Arquivo"); self.tree.heading("status", text="Status"); self.tree.heading("prog", text="%"); self.tree.heading("date", text="Data")
        self.tree.column("id", width=0, stretch=False); self.tree.column("file", width=300); self.tree.column("status", width=100, anchor="center"); self.tree.column("prog", width=60, anchor="center"); self.tree.column("date", width=120, anchor="center")
        
        self.tree.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        
        # FIX: Comprehensive Styling to kill White Rows interactions
        # We set background explicitly to avoid system defaults leaking through
        self.tree.tag_configure('completed', background=Theme.BG_DARK, foreground=Theme.FG_PRIMARY)
        self.tree.tag_configure('processing', background=Theme.BG_DARK, foreground=Theme.ACCENT)
        self.tree.tag_configure('failed', background=Theme.BG_DARK, foreground=Theme.ERROR)
        self.tree.tag_configure('queued', background=Theme.BG_DARK, foreground=Theme.FG_SECONDARY)
        self.tree.tag_configure('pending', background=Theme.BG_DARK, foreground=Theme.FG_SECONDARY)
        self.tree.tag_configure('default', background=Theme.BG_DARK, foreground=Theme.FG_PRIMARY)
        
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def refresh_table(self, event=None):
        if not hasattr(self, 'tree') or not self.tree.winfo_exists(): return
        
        # Preserve selection
        sel = self.tree.selection()
        sid = self.tree.item(sel[0])['values'][0] if sel else None
        
        # Clear
        for i in self.tree.get_children(): self.tree.delete(i)
        
        # Get filters
        search_term = self.search_var.get().lower().strip() if hasattr(self, 'search_var') else ""
        status_filter = self.filter_status_var.get() if hasattr(self, 'filter_status_var') else "Todos"
        sort_mode = self.sort_var.get() if hasattr(self, 'sort_var') else "Data (Novos)"
        
        filtered_tasks = []
        for t in self.tasks:
            # 1. Status Filter
            if status_filter == "Ativos" and t['status'] not in ['processing', 'queued']: continue
            if status_filter == "Concluídos" and t['status'] != 'completed': continue
            if status_filter == "Falhas" and t['status'] != 'failed': continue
            
            # 2. Search Filter
            if search_term and search_term not in t['filename'].lower(): continue
            
            filtered_tasks.append(t)
            
        # 3. Sort
        if sort_mode == "Data (Novos)":
            filtered_tasks.sort(key=lambda x: x.get('created_at',''), reverse=True)
        elif sort_mode == "Data (Antigos)":
            filtered_tasks.sort(key=lambda x: x.get('created_at',''))
        elif sort_mode == "Nome (A-Z)":
            filtered_tasks.sort(key=lambda x: x['filename'].lower())
        elif sort_mode == "Nome (Z-A)":
            filtered_tasks.sort(key=lambda x: x['filename'].lower(), reverse=True)
        else:
            # Default fallback (status priority)
            filtered_tasks.sort(key=lambda x: ({"processing":0,"queued":1}.get(x['status'], 4), x['task_id']))

        for t in filtered_tasks:
            # Dynamic Dislay
            st_disp = t['status'].upper()
            if t['status'] == 'completed':
                st_disp = (t.get('analysis_status') or "PENDENTE DE ANÁLISE").upper()
            
            # Robust Tagging
            raw_status = t['status']
            tag = raw_status if raw_status in ['completed', 'processing', 'failed', 'queued', 'pending'] else 'default'
            
            self.tree.insert("", "end", iid=t['task_id'], values=(
                t['task_id'], 
                f" {t['filename']}", 
                st_disp, 
                f"{t.get('progress') or 0}%", 
                format_time(t.get('created_at',''))
            ), tags=(tag,))
            
        if sid and self.tree.exists(sid): 
            try: self.tree.selection_set(sid)
            except: pass
    def do_upload(self):
        fs = filedialog.askopenfilenames()
        if fs: threading.Thread(target=lambda: [requests.post(f"{self.api_url}/api/upload", files={"file":open(f,'rb')}, headers={"Authorization":f"Bearer {self.token}"}, data={"timestamp":"true"}) for f in fs] and self.fetch_now(), daemon=True).start()
    def show_context_menu(self, e):
        i = self.tree.identify_row(e.y)
        if i:
            self.tree.selection_set(i)
            m = tk.Menu(self, tearoff=0)
            m.add_command(label="Detalhes", command=self.on_double_click)
            m.add_command(label="Ouvir Áudio", command=self.play_audio)
            m.add_command(label="Excluir", command=self.delete_task)
            m.post(e.x_root, e.y_root)

    def play_audio(self):
        sel = self.tree.selection()
        if not sel: return
        task_id = self.tree.item(sel[0])['values'][0]
        
        def _play():
            try:
                r = requests.get(f"{self.api_url}/api/audio/{task_id}", headers={"Authorization": f"Bearer {self.token}"}, stream=True)
                if r.status_code == 200:
                    fname = f"audio_{task_id}.wav"
                    if "Content-Disposition" in r.headers:
                        import re
                        m = re.search('filename="(.+)"', r.headers["Content-Disposition"])
                        if m: fname = m.group(1)
                    
                    path = os.path.join(tempfile.gettempdir(), fname)
                    with open(path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                    os.startfile(path)
                else:
                     messagebox.showerror("Erro", f"Erro ao baixar áudio: {r.status_code}")
            except Exception as e: messagebox.showerror("Erro", str(e))
        threading.Thread(target=_play, daemon=True).start()

    def on_double_click(self, e=None):
        sel = self.tree.selection()
        if sel: threading.Thread(target=lambda: self.show_details(requests.get(f"{self.api_url}/api/result/{self.tree.item(sel[0])['values'][0]}", headers={"Authorization":f"Bearer {self.token}"}).json()), daemon=True).start()

    def delete_task(self):
        sel = self.tree.selection()
        if sel: requests.delete(f"{self.api_url}/api/task/{self.tree.item(sel[0])['values'][0]}", headers={"Authorization":f"Bearer {self.token}"}); self.tree.delete(sel[0])

    def rename_task(self): pass

if __name__ == "__main__":
    app = MirrorMonitorApp()
    app.mainloop()
