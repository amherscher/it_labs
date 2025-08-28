# Samba Fileshare Lab

**Objective:**  
Configure a Linux server with Samba to provide cross-platform file sharing for Windows, macOS, and Linux clients. Practice user management, permissions, and troubleshooting.

---

## Environment
- **Server:** Ubuntu 22.04 LTS on Dell Optiplex 7080  
- **Service:** Samba (`smbd`/`nmbd`)  
- **Clients:**  
  - Windows 11  
  - macOS Ventura  
  - Ubuntu Desktop  

---

## Installation
```bash
sudo apt update
sudo apt install samba -y

# 1) Share directory
sudo mkdir -p /srv/samba/shared

# 2) Group to control access
sudo groupadd smbshare 2>/dev/null || true

# 3) Ownership & sticky group bit (new files keep group)
sudo chgrp -R smbshare /srv/samba/shared
sudo chmod -R 2770 /srv/samba/shared

# 4) (Optional but nice) Default ACLs so group members always have rwx
sudo setfacl -R -m g:smbshare:rwx /srv/samba/shared
sudo setfacl -R -d -m g:smbshare:rwx /srv/samba/shared
