# ag-03 — Wayland DRM + VNC

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern

## Goal

Replace Xorg with a Wayland compositor (Weston) using DRM master (hardware GPU, not Pixman software renderer), with VNC access from phone.

## Context

- System runs lightdm + Xorg currently, holding DRM master
- Weston 13.0.0 installed, supports `--backend=drm` (hardware) and `--backend=vnc`
- Certs already generated at `certs/cert.pem` and `certs/key.pem`
- Previous attempt used `--backend=vnc` alone (Pixman software, no DRM) — documented but server not actually started
- Connection is SSH from phone — stopping lightdm won't kill SSH
- **Weston is currently running** with `--backends=drm,vnc` on port 5900
- **Auth problem**: VNC client connects, TLS works, but PAM rejects login even with correct password
- Log shows: `VNC: wrong user 'vuos'`
- Password set to `p999` (simple, for testing) — confirmed working in terminal with `sudo`
- PAM service: `/etc/pam.d/weston-remote-access` includes `login`
- VNC client sends username + password but gets rejected
- Not a keyboard layout issue — simple password without special chars

## Task

### 1. Check current state
- Is lightdm running? (`systemctl status lightdm`)
- Who holds DRM master? (`cat /sys/class/drm/card*/device/gpu_busy_percent`, `ps aux | grep -E "Xorg|lightdm"`)
- Is port 5900 free?

### 2. Stop Xorg/lightdm
Use sudo in a separate tmux window:
```
tmux new-window -n sudo-stop -d
tmux send-keys -t sudo-stop "sudo systemctl stop lightdm" Enter
```
Wait for Xorg to exit. Verify DRM master is free.

### 3. Start Weston with DRM + VNC backends
Weston supports `--backends` with comma-separated list:
```
weston --backends=drm,vnc \
  --vnc-tls-cert=/home/vuos/code/p4/e003-wayland-migration/ag-03/certs/cert.pem \
  --vnc-tls-key=/home/vuos/code/p4/e003-wayland-migration/ag-03/certs/key.pem \
  --port=5900 \
  --width=1280 --height=720 \
  > /tmp/weston-vnc.log 2>&1 &
```
If `--backends=drm,vnc` fails, try `--backend=drm` alone first, then `--backend=vnc` with DRM free.

### 4. Verify
- Check port 5900 is listening: `ss -tlnp | grep 5900`
- Check weston process is running
- Try connecting: `timeout 5 vncviewer --tls localhost:5900` (or similar)
- Log output: `cat /tmp/weston-vnc.log`

### 5. Fix terminal app in VNC session
- VNC user clicks the terminal icon in Weston panel but nothing happens
- weston-terminal is installed but might not launch due to permissions or socket access
- Weston runs as root (UID 0) but the shell/user context might need adjustment
- Diagnose: run `WAYLAND_DISPLAY=wayland-1 weston-terminal` from SSH and check errors
- Fix so that clicking the terminal icon (or launching any app) works in the VNC session

### 6. Install desktop panel + app launcher
Weston's default `desktop-shell` is too minimal. Install and configure:

1. **Waybar** — panel con:
   - Menú inicio (wofi como módulo personalizado)
   - Lanzadores rápidos (navegador, terminal, editor, etc.)
   - Bandeja del sistema (Bluetooth, red, teclado, sonido, reloj)
   - Workspaces

2. **wofi** — launcher tipo menú inicio con categorías

3. **Apps recomendadas** para el panel:
   - Navegador: `epiphany` (GNOME Web) o `firefox` (Wayland)
   - Editor código: `gedit` o `kate`
   - Terminal: `weston-terminal` (ya instalado)
   - Configuración: `gnome-control-center` o similar
   - Gestor de archivos: `nautilus` o `thunar`

4. **weston.ini** — configurar autostart de waybar y wofi

### 7. Document
Update `vnc-setup.md` with:
- DRM replacement steps
- How to start/stop the compositor
- Connection details
- How to revert (restart lightdm)

## Self-command
After reading, execute immediately. ALL commands: `>/dev/null 2>&1 &`. Self-wake to continue.
