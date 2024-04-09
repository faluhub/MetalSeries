import os, wmi, psutil, shutil, json, jsbeautifier, asarPy
from cached_property import cached_property

class Decompiler:
    def __init__(self) -> None:
        self.wmi = wmi.WMI()
        self.default_root_path = "C:/Program Files/SteelSeries/GG"
        self.last_copy_ver_path = "./data/last_copy_ver.txt"
        self.media_extensions = [".png", ".svg", ".jpg", ".woff", ".ttf", ".woff2", ".gif", ".webp", ".webm", ".otf", ".ico", ".eot"]

    @cached_property
    def root_path(self) -> str:
        if not os.path.exists(self.default_root_path):
            processes = self.wmi.Win32_Process(name="SteelSeriesGG.exe")
            if len(processes) > 0:
                process = psutil.Process(processes[0].ProcessId)
                path = os.path.dirname(process.exe())
                print(f"Using identified root path: '{path}'")
                return path
            raise Exception("Couldn't find SteelSeries installation path. Make sure 'SteelSeriesGG.exe' is running.")
        print(f"Using default installation path: '{self.default_root_path}'.")
        return self.default_root_path

    def save_asar(self) -> None:
        os.makedirs("./data", exist_ok=True)
        copy_paths = [
            os.path.join(self.root_path, "resources/app.asar"),
            os.path.join(self.root_path, "resources/app.asar.unpacked")
        ]
        for path in copy_paths:
            basename = os.path.basename(path)
            dest = os.path.join("./data", basename)
            if os.path.isdir(path):
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(path, dest)
            else:
                if os.path.exists(dest):
                    os.remove(dest)
                shutil.copyfile(path, dest)
            print(f"Copied '{basename}'.")

        modules_path = "./data/app.asar.unpacked/native_modules/win32"
        dest = os.path.join(modules_path, "x64")
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(os.path.join(modules_path, "ia32"), dest)
        print("Created x64 modules.")

        with open(os.path.join(self.root_path, "version.json")) as r:
            version = json.load(r)["version"]
            with open(self.last_copy_ver_path, "w") as w:
                w.write(version)
                print("Saved last copied version.")
    
    def save_latest(self) -> bool:
        if not os.path.exists(self.last_copy_ver_path):
            print("Hasn't copied before, copying asar...")
            self.save_asar()
            return True
        with open(os.path.join(self.root_path, "version.json")) as o:
            official_version = json.load(o)["version"]
            print(f"Installed GG version: '{official_version}'.")
            with open(self.last_copy_ver_path, "r") as c:
                copied_version = c.read()
                print(f"Last copied GG version: '{copied_version}'.")
        if not official_version == copied_version:
            print("Last copied not latest version, copying asar...")
            self.save_asar()
            return True
        return False

    def decompile_asar(self) -> None:
        saved_new = self.save_latest()
        os.makedirs("./decomp", exist_ok=True)
        if saved_new:
            print("New asar file found, decompiling...")
            if os.path.exists("./decomp"):
                shutil.rmtree("./decomp")
                print("Deleted old decomp.")
            print("Starting extraction...")
            asarPy.extract_asar("./data/app.asar", "./decomp")
            print("Finished extracting, separating media...")
            self.move_media()
            print("Beautifying source code...")
            self.beautify()
            return
        print("Asar file up-to-date, skipping decomp.")
    
    def move_media(self) -> None:
        folder = "./decomp/render"
        media_folder = os.path.join(folder, "media")
        os.makedirs(media_folder, exist_ok=True)
        affected = []
        for filename in os.listdir(folder):
            for extension in self.media_extensions:
                if filename.endswith(extension):
                    shutil.move(os.path.join(folder, filename), os.path.join(media_folder, filename))
                    affected.append(filename)
                    break
        print(f"Finished moving {len(affected)} media files, updating usages...")
        replaced = 0
        for filename in os.listdir(folder):
            path = os.path.join(folder, filename)
            if not os.path.isdir(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for usage in affected:
                        replaced += content.count(usage)
                        content = content.replace(usage, f"media/{usage}")
                    with open(path, "w", encoding="utf-8") as w:
                        w.write(content)
        print(f"Updated {replaced} usages.")

    def beautify(self) -> None:
        opts = jsbeautifier.BeautifierOptions()
        opts.indent_size = 2
        opts.preserve_newlines = False
        def walk(path: str):
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                if filename.endswith(".js"):
                    res = jsbeautifier.beautify_file(file_path, opts)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(res)
                    print(f"Beautified '{filename}'.")
                elif os.path.isdir(file_path):
                    walk(file_path)
        walk("./decomp")
        print("Finished beautifying source code.")

class Patcher:
    def __init__(self, decompiler: Decompiler) -> None:
        self.decompiler = decompiler
        file = open("./patches.json")
        self.patches = json.load(file)
        file.close()
        self.temp_path = "./data/_patched"
    
    def remove_temp_path(self):
        if os.path.exists(self.temp_path):
            shutil.rmtree(self.temp_path)
            print("Removed temp path.")
    
    def create_temp_path(self):
        self.remove_temp_path()
        shutil.copytree("./decomp", self.temp_path)
        print("Copied decomp to temp folder.")
    
    def find(self, text: str, string: str):
        indices = []
        start = 0
        while True:
            index = text.find(string, start, len(text))
            if index == -1:
                return indices
            indices.append(index)
            start = index + 1

    def replace(self, text: str, string: str, replacement: str, occurence: int, limit: int):
        indices = self.find(text, string)
        if len(indices) - 1 < occurence:
            return text
        index = indices[occurence]
        prefix = text[0:index]
        suffix = text[index:len(text)].replace(string, replacement, limit)
        return prefix + suffix

    def apply_patches(self):
        print("Patching asar contents...")
        self.create_temp_path()
        for patch_id in self.patches:
            print(f"Starting patch '{patch_id}'...")
            data = self.patches[patch_id]
            if not data["enabled"]:
                print(f"Skipping '{patch_id}' as it's disabled.")
                continue
            for patch in data["patches"]:
                path = os.path.join(self.temp_path, patch["file"])
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    content = self.replace(content, patch["string"], patch["replacement"], patch["occurence"], patch["limit"])
                    with open(path, "w", encoding="utf-8") as w:
                        w.write(content)
            print(f"Finished patch '{patch_id}'.")
    
    def pack_asar(self):
        self.decompiler.decompile_asar()
        self.apply_patches()
        patched_path = "./data/patched.asar"
        print("Packing asar file...")
        asarPy.pack_asar(self.temp_path, patched_path)
        print("Finished packing asar file.")
        shutil.copyfile(patched_path, os.path.join(self.decompiler.root_path, "resources/app.asar"))
        print("Copied packed file.")
        self.remove_temp_path()

Patcher(Decompiler()).pack_asar()
# Decompiler().beautify()
