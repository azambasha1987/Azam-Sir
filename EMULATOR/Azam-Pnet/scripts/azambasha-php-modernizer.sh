#!/usr/bin/env bash
# ==============================================================================
# PNetLab PHP 8.4 / 8.5 Runtime & API Modernizer for Ubuntu 26+ (Resolute)
# Injects #[AllowDynamicProperties] into core UNetLab and Slim framework classes,
# tunes PHP-FPM OPcache/memory limits, and stabilizes HTTP/HTTPS session cookies.
# ==============================================================================
set -euo pipefail

echo "============================================================"
echo "    [2/4] Modernizing PHP 8.4/8.5 Engine & Configurations..."
echo "============================================================"

# 1. Detect Installed PHP Version
PHP_VER="$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;' 2>/dev/null || echo "8.5")"
echo "      -> Detected PHP Runtime: PHP ${PHP_VER}"

# 2. Inject #[AllowDynamicProperties] into Core UNetLab & Slim Classes
echo "      -> Patching PHP classes with #[AllowDynamicProperties]..."
python3 - << 'PYEOF'
import os, re

# The pnetlab .deb ships PHP files with #[\AllowDynamicProperties] (note the backslash).
# PHP 8.2+ treats this as a PHP attribute identical to #[AllowDynamicProperties].
# PHP 8.5 fatal-errors if the attribute appears more than once on the same class.
# We must use exact string matching (not regex) because the backslash confuses patterns.

ATTR_BS  = '#[\\AllowDynamicProperties]'   # with backslash (as shipped by .deb)
ATTR_PLAIN = '#[AllowDynamicProperties]'    # without backslash (injected by us)

class_regex = re.compile(r'^(class\s+[A-Za-z0-9_]+)', re.MULTILINE)

target_dirs = [
    "/opt/unetlab/html/includes",
    "/opt/unetlab/html/includes/Slim",
    "/opt/unetlab/html/includes/models",
]

deduped = 0
injected = 0

for target_dir in target_dirs:
    if not os.path.isdir(target_dir):
        continue
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules')]
        for fname in files:
            if not fname.endswith('.php'):
                continue
            fpath = os.path.join(root, fname)
            try:
                content = open(fpath, encoding='utf-8', errors='ignore').read()
                changed = False

                # ── Pass 1: Deduplicate #[\AllowDynamicProperties] (backslash form) ──
                if content.count(ATTR_BS) > 1:
                    first = content.find(ATTR_BS)
                    content = content[:first + len(ATTR_BS)] + \
                              content[first + len(ATTR_BS):].replace(ATTR_BS, '')
                    changed = True
                    deduped += 1

                # ── Pass 2: Deduplicate #[AllowDynamicProperties] (plain form) ────────
                if content.count(ATTR_PLAIN) > 1:
                    first = content.find(ATTR_PLAIN)
                    content = content[:first + len(ATTR_PLAIN)] + \
                              content[first + len(ATTR_PLAIN):].replace(ATTR_PLAIN, '')
                    changed = True

                # ── Pass 3: Inject into files that have neither form yet ──────────────
                has_attr = (ATTR_BS in content) or (ATTR_PLAIN in content)
                if not has_attr:
                    def repl(m):
                        global injected
                        injected += 1
                        return ATTR_PLAIN + '\n' + m.group(1)
                    new_content = class_regex.sub(repl, content, count=1)
                    if new_content != content:
                        content = new_content
                        changed = True

                if changed:
                    open(fpath, 'w', encoding='utf-8').write(content)
            except Exception as e:
                print(f"  SKIP {fpath}: {e}")

print(f"  Deduplicated: {deduped} file(s)")
print(f"  Injected attr: {injected} file(s)")
PYEOF


# 3. Ensure Session Cookie Compatibility in api.php
API_PHP="/opt/unetlab/html/api.php"
if [ -f "$API_PHP" ]; then
    sed -i 's/"secure" *=> *true/"secure" => (!empty($_SERVER["HTTPS"]) \&\& $_SERVER["HTTPS"] !== "off")/g' "$API_PHP" 2>/dev/null || true
    sed -i 's/"samesite" *=> *"Strict"/"samesite" => "Lax"/g' "$API_PHP" 2>/dev/null || true
    echo "      -> Modernized session cookie attributes in api.php"
fi

# 4. Tune PHP-FPM and PHP CLI Configurations
for conf in /etc/php/${PHP_VER}/fpm/php.ini /etc/php/${PHP_VER}/cli/php.ini /etc/php/*/*/php.ini; do
    if [ -f "$conf" ]; then
        sed -i 's/^memory_limit = .*/memory_limit = 2048M/' "$conf" 2>/dev/null || true
        sed -i 's/^upload_max_filesize = .*/upload_max_filesize = 100G/' "$conf" 2>/dev/null || true
        sed -i 's/^post_max_size = .*/post_max_size = 100G/' "$conf" 2>/dev/null || true
        sed -i 's/^max_execution_time = .*/max_execution_time = 3600/' "$conf" 2>/dev/null || true
        sed -i 's/^max_input_time = .*/max_input_time = 3600/' "$conf" 2>/dev/null || true
        sed -i 's/^;max_input_vars = .*/max_input_vars = 100000/' "$conf" 2>/dev/null || true
        sed -i 's/^max_input_vars = .*/max_input_vars = 100000/' "$conf" 2>/dev/null || true
        sed -i 's/^error_reporting = .*/error_reporting = E_ALL \& ~E_DEPRECATED \& ~E_NOTICE \& ~E_USER_DEPRECATED/' "$conf" 2>/dev/null || true
        
        # OPcache Settings & JIT Compiler
        sed -i 's/^;*opcache.enable=.*/opcache.enable=1/' "$conf" 2>/dev/null || true
        sed -i 's/^;*opcache.enable_cli=.*/opcache.enable_cli=1/' "$conf" 2>/dev/null || true
        sed -i 's/^;*opcache.memory_consumption=.*/opcache.memory_consumption=512/' "$conf" 2>/dev/null || true
        sed -i 's/^;*opcache.interned_strings_buffer=.*/opcache.interned_strings_buffer=64/' "$conf" 2>/dev/null || true
        sed -i 's/^;*opcache.max_accelerated_files=.*/opcache.max_accelerated_files=50000/' "$conf" 2>/dev/null || true
        sed -i 's/^;*opcache.revalidate_freq=.*/opcache.revalidate_freq=2/' "$conf" 2>/dev/null || true
        sed -i 's/^;*opcache.jit=.*/opcache.jit=tracing/' "$conf" 2>/dev/null || true
        sed -i 's/^;*opcache.jit_buffer_size=.*/opcache.jit_buffer_size=64M/' "$conf" 2>/dev/null || true
        grep -q "opcache.jit=tracing" "$conf" || echo "opcache.jit=tracing" >> "$conf" 2>/dev/null || true
        grep -q "opcache.jit_buffer_size=64M" "$conf" || echo "opcache.jit_buffer_size=64M" >> "$conf" 2>/dev/null || true
    fi
done
echo "      -> Applied high-performance OPcache JIT Tracing (64MB), 2GB memory, and 100GB upload limits"

# 5. Restart All Active PHP-FPM Services
for svc in $(systemctl list-units --type=service --state=running 2>/dev/null | grep -o 'php[0-9.]*-fpm' | sort -u); do
    systemctl restart "$svc" 2>/dev/null || true
done

echo "============================================================"
echo "    [SUCCESS] PHP 8.3/8.4/8.5+ Engine & Runtime Modernized! "
echo "============================================================"
