import os, sys, json, tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import urllib.request, subprocess, platform, threading, uuid, requests, shutil

# --- Constants ---
USER_AGENT = "CatClient/1.5 (LunarCat)"
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
ELYBY_AUTH_URL = "https://authserver.ely.by/auth/authenticate"

# Directories
if platform.system() == "Windows":
    APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
    BASE_DIR = os.path.join(APPDATA, '.catclient')
else:
    BASE_DIR = os.path.join(os.path.expanduser('~'), '.catclient')

MINECRAFT_DIR = os.path.join(BASE_DIR, 'minecraft')
VERSIONS_DIR = os.path.join(MINECRAFT_DIR, 'versions')
LIBRARIES_DIR = os.path.join(MINECRAFT_DIR, 'libraries')
ASSETS_DIR = os.path.join(MINECRAFT_DIR, 'assets')
for d in [MINECRAFT_DIR, VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR,
          os.path.join(ASSETS_DIR, 'indexes'), os.path.join(ASSETS_DIR, 'objects')]:
    os.makedirs(d, exist_ok=True)

# --- Helpers ---
def download_file(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest): return
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    print(f"Downloaded {dest}")

def authenticate_elyby(username, password):
    try:
        payload = {"agent": {"name": "Minecraft", "version": 1},
                   "username": username, "password": password}
        resp = requests.post(ELYBY_AUTH_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            profile = data.get("selectedProfile", {})
            return {
                "username": profile.get("name", username),
                "uuid": profile.get("id"),
                "token": data.get("accessToken"),
                "type": "elyby"
            }
        else:
            messagebox.showerror("Ely.by Error", resp.text)
    except Exception as e:
        messagebox.showerror("Ely.by Error", f"Auth failed: {e}")
    return None

# --- CatClient Lunar Edition ---
class CatClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CatClient 1.5.x 🐾 (Lunar Cat)")
        self.geometry("900x550")
        self.configure(bg="#1b1b1b")

        self.versions, self.version_categories = {}, {
            "Latest Release": [], "Latest Snapshot": [],
            "Release": [], "Snapshot": [], "Old Beta": [], "Old Alpha": []
        }

        # Default offline session
        self.session = {"username": "CatPlayer",
                        "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, "CatPlayer")),
                        "token": "cat_offline",
                        "type": "offline"}

        self.online_mode = tk.BooleanVar(value=False)
        self.init_ui()
        threading.Thread(target=self.load_version_manifest, daemon=True).start()

    # --- UI ---
    def init_ui(self):
        sidebar = tk.Frame(self, bg="#242424", width=280)
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="🐾 CatClient 1.5.x", font=("Consolas", 18, "bold"),
                 bg="#242424", fg="#55ff55").pack(pady=15)

        # Ely.by login
        tk.Label(sidebar, text="Username/Email", bg="#242424", fg="white").pack(anchor="w", padx=15)
        self.username_input = tk.Entry(sidebar, bg="#404040", fg="white", relief="flat")
        self.username_input.pack(fill="x", padx=15, pady=3)

        tk.Label(sidebar, text="Password", bg="#242424", fg="white").pack(anchor="w", padx=15)
        self.password_input = tk.Entry(sidebar, bg="#404040", fg="white", show="*", relief="flat")
        self.password_input.pack(fill="x", padx=15, pady=3)

        tk.Checkbutton(sidebar, text="Login with Ely.by", variable=self.online_mode,
                       bg="#242424", fg="white", activebackground="#242424",
                       selectcolor="#242424").pack(anchor="w", padx=15, pady=5)

        # Version picker
        tk.Label(sidebar, text="Game Version", bg="#242424", fg="white").pack(anchor="w", padx=15, pady=(20,0))
        self.category_combo = ttk.Combobox(sidebar, values=list(self.version_categories.keys()), state="readonly")
        self.category_combo.pack(fill="x", padx=15, pady=3)
        self.category_combo.set("Latest Release")
        self.category_combo.bind("<<ComboboxSelected>>", self.update_version_list)
        self.version_combo = ttk.Combobox(sidebar, state="readonly")
        self.version_combo.pack(fill="x", padx=15, pady=3)

        # Buttons
        tk.Button(sidebar, text="🐾 PLAY 🐾", font=("Consolas", 14, "bold"),
                  bg="#3aa13a", fg="white", relief="flat",
                  command=self.prepare_and_launch).pack(fill="x", padx=15, pady=(20,5))
        tk.Button(sidebar, text="Play Mojang Offline", font=("Consolas", 10),
                  bg="#505050", fg="white", relief="flat",
                  command=self.run_offline_only).pack(fill="x", padx=15)

        # Right side news panel
        content = tk.Frame(self, bg="#1b1b1b")
        content.pack(side="right", fill="both", expand=True)
        tk.Label(content, text="CatClient News", font=("Consolas", 16, "bold"),
                 bg="#1b1b1b", fg="white").pack(anchor="w", padx=15, pady=15)
        self.news_box = tk.Text(content, bg="#101010", fg="white", wrap="word",
                                relief="flat", font=("Consolas", 10))
        self.news_box.pack(fill="both", expand=True, padx=15, pady=10)
        self.news_box.insert("end", "✨ CatClient Lunar Edition\n\n- Ely.by online mode\n- Mojang offline mode\n- Auto-downloads JSON, JAR, libs, assets\n- Modern dark UI (Lunar vibes)\n")

    # --- Version manifest ---
    def load_version_manifest(self):
        try:
            req = urllib.request.Request(VERSION_MANIFEST_URL, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req) as url:
                manifest = json.loads(url.read().decode())
            self.versions = {v["id"]: v["url"] for v in manifest["versions"]}
            for c in self.version_categories: self.version_categories[c] = []
            latest_release, latest_snapshot = manifest["latest"]["release"], manifest["latest"]["snapshot"]
            for v in manifest["versions"]:
                if v["id"] == latest_release:
                    self.version_categories["Latest Release"].append(v["id"])
                elif v["id"] == latest_snapshot:
                    self.version_categories["Latest Snapshot"].append(v["id"])
                elif v["type"] == "release":
                    self.version_categories["Release"].append(v["id"])
                elif v["type"] == "snapshot":
                    self.version_categories["Snapshot"].append(v["id"])
                elif v["type"] == "old_beta":
                    self.version_categories["Old Beta"].append(v["id"])
                elif v["type"] == "old_alpha":
                    self.version_categories["Old Alpha"].append(v["id"])
            for c in ["Release","Snapshot","Old Beta","Old Alpha"]:
                self.version_categories[c].sort(reverse=True)
            self.update_version_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load versions: {e}")

    def update_version_list(self, event=None):
        cat = self.category_combo.get()
        vs = self.version_categories.get(cat, [])
        self.version_combo['values'] = vs
        if vs: self.version_combo.current(0)

    # --- Downloader ---
    def ensure_version(self, version_id):
        vdir = os.path.join(VERSIONS_DIR, version_id)
        vjson = os.path.join(vdir, f"{version_id}.json")
        os.makedirs(vdir, exist_ok=True)

        # JSON
        if not os.path.exists(vjson):
            url = self.versions.get(version_id)
            if url: download_file(url, vjson)
        if not os.path.exists(vjson): return None

        with open(vjson) as f: data = json.load(f)

        # Client JAR
        jar_info = data.get("downloads", {}).get("client")
        jar_path = os.path.join(vdir, f"{version_id}.jar")
        if jar_info and not os.path.exists(jar_path):
            download_file(jar_info["url"], jar_path)

        # Libraries
        for lib in data.get("libraries", []):
            art = lib.get("downloads", {}).get("artifact")
            if art:
                lib_path = os.path.join(LIBRARIES_DIR, art["path"])
                if not os.path.exists(lib_path):
                    download_file(art["url"], lib_path)

        # Assets
        asset_index = data.get("assetIndex", {})
        if asset_index:
            idx_path = os.path.join(ASSETS_DIR, "indexes", f"{asset_index['id']}.json")
            if not os.path.exists(idx_path):
                download_file(asset_index["url"], idx_path)
            with open(idx_path) as f: idx = json.load(f)
            for name, obj in idx.get("objects", {}).items():
                h = obj["hash"]; sub = h[:2]
                apath = os.path.join(ASSETS_DIR, "objects", sub, h)
                if not os.path.exists(apath):
                    url = f"https://resources.download.minecraft.net/{sub}/{h}"
                    download_file(url, apath)

        return vjson

    # --- Launcher ---
    def build_launch_command(self, version_id):
        vjson = self.ensure_version(version_id)
        if not vjson: return []
        with open(vjson) as f: data = json.load(f)
        main_class = data.get("mainClass")
        if not main_class: return []
        vdir = os.path.join(VERSIONS_DIR, version_id)
        jar_path = os.path.join(vdir, f"{version_id}.jar")
        classpath = [jar_path]
        for lib in data.get("libraries", []):
            art = lib.get("downloads", {}).get("artifact")
            if art:
                lib_path = os.path.join(LIBRARIES_DIR, art["path"])
                if os.path.exists(lib_path): classpath.append(lib_path)
        cmd = ["java", "-Xmx2G", "-cp", os.pathsep.join(classpath), main_class]

        args = data.get("minecraftArguments","").split()
        repl = {
            "${auth_player_name}": self.session["username"],
            "${auth_uuid}": self.session["uuid"],
            "${auth_access_token}": self.session["token"],
            "${version_name}": version_id,
            "${game_directory}": MINECRAFT_DIR,
            "${assets_root}": ASSETS_DIR,
            "${assets_index_name}": data.get("assetIndex",{}).get("id",""),
            "${user_type}": self.session.get("type","catclient"),
            "${user_properties}": "{}"
        }
        final_args = []
        for a in args:
            for k,v in repl.items():
                if k in a: a = a.replace(k,v)
            final_args.append(a)
        return cmd + final_args

    def prepare_and_launch(self):
        version = self.version_combo.get()
        if not version: return messagebox.showerror("Error","Pick a version")

        if self.online_mode.get():
            u, p = self.username_input.get().strip(), self.password_input.get().strip()
            s = authenticate_elyby(u,p)
            if not s: return
            self.session = s
        else:
            self.session = {"username": "CatPlayer",
                            "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, "CatPlayer")),
                            "token": "cat_offline",
                            "type": "offline"}

        cmd = self.build_launch_command(version)
        if not cmd: return
        try:
            subprocess.Popen(cmd, cwd=MINECRAFT_DIR)
            messagebox.showinfo("Launch", f"Meowcraft {version} started as {self.session['username']}!")
        except Exception as e:
            messagebox.showerror("Error", f"Launch failed: {e}")

    def run_offline_only(self):
        version = self.version_combo.get()
        if not version: return messagebox.showerror("Error","Pick a version")
        self.session = {"username": "CatPlayer",
                        "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, "CatPlayer")),
                        "token": "cat_offline",
                        "type": "offline"}
        cmd = self.build_launch_command(version)
        if not cmd: return
        try:
            subprocess.Popen(cmd, cwd=MINECRAFT_DIR)
            messagebox.showinfo("Launch", f"Mojang Offline {version} launched!")
        except Exception as e:
            messagebox.showerror("Error", f"Launch failed: {e}")

if __name__ == "__main__":
    app = CatClientApp()
    app.mainloop()
