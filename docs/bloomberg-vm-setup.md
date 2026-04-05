# Bloomberg DAPI on macOS via Parallels VM

Source: [BLPAPI SDK — Testing DAPI on macOS](https://bbgithub.dev.bloomberg.com/pages/apisdk/blpapi-docs/int/BLPAPI%20Development%20Tools%20%26%20Guide/SDLC/dapi-on-mac/)

Connect to Bloomberg's Desktop API (DAPI) from macOS by running Bloomberg Terminal
inside a Windows VM and forwarding the BLPAPI port over SSH.

## Architecture

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  macOS (Host)           │         │  Windows VM (Parallels)      │
│                         │  SSH    │                              │
│  Python + blpapi  ──────┼────────►│  bbcomm (:8194)              │
│  localhost:8194         │  tunnel │  Bloomberg Terminal           │
│                         │         │  OpenSSH Server               │
└─────────────────────────┘         └──────────────────────────────┘
```

DAPI only binds to `127.0.0.1` (localhost) — it does not listen on external
interfaces. You **cannot** connect directly to the VM's IP on port 8194.
An SSH tunnel forwards macOS `localhost:8194` to the VM's `localhost:8194`
where bbcomm is actually listening.

---

## Step 1: Install Windows in Parallels

1. Follow the [Setting up a Parallels Virtual Machine](https://bbgithub.dev.bloomberg.com/pages/apisdk/blpapi-docs/) tutorials
2. Create a Windows VM and ensure it is running properly
3. Note the VM's IP address: open Command Prompt in Windows and run `ipconfig`
   - Typically `10.211.55.3` on the Shared Network adapter

### Optional: Install Bloomberg Root CA

Reduces browser SSL warnings inside the VM:

1. Search for "Bloomberg LP Corporate Class1 Root CA G2 V2" on the TEAM page
2. Download the certificate (you can download on macOS and drag to Windows VM)
3. On Windows, open **Manage Computer Certificates** from Start menu
4. Import into **Trusted Root Certification Authorities** → Certificates → right-click → Import

---

## Step 2: Install Bloomberg Terminal & bbcomm

Inside the Windows VM:

1. Go to Bloomberg's software download page
2. Install **Bloomberg Terminal**
3. Install **bbcomm** (required for DAPI connections)

**bbcomm logs**: `%temp%\Bloomberg\Log\bbcomm.*.log`

You can also download the demo tool to verify DAPI connectivity within the VM itself.

> **Note**: If this is a one-off test, you can skip the SSH tunnel and run your
> BLPAPI script directly inside the Windows VM. Download the SDK from the
> [public SDK download page](https://www.bloomberg.com/professional/support/api-library/).
> The Windows SDK is x86 only — ensure you use an x86 Python/C# runtime if on ARM.

---

## Step 3: Install and Configure OpenSSH on Windows

Run all commands in **PowerShell as Administrator** inside the VM.

### Install OpenSSH Server

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

### Set up SSH key authentication

On your **Mac**, generate a key if you don't have one:

```bash
ssh-keygen -t ed25519
```

Copy the public key content (`~/.ssh/id_ed25519.pub`), then on **Windows**:

```powershell
# Create the authorized_keys file (must use administrators_authorized_keys
# since the Windows user is an administrator)
New-Item -Path "C:\ProgramData\ssh\administrators_authorized_keys" -ItemType File -Force
notepad C:\ProgramData\ssh\administrators_authorized_keys
# Paste your Mac's public key and save
```

> **Important**: Create the file with `New-Item` first, then open in notepad.
> If you let notepad create it, it will add a `.txt` extension.

### Enable and start the service

```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

### Set the VM's network to private

```powershell
Set-NetConnectionProfile -InterfaceAlias "Ethernet*" -NetworkCategory Private
```

### Verify SSH from macOS

```bash
ssh lliu528@10.211.55.3
```

---

## Step 4: SSH Port Forwarding

From macOS, add your key to the keychain and create the tunnel:

```bash
# Add key to macOS keychain
ssh-add --apple-use-keychain ~/.ssh/id_ed25519

# Establish the SSH tunnel
ssh -F /dev/null \
    -L 8194:127.0.0.1:8194 \
    -N -v lliu528@10.211.55.3
```

### Flag Explanation

| Flag | Purpose |
|------|---------|
| `-F /dev/null` | Bypass `~/.ssh/config` — corporate SSH configs often route through proxies that break the tunnel |
| `-L 8194:127.0.0.1:8194` | Forward local port 8194 to VM's localhost:8194 (bbcomm) |
| `-N` | No remote command — just forward ports |
| `-v` | Verbose output for debugging |

Replace `lliu528` with your Windows username and `10.211.55.3` with your VM's IP.

### Verify the Tunnel

In a separate terminal on macOS:

```bash
nc -z localhost 8194 && echo "Tunnel OK" || echo "Tunnel FAILED"
```

### Background Tunnel (Recommended)

Run the tunnel once and it stays up in the background until the VM shuts down:

```bash
ssh -F /dev/null \
    -L 8194:127.0.0.1:8194 \
    -N -f -o ServerAliveInterval=60 -o ServerAliveCountMax=3 \
    lliu528@10.211.55.3
```

The `-f` flag sends SSH to the background after authentication. Check if it's running:

```bash
lsof -i :8194
```

Kill it when done:

```bash
pkill -f "ssh.*8194.*10.211.55.3"
```

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| SSH connects but hangs | Corporate proxy intercepting | Use `-F /dev/null` to bypass SSH config |
| `Connection refused` on port 22 | OpenSSH not running in VM | Start sshd service (Step 3) |
| `Connection refused` on port 8194 | bbcomm not running | Open Bloomberg Terminal in the VM |
| `Permission denied` | Wrong credentials or key not in `administrators_authorized_keys` | Check Step 3 |
| Tunnel drops after idle | SSH timeout | Add `-o ServerAliveInterval=60` |

---

## Step 5: Run BLPAPI Apps on macOS

With the tunnel active, BLPAPI apps connect to `localhost:8194` — no code changes needed.

```bash
# Run the Bloomberg collector
python3 scripts/bloomberg_collector.py --security "MSFT US Equity" --output output/MSFT/data_pack.md
```

```python
import blpapi

options = blpapi.SessionOptions()
options.setServerHost("localhost")
options.setServerPort(8194)

session = blpapi.Session(options)
if session.start():
    print("Connected to Bloomberg via VM tunnel")
```

---

## Testing DAPI on DEV

For testing against DEV hosts (no production terminal needed).

### 1) Configure BBCOMM route

Create `C:\blp\DAPI\MONITOR.RTE` with:

```
0 aread-pw-538 8194
65 aread-pw-538 8195
# alternatively point to any host in area-ny-dev.bdns.bloomberg.com
# or area-nj-dev.bdns.bloomberg.com if aread-pw-538 is unavailable
```

Open `C:\blp\DAPI\bbconfig.exe`, choose **Route File** and select the `MONITOR.RTE` you created.

### 2) Terminal: disable "Api settings follow terminal settings"

Run `{CONN <GO>}` in the Bloomberg terminal and uncheck **Api settings follow terminal settings**.

**If the popup doesn't show** (common in VMs):

1. Shutdown the Bloomberg terminal
2. Delete these cache folders:
   - `%temp%\Bloomberg\bb2cache`
   - `%localappdata%\Bloomberg\bucache`
3. Relaunch and run `{CONN <GO>}` again

**If that still fails**, edit the registry:
- Run `regedit` → navigate to `HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bloomberg L.P.\Connection Wizard`
- Change `API follows Terminal` from `1` to `0`

### 3) Select a DEV host

Run `{CNNT SDV9 <GO>}` (or another available SUNDEV host).

- If prompted for **Express login**, choose to log off instead
- Log back in and verify via `{VSAT <GO>}`
- First-time login on a new machine/VM: SN replication from Prod to Dev can take up to 24 hours

### 4) Restart bbcomm

```cmd
C:\blp\DAPI\bbstop.exe
C:\blp\DAPI\bbcomm.exe
```

The SSH tunnel setup remains the same — only the bbcomm backend changes.

---

## Quick Reference

```bash
# 1. Start VM (Parallels)
# 2. Open Bloomberg Terminal in VM (starts bbcomm)

# 3. Start SSH tunnel (macOS terminal)
ssh -F /dev/null -L 8194:127.0.0.1:8194 -N -o ServerAliveInterval=60 lliu528@10.211.55.3

# 4. Run your script (separate macOS terminal)
python3 scripts/bloomberg_collector.py --security "AAPL US Equity" --output output/AAPL/data_pack.md
```
