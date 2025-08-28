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

