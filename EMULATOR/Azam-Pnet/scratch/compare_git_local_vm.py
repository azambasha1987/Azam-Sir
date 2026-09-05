import os
import sys
import hashlib
import json
import subprocess
import paramiko

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

LOCAL_DIR = r"E:\Git\EMULATOR\Azam-Pnet"
GIT_ROOT = r"E:\Git"
VM_HOST = "192.168.1.29"
VM_USER = "root"
VM_PASS = "azam"
VM_PORT = 22
REMOTE_AZAM_PNET = "/opt/azambasha/EMULATOR/Azam-Pnet"

def run_local(cmd, cwd=GIT_ROOT):
    res = subprocess.run(cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip(), res.stderr.strip(), res.returncode

def get_file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 80)
    print("      AZAM-PNET THREE-WAY CONFIGURATION & SYNCHRONIZATION AUDIT      ")
    print("   [1] GitHub Remote  <--->  [2] Local Git Workspace  <--->  [3] Live VM    ")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. GITHUB REMOTE VS LOCAL GIT REPOSITORY
    # -------------------------------------------------------------
    print("\n[A] GITHUB REMOTE VS LOCAL GIT REPOSITORY")
    print("-" * 60)
    run_local("git fetch origin")
    
    local_head, _, _ = run_local("git rev-parse HEAD")
    remote_head, _, _ = run_local("git rev-parse origin/main")
    local_branch, _, _ = run_local("git rev-parse --abbrev-ref HEAD")
    git_status, _, _ = run_local("git status --short", cwd=GIT_ROOT)
    remote_url, _, _ = run_local("git remote get-url origin")

    print(f"  * GitHub Remote URL   : {remote_url}")
    print(f"  * Local Active Branch : {local_branch}")
    print(f"  * Local Git HEAD      : {local_head}")
    print(f"  * GitHub Remote HEAD  : {remote_head}")

    if local_head == remote_head:
        print("  * Local <-> GitHub Sync: [100% IN SYNC] Local HEAD matches origin/main exactly.")
    else:
        print("  * Local <-> GitHub Sync: [DIVERGED]")
        unpushed, _, _ = run_local("git log --oneline origin/main..HEAD")
        if unpushed:
            print(f"    - Unpushed local commits to GitHub:\n{unpushed}")
        unpulled, _, _ = run_local("git log --oneline HEAD..origin/main")
        if unpulled:
            print(f"    - Unpulled commits from GitHub:\n{unpulled}")

    uncommitted = [l for l in git_status.splitlines() if not l.endswith('.pyc') and 'compare_git_local_vm.py' not in l]
    if not uncommitted:
        print("  * Working Tree Status : [CLEAN] No uncommitted modifications.")
    else:
        print("  * Working Tree Status : [UNCOMMITTED CHANGES PRESENT]:")
        for line in uncommitted:
            print(f"    {line}")

    # -------------------------------------------------------------
    # 2. CONNECT TO LIVE VM
    # -------------------------------------------------------------
    print("\n[B] LIVE VM CONNECTION & GIT REPOSITORY AUDIT")
    print("-" * 60)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(VM_HOST, port=VM_PORT, username=VM_USER, password=VM_PASS, timeout=10)
        print(f"  [OK] Successfully connected via SSH to {VM_USER}@{VM_HOST}:{VM_PORT}")
    except Exception as e:
        print(f"  [FAILED] Could not connect to VM: {e}")
        return

    def exec_vm(cmd):
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        code = stdout.channel.recv_exit_status()
        return out, err, code

    vm_git_head, _, _ = exec_vm("cd /opt/azambasha && git rev-parse HEAD")
    vm_git_branch, _, _ = exec_vm("cd /opt/azambasha && git rev-parse --abbrev-ref HEAD")
    vm_git_status, _, _ = exec_vm("cd /opt/azambasha && git status --short")
    
    print(f"  * VM Repo Location    : /opt/azambasha")
    print(f"  * VM Branch           : {vm_git_branch}")
    print(f"  * VM Git HEAD         : {vm_git_head}")

    if vm_git_head == local_head:
        print("  * VM Git Sync Status  : [100% IN SYNC] VM Git HEAD matches Local Git & GitHub.")
    else:
        print(f"  * VM Git Sync Status  : [BEHIND / DIFFERENT]")
        diff_commits, _, _ = exec_vm(f"cd /opt/azambasha && git log --oneline {vm_git_head}..origin/main 2>/dev/null || git log --oneline -n 5")
        local_missing_commits, _, _ = run_local(f"git log --oneline {vm_git_head}..HEAD")
        print(f"    - Commits present in GitHub & Local but MISSING on VM ({len(local_missing_commits.splitlines())} commits):")
        for c in local_missing_commits.splitlines():
            print(f"        + {c}")

    if not vm_git_status:
        print("  * VM Working Tree     : [CLEAN] No uncommitted local edits on VM.")
    else:
        print(f"  * VM Working Tree     : [MODIFIED ON VM]:\n{vm_git_status}")

    # -------------------------------------------------------------
    # 3. FILE-BY-FILE COMPARISON: LOCAL EMULATOR/Azam-Pnet vs VM /opt/azambasha/EMULATOR/Azam-Pnet
    # -------------------------------------------------------------
    print("\n[C] FILE-BY-FILE COMPARISON (Local Azam-Pnet vs VM /opt/azambasha/EMULATOR/Azam-Pnet)")
    print("-" * 60)
    
    # Get remote file list with md5sums from VM
    vm_md5_raw, _, _ = exec_vm(f"cd {REMOTE_AZAM_PNET} 2>/dev/null && find . -type f ! -path '*/.git*' ! -path '*/__pycache__*' ! -path '*/scratch*' -exec md5sum {{}} +")
    vm_files = {}
    for line in vm_md5_raw.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            m = parts[0]
            f = " ".join(parts[1:]).lstrip("./").replace("\\", "/")
            vm_files[f] = m

    local_files = {}
    for root, dirs, files in os.walk(LOCAL_DIR):
        if ".git" in root or "__pycache__" in root or "scratch" in root:
            continue
        for f in files:
            if f.endswith(('.pyc', '.tmp', '.log')):
                continue
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, LOCAL_DIR).replace("\\", "/")
            local_files[rel_p] = get_file_md5(full_p)

    missing_on_vm = []
    modified_on_vm = []
    extra_on_vm = []
    matching_files = []

    for rel_p, l_md5 in local_files.items():
        if rel_p not in vm_files:
            missing_on_vm.append(rel_p)
        elif vm_files[rel_p] != l_md5:
            modified_on_vm.append(rel_p)
        else:
            matching_files.append(rel_p)

    for r_file in vm_files:
        if r_file not in local_files:
            extra_on_vm.append(r_file)

    print(f"  * Total Local Files in Azam-Pnet  : {len(local_files)}")
    print(f"  * Total VM Files in Azam-Pnet     : {len(vm_files)}")
    print(f"  * Exact Matching Identical Files  : {len(matching_files)}")
    print(f"  * Files Missing on VM             : {len(missing_on_vm)}")
    print(f"  * Files Differing in Content on VM: {len(modified_on_vm)}")
    print(f"  * Extra Files Only on VM          : {len(extra_on_vm)}")

    if modified_on_vm:
        print("\n  [!] Specific files with content differences between Local and VM:")
        for f in modified_on_vm:
            print(f"      - {f}")

    if missing_on_vm:
        print("\n  [!] Specific files missing on VM:")
        for f in missing_on_vm:
            print(f"      - {f}")

    # -------------------------------------------------------------
    # 4. RUNTIME SYSTEM CONFIGURATION COMPARISON ON VM
    # -------------------------------------------------------------
    print("\n[D] LIVE VM RUNTIME CONFIGURATION INSPECTION")
    print("-" * 60)
    
    # 1. Netplan / Network
    netplan_cfg, _, _ = exec_vm("cat /etc/netplan/*.yaml 2>/dev/null || cat /etc/netplan/*.yml 2>/dev/null")
    print("  1. Netplan Bridge Configuration (/etc/netplan/):")
    for l in netplan_cfg.splitlines():
        print(f"       {l}")

    # 2. Apache & PHP-FPM
    apache_modules, _, _ = exec_vm("apache2ctl -M 2>/dev/null | grep -E 'mpm|proxy_fcgi|rewrite'")
    php_fpm_status, _, _ = exec_vm("systemctl is-active php8.5-fpm 2>/dev/null || systemctl is-active php*-fpm 2>/dev/null || echo 'inactive'")
    print(f"\n  2. Web Server Configuration:")
    print(f"       * Apache Active Modules: {', '.join([m.strip() for m in apache_modules.splitlines()])}")
    print(f"       * PHP-FPM Engine Status: {php_fpm_status.strip()}")

    # 3. Installed Packages & Versions
    pnet_packages, _, _ = exec_vm("dpkg -l | grep -E 'pnetlab|unetlab|azambasha'")
    print(f"\n  3. Core Packages Installed on VM:")
    for p in pnet_packages.splitlines():
        print(f"       {p}")

    # 4. Active Services
    services_check, _, _ = exec_vm("systemctl is-active apache2 mysql docker guacd pnetlab-satellited 2>/dev/null")
    service_names = ["apache2", "mysql/mariadb", "docker", "guacd", "pnetlab-satellited"]
    print(f"\n  4. Critical Services Status:")
    for name, status in zip(service_names, services_check.splitlines()):
        print(f"       * {name:20s}: {status}")

    client.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
