import sys
import time
import os
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Resolve repository directories dynamically
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGIN_DIR = os.path.join(BASE_DIR, "login")

def deploy_locally():
    print("[*] Applying Azam Basha Branding & Logo Assets natively...")
    
    logo_src = os.path.join(ASSETS_DIR, "logo.png")
    favicon_src = os.path.join(ASSETS_DIR, "favicon.ico")
    favicon_png_src = os.path.join(ASSETS_DIR, "favicon.png")
    
    if not os.path.exists(logo_src):
        print(f"[!] Logo source not found at {logo_src}")
        return False

    remote_logo_paths = [
        "/opt/unetlab/data/branding/logo.png",
        "/opt/unetlab/html/images/logo.png",
        "/opt/unetlab/html/themes/default/images/logo.png",
        "/opt/unetlab/html/assets-common/img/logo.png",
        "/usr/share/plymouth/themes/pnetlab/logo.png"
    ]

    for rpath in remote_logo_paths:
        rdir = os.path.dirname(rpath)
        os.makedirs(rdir, exist_ok=True)
        try:
            shutil.copyfile(logo_src, rpath)
            os.chmod(rpath, 0o644)
            print(f"  [✔] Deployed logo -> {rpath}")
        except Exception as e:
            print(f"  [-] Note for {rpath}: {e}")

    remote_favicon_paths = [
        "/opt/unetlab/html/images/favicon.png",
        "/opt/unetlab/html/themes/default/images/favicon.ico",
        "/opt/unetlab/html/favicon.ico",
        "/opt/unetlab/html/favicon/favicon.ico",
        "/opt/unetlab/html/assets-common/img/favicon.ico",
        "/opt/unetlab/html/assets-common/img/favicon.png"
    ]

    for fpath in remote_favicon_paths:
        rdir = os.path.dirname(fpath)
        os.makedirs(rdir, exist_ok=True)
        src = favicon_png_src if fpath.endswith(".png") and os.path.exists(favicon_png_src) else favicon_src
        if os.path.exists(src):
            try:
                shutil.copyfile(src, fpath)
                os.chmod(fpath, 0o644)
                print(f"  [✔] Deployed favicon -> {fpath}")
            except Exception as e:
                print(f"  [-] Note for {fpath}: {e}")

    # Copy modernized login page if available
    login_html_src = os.path.join(LOGIN_DIR, "index.html")
    login_css_src = os.path.join(LOGIN_DIR, "login.css")
    if os.path.exists(login_html_src):
        dest_html = "/opt/unetlab/html/login/index.html"
        os.makedirs("/opt/unetlab/html/login", exist_ok=True)
        try:
            shutil.copyfile(login_html_src, dest_html)
            os.chmod(dest_html, 0o644)
            print(f"  [✔] Deployed modernized login HTML -> {dest_html}")
        except Exception as e:
            print(f"  [-] Note for {dest_html}: {e}")

    if os.path.exists(login_css_src):
        dest_css = "/opt/unetlab/html/login/login.css"
        try:
            shutil.copyfile(login_css_src, dest_css)
            os.chmod(dest_css, 0o644)
            print(f"  [✔] Deployed modernized login CSS -> {dest_css}")
        except Exception as e:
            print(f"  [-] Note for {dest_css}: {e}")

    # Update branding config.json to cache bust
    now_ts = int(time.time())
    cfg_json = f'{{\n    "name": "Azam Basha",\n    "login_header": "Azam Basha Network Emulation Platform",\n    "hide_default_creds": false,\n    "updated_at": {now_ts}\n}}\n'
    cfg_path = "/opt/unetlab/data/branding/config.json"
    os.makedirs("/opt/unetlab/data/branding", exist_ok=True)
    with open(cfg_path, 'w', encoding='utf-8') as f:
        f.write(cfg_json)
    
    os.system("chown -R www-data:www-data /opt/unetlab/data/branding 2>/dev/null || true")
    os.system("chmod -R 777 /opt/unetlab/data/branding 2>/dev/null || true")
    print(f"  [✔] Updated {cfg_path}")
    print("\n[SUCCESS] Azam Basha Branding deployed successfully!")
    return True

if __name__ == "__main__":
    deploy_locally()

