import os, sys, subprocess, threading, shutil
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox

ROOT=Path(__file__).resolve().parent
VENV=ROOT/".build_venv"

class Builder(ctk.CTk):
    def __init__(self):
        super().__init__(); ctk.set_appearance_mode("dark")
        self.title("EBS PC Remote Builder v1.0.4"); self.geometry("980x680"); self.minsize(850,600)
        self.configure(fg_color="#07111f")
        self._build()

    def _build(self):
        side=ctk.CTkFrame(self,width=220,corner_radius=0,fg_color="#081421"); side.pack(side="left",fill="y"); side.pack_propagate(False)
        ctk.CTkLabel(side,text="EBS",font=("Segoe UI",36,"bold"),text_color="#19d4ff").pack(anchor="w",padx=28,pady=(30,0))
        ctk.CTkLabel(side,text="PC REMOTE\nBUILDER",font=("Segoe UI",14,"bold"),text_color="#8fa9c4",justify="left").pack(anchor="w",padx=29,pady=(0,30))
        for t in ["◉ Ana Sayfa","▣ Windows EXE","⌁ Bağımlılıklar","⚙ Ayarlar","≡ Log"]:
            ctk.CTkButton(side,text=t,anchor="w",height=44,fg_color="transparent",hover_color="#10213a",corner_radius=10).pack(fill="x",padx=14,pady=4)
        main=ctk.CTkFrame(self,fg_color="#07111f",corner_radius=0); main.pack(side="left",fill="both",expand=True)
        ctk.CTkLabel(main,text="EBS PC Remote Builder",font=("Segoe UI",30,"bold"),text_color="#eef7ff").pack(anchor="w",padx=30,pady=(28,4))
        ctk.CTkLabel(main,text="Windows ↔ Windows LAN remote desktop derleyicisi",font=("Segoe UI",13),text_color="#8fa9c4").pack(anchor="w",padx=31,pady=(0,22))
        card=ctk.CTkFrame(main,fg_color="#0d1a2d",corner_radius=20,border_width=1,border_color="#1c3556"); card.pack(fill="x",padx=30,pady=8)
        ctk.CTkLabel(card,text="WINDOWS EXE",font=("Segoe UI",16,"bold"),text_color="#19d4ff").pack(anchor="w",padx=24,pady=(20,5))
        ctk.CTkLabel(card,text="✓ İzole build ortamı\n✓ Bağımlılık kurulumu\n✓ PyInstaller\n✓ UAC Admin manifest\n✓ Modern icon\n✓ Tek EXE",justify="left",font=("Segoe UI",13),text_color="#eef7ff").pack(anchor="w",padx=24,pady=6)
        ctk.CTkButton(card,text="WINDOWS EXE DERLE",height=48,fg_color="#2678ff",hover_color="#195cd0",corner_radius=12,font=("Segoe UI",14,"bold"),command=self.start).pack(fill="x",padx=24,pady=(12,22))
        self.log=ctk.CTkTextbox(main,fg_color="#040b13",border_width=1,border_color="#1c3556",text_color="#8ce9b1",font=("Consolas",11))
        self.log.pack(fill="both",expand=True,padx=30,pady=(12,28))
        self.write("EBS PC Remote Builder hazır.")

    def write(self,s):
        self.log.insert("end",s+"\n"); self.log.see("end"); self.update_idletasks()

    def run(self,args,cwd=None):
        self.write("> "+" ".join(map(str,args)))
        p=subprocess.Popen(args,cwd=cwd or ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="replace")
        for line in p.stdout:self.write(line.rstrip())
        p.wait(); self.write(f"[ÇIKIŞ KODU] {p.returncode}"); return p.returncode

    def start(self): threading.Thread(target=self.build_exe,daemon=True).start()

    def build_exe(self):
        try:
            py=sys.executable
            if not VENV.exists():
                if self.run([py,"-m","venv",str(VENV)]): raise RuntimeError("venv oluşturulamadı")
            vpy=VENV/"Scripts"/"python.exe"
            # Tkinter pip paketi değildir. Ana Python kurulumu Tcl/Tk içermiyorsa
            # sağlam bir GUI EXE üretilemez; bunu build öncesi açıkça kontrol et.
            tkcheck = subprocess.run(
                [py, "-c", "import tkinter, _tkinter; print(tkinter.TkVersion)"],
                capture_output=True, text=True
            )
            if tkcheck.returncode != 0:
                raise RuntimeError(
                    "Bu Python kurulumunda Tkinter/Tcl-Tk bulunamadı. "
                    "Python'u python.org Windows x64 kurucusuyla 'tcl/tk and IDLE' özelliği açık olacak şekilde kurun. "
                    "Ayrıntı: " + (tkcheck.stderr.strip() or tkcheck.stdout.strip())
                )
            self.write("[OK] Tkinter/Tcl-Tk bulundu: " + tkcheck.stdout.strip())
            if self.run([str(vpy),"-m","pip","install","--upgrade","pip","setuptools==80.10.2","wheel"]):raise RuntimeError("Temel paket kurulamadı")
            if self.run([str(vpy),"-m","pip","install","-r",str(ROOT/"requirements.txt"),"pyinstaller>=6.15.0"]):raise RuntimeError("Bağımlılıklar kurulamadı")
            dist=ROOT/"dist"; build=ROOT/"build"
            for p in (dist,build):
                if p.exists():shutil.rmtree(p)
            # Tkinter Python'ın stdlib parçasıdır; pip ile kurulmaz. PyInstaller'a
            # ana Python kurulumundaki Tcl/Tk runtime klasörlerini açıkça veriyoruz.
            base_py = Path(sys.base_prefix)
            tcl_dir = base_py / "tcl"
            dll_dir = base_py / "DLLs"

            # İzole venv içindeki PyInstaller, stdlib tkinter modüllerini ana Python'dan görür;
            # ancak bazı Windows kurulumlarında hook otomatik tespit edemediği için hidden-import eklenir.
            cmd=[str(vpy),"-m","PyInstaller","--noconfirm","--clean","--onefile","--windowed",
                 "--name","EBS_PC_Remote","--uac-admin",
                 "--hidden-import","tkinter",
                 "--hidden-import","tkinter.ttk",
                 "--hidden-import","tkinter.messagebox",
                 "--hidden-import","tkinter.filedialog",
                 "--hidden-import","_tkinter",
                 "--collect-all","customtkinter","--collect-all","tkinterdnd2"]

            # Tcl/Tk data ve DLL'lerini yalnızca gerçekten mevcutlarsa ekle.
            if tcl_dir.exists():
                cmd += ["--add-data", f"{tcl_dir}{os.pathsep}tcl"]
            for dll_name in ("tcl86t.dll","tk86t.dll","tcl87.dll","tk87.dll"):
                dll_path = dll_dir / dll_name
                if dll_path.exists():
                    cmd += ["--add-binary", f"{dll_path}{os.pathsep}."]
            ico=ROOT/"assets"/"ebs_pc_remote.ico"
            if ico.exists():cmd += ["--icon",str(ico)]
            cmd += [str(ROOT/"main.py")]
            if self.run(cmd):raise RuntimeError("PyInstaller başarısız")
            exe=dist/"EBS_PC_Remote.exe"
            if not exe.exists():raise RuntimeError("EXE bulunamadı")
            self.write(f"[BAŞARILI] {exe}")
            messagebox.showinfo("EBS Builder",f"EXE hazır:\n{exe}",parent=self)
        except Exception as e:
            self.write("[HATA] "+str(e))
            messagebox.showerror("EBS Builder",str(e),parent=self)

if __name__=="__main__":
    Builder().mainloop()
