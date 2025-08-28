**WireGuard VPN Setup (Ubuntu Host, Mac Client) with PostgreSQL & Remote Desktop Access**

---

### 🔧 STEP-BY-STEP SETUP LOG

#### **1. Install WireGuard on Ubuntu Server (192.168.68.59)**

Installs the WireGuard VPN software.

```bash
sudo apt update
sudo apt install wireguard
```

#### **2. Generate Server Keys**

Generates private/public key pair for secure communication.

```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

#### **3. Create Server Config (**\`\`**)**

Defines the VPN interface settings and peer (Mac client).

```ini
[Interface]
PrivateKey = <server-private-key>
Address = 10.0.0.1/24
ListenPort = 51820
SaveConfig = true
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eno1 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eno1 -j MASQUERADE

[Peer]
PublicKey = <mac-public-key>
AllowedIPs = 10.0.0.2/32
```

#### **4. Enable IP Forwarding**

Allows the server to route packets from the VPN.

```bash
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### **5. Start WireGuard Service**

Brings up the VPN tunnel.

```bash
sudo systemctl start wg-quick@wg0
sudo systemctl enable wg-quick@wg0
```

---

#### **6. Install WireGuard on MacBook**

GUI client to manage VPN connections.

- Download from App Store
- Create new tunnel config:

```ini
[Interface]
PrivateKey = <mac-private-key>
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = <server-public-key>
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = <your-public-ip>:51820
PersistentKeepalive = 25
```

#### **7. Start Tunnel on Mac**

Launches the VPN connection.

- Launch WireGuard app
- Activate the tunnel

#### **8. Verify Handshake**

Confirms that the tunnel is active.

```bash
sudo wg
```

Look for `latest handshake` under `[Peer]`.

#### **9. Enable NAT Routing**

Required to route traffic out to the LAN from the VPN tunnel.

- Already handled by `PostUp` and `PostDown` in config.

---

### 💡 BONUS CONFIGURATION: PostgreSQL Access from Mac

#### **PostgreSQL Server (192.168.68.55)**

\`\`**:**

```conf
listen_addresses = '*'
```

\`\`**:**

```conf
host    all             all             10.0.0.0/24         md5
```

**Restart PostgreSQL:**

```bash
sudo systemctl restart postgresql
```

**Test from Mac:**

```bash
psql -h 192.168.68.55 -U andrew -d lawnstore
```

---

### 🖥️ REMOTE DESKTOP VIA VNC (Ubuntu with Xorg, Mac Viewer)

#### **1. Switch to Ubuntu on Xorg (Not Wayland)**

Allows `x11vnc` to work correctly.

- On login screen → Click gear icon → Choose **"Ubuntu on Xorg"** → Login

#### **2. Install and Configure x11vnc**

```bash
sudo apt install x11vnc
x11vnc -storepasswd
```

Creates a password file at `~/.vnc/passwd`

#### **3. Run x11vnc**

```bash
x11vnc -usepw -display :0
```

Starts the VNC server for current desktop session

#### **4. (Optional) Auto-Start on Login**

```bash
mkdir -p ~/.config/autostart
cat <<EOF > ~/.config/autostart/x11vnc.desktop
[Desktop Entry]
Type=Application
Exec=x11vnc -usepw -forever -display :0
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Start VNC Server
EOF
```

Ensures VNC starts automatically with the desktop session.

#### **5. Connect from Mac**

Use built-in **Screen Sharing** app:

```bash
open vnc://10.0.0.1:5900
```

- Enter password when prompted
- Go to **View > Enter Full Screen** for fullscreen access

#### **6. Create Desktop Shortcut on Mac**

To easily reconnect:

- Open Safari and enter: `vnc://10.0.0.1:5900`
- Press Enter (launches Screen Sharing)
- Drag the address bar icon to your Desktop to create a shortcut

---

### 🔒 FINAL RESULT: Secure VPN with Remote GUI & DB Access

You now have:

- A **private VPN tunnel** from Mac to Ubuntu
- **Local network access** to internal services (e.g. PostgreSQL)
- **Full remote desktop GUI access** via VNC (X11-based session)
- No ports exposed to the public internet

---

### 🤔 Real-World Capabilities Enabled

#### ✅ Examples:

- SSH into server: `ssh andrew@10.0.0.1`
- Access PostgreSQL with DBeaver or `psql`
- Use browser to test local Flask apps: `http://10.0.0.1:5000`
- Remotely manage Linux GUI over VNC
- Set up internal web dashboards or admin tools
- Sync files over SFTP or Samba within VPN

This setup is suitable for:

- Self-hosted dev environments
- Small business IT management
- Remote access to LAN resources
