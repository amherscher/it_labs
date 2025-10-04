# Ubuntu RAID‑1 Migration & Operations Guide

This document records exactly how we migrated an existing standalone data disk to a mirrored **RAID‑1** array using Linux **mdadm** — without losing data — and how to repeat the process in the future. It also includes verification steps, recovery procedures, and reusable scripts.

> **Scenario (what we did):**
> - **OS drive**: NVMe (`/dev/nvme0n1`) with `/` and `/boot/efi`.
> - **Existing data drive**: 2TB at `/dev/sda1` mounted on `/mnt/data` (had data we must preserve).
> - **New drive**: 2TB at `/dev/sdb1` (blank, to become the mirror).
> - **Goal**: Convert `/mnt/data` into a RAID‑1 array at `/dev/md0` **without wiping existing data**.

---

## 1) Prerequisites & Safety

- You have **backups** of your most important files.
- Install mdadm:
  ```bash
  sudo apt update && sudo apt install -y mdadm
  ```
- Confirm drives (examples below will vary on your system):
  ```bash
  lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINT
  sudo fdisk -l
  ```
- Ensure the **new** disk has a partition (full‑size) marked for RAID:
  ```bash
  # If needed, create /dev/sdb1 and mark it for RAID
  sudo parted /dev/sdb --script mklabel gpt mkpart primary 0% 100%
  sudo parted /dev/sdb --script set 1 raid on
  ```

> **Why not use /dev/sda1 directly?** It contains live data. We first build a **degraded** RAID‑1 with the new disk, copy data into it, then add the old disk as the mirror.

---

## 2) Create a degraded RAID‑1 on the new disk

```bash
# Create md0 using only the new member; "missing" is a placeholder for the 2nd disk
sudo mdadm --create --verbose /dev/md0 \
  --level=1 --raid-devices=2 /dev/sdb1 missing

# Check status
cat /proc/mdstat
sudo mdadm --detail /dev/md0
```

> The "metadata at start" note is expected and fine for data arrays. We are **not** booting from md0.

---

## 3) Create filesystem on md0 and mount it temporarily

```bash
sudo mkfs.ext4 /dev/md0
sudo mkdir -p /mnt/raid1_new
sudo mount /dev/md0 /mnt/raid1_new

# Capture UUID for fstab later
sudo blkid /dev/md0
```

> Prefer OS‑scheduled TRIM (`fstrim.timer`) over mount‑time `discard` for SSDs:
```bash
sudo systemctl enable --now fstrim.timer
```

---

## 4) Sync data from the old mount to the new array (rsync)

Run rsync **at least once fully**, and a quick second pass to catch changes.

```bash
# Close apps writing to /mnt/data (VMs, transfers, etc.)

# First pass (can take a while)
sudo rsync -aHAX --info=progress2 --delete /mnt/data/ /mnt/raid1_new/

# Second pass (should be quick)
sudo rsync -aHAX --delete /mnt/data/ /mnt/raid1_new/
```

**Flags explained:**
- `-a` archive (preserves perms, times, etc.)
- `H` hardlinks, `A` ACLs, `X` xattrs
- `--delete` makes destination an exact mirror (use `--dry-run` if cautious)

**Optional verification before flipping mounts:**
```bash
# Compare file counts & sizes (quick heuristic)
sudo bash -c 'du -sb /mnt/data | cut -f1; du -sb /mnt/raid1_new | cut -f1'
```

---

## 5) Make md0 the live /mnt/data

```bash
# Ensure nothing is using /mnt/data
sudo fuser -vm /mnt/data || true
sudo lsof +f -- /mnt/data || true

# Unmount the old data volume
sudo umount /mnt/data

# Mount the array in its place
sudo mount /dev/md0 /mnt/data

# Confirm
mount | grep " /mnt/data "
df -h /mnt/data
```

### Persist mount in /etc/fstab
Use the UUID you got from `blkid`:
```bash
sudo cp /etc/fstab /etc/fstab.bak
# Replace <UUID> with your md0 UUID
echo 'UUID=<UUID> /mnt/data ext4 noatime,defaults,nofail 0 2' | sudo tee -a /etc/fstab

# Test
sudo mount -a
```

### Persist array config
```bash
sudo cp /etc/mdadm/mdadm.conf /etc/mdadm/mdadm.conf.bak
printf "DEVICE partitions\n" | sudo tee /etc/mdadm/mdadm.conf >/dev/null
sudo mdadm --detail --scan | sudo tee -a /etc/mdadm/mdadm.conf
sudo update-initramfs -u
```

---

## 6) Add the original data partition as the mirror

Now that `/mnt/data` runs from md0, add `/dev/sda1` as the 2nd mirror member.

```bash
# Sanity: sda1 should NOT be mounted
mount | grep sda1 || echo "sda1 not mounted (good)"

# Remove old FS signatures so mdadm can claim it
sudo wipefs -a /dev/sda1

# Add it into the array
sudo mdadm --add /dev/md0 /dev/sda1

# Monitor resync
watch -n2 cat /proc/mdstat
# (Ctrl+C to exit)

# Details
sudo mdadm --detail /dev/md0
```

When complete, `/proc/mdstat` shows `[UU]` for md0 and `mdadm --detail` shows both devices as `active sync`.

---

## 7) Verification Checklist

- `mount | grep /mnt/data` → shows `/dev/md0 on /mnt/data`.
- `cat /proc/mdstat` → shows md0 `[UU]` when finished.
- `sudo mdadm --detail /dev/md0` → both members active, states `clean` or `active`.
- `df -h /mnt/data` → size and usage look right.

---

## 8) Day‑2 Ops: common tasks

### Check array health
```bash
cat /proc/mdstat
sudo mdadm --detail /dev/md0
```

### Trigger a periodic TRIM (if needed)
```bash
sudo fstrim -av
```

### Schedule mdadm email alerts (optional)
Add a mail recipient in `/etc/mdadm/mdadm.conf`:
```conf
MAILADDR root
```
Then ensure a local MTA (like `postfix` in local‑only mode) is set up if you want email.

---

## 9) Drive replacement / failure procedures

> **If a drive fails**, the array stays online (degraded). Replace and rebuild.

### A) Identify and mark bad member
```bash
sudo mdadm --detail /dev/md0
# Suppose /dev/sda1 shows as faulty; mark & remove
sudo mdadm --fail /dev/md0 /dev/sda1
sudo mdadm --remove /dev/md0 /dev/sda1
```

### B) Physically replace disk, partition the new disk
```bash
# Example: new disk appears as /dev/sda
sudo parted /dev/sda --script mklabel gpt mkpart primary 0% 100%
sudo parted /dev/sda --script set 1 raid on
```

### C) Add new member and rebuild
```bash
sudo mdadm --add /dev/md0 /dev/sda1
watch -n2 cat /proc/mdstat
```

---

## 10) Automation Scripts

All scripts assume:
```bash
ARRAY=/dev/md0
SRC=/mnt/data
DEST=/mnt/raid1_new
NEW_PART=/dev/sdb1
OLD_PART=/dev/sda1
```
Adjust variables for your system before running.

### 10.1 Create degraded array on new disk
```bash
#!/usr/bin/env bash
set -euo pipefail
ARRAY=${ARRAY:-/dev/md0}
NEW_PART=${NEW_PART:-/dev/sdb1}

sudo mdadm --create --verbose "$ARRAY" \
  --level=1 --raid-devices=2 "$NEW_PART" missing

cat /proc/mdstat
sudo mdadm --detail "$ARRAY"
```

### 10.2 Format and mount temporary
```bash
#!/usr/bin/env bash
set -euo pipefail
ARRAY=${ARRAY:-/dev/md0}
DEST=${DEST:-/mnt/raid1_new}

sudo mkfs.ext4 "$ARRAY"
sudo mkdir -p "$DEST"
sudo mount "$ARRAY" "$DEST"
sudo blkid "$ARRAY"
```

### 10.3 Sync data reliably (two passes)
```bash
#!/usr/bin/env bash
set -euo pipefail
SRC=${SRC:-/mnt/data}
DEST=${DEST:-/mnt/raid1_new}

sudo rsync -aHAX --info=progress2 --delete "$SRC/" "$DEST/"
sudo rsync -aHAX --delete "$SRC/" "$DEST/"
```

### 10.4 Flip mount to md0 and persist
```bash
#!/usr/bin/env bash
set -euo pipefail
ARRAY=${ARRAY:-/dev/md0}
DEST=${DEST:-/mnt/raid1_new}
LIVE=/mnt/data

# ensure quiet
sudo fuser -vm "$LIVE" || true
sudo umount "$LIVE"
sudo mount "$ARRAY" "$LIVE"

UUID=$(sudo blkid -s UUID -o value "$ARRAY")
sudo cp /etc/fstab /etc/fstab.bak
LINE="UUID=${UUID} ${LIVE} ext4 noatime,defaults,nofail 0 2"
if ! grep -q "$UUID" /etc/fstab; then echo "$LINE" | sudo tee -a /etc/fstab; fi

sudo cp /etc/mdadm/mdadm.conf /etc/mdadm/mdadm.conf.bak
printf "DEVICE partitions\n" | sudo tee /etc/mdadm/mdadm.conf >/dev/null
sudo mdadm --detail --scan | sudo tee -a /etc/mdadm/mdadm.conf
sudo update-initramfs -u
```

### 10.5 Add the original partition as mirror & monitor
```bash
#!/usr/bin/env bash
set -euo pipefail
ARRAY=${ARRAY:-/dev/md0}
OLD_PART=${OLD_PART:-/dev/sda1}

# ensure not mounted
mount | grep "$OLD_PART" && { echo "$OLD_PART is mounted; aborting"; exit 1; } || true

sudo wipefs -a "$OLD_PART"
sudo mdadm --add "$ARRAY" "$OLD_PART"

watch -n2 cat /proc/mdstat
```

### 10.6 Quick health check
```bash
#!/usr/bin/env bash
set -euo pipefail
ARRAY=${ARRAY:-/dev/md0}

cat /proc/mdstat
sudo mdadm --detail "$ARRAY"
```

---

## 11) Troubleshooting

- **mdadm: cannot use /dev/sdX1: Device or resource busy**  
  The partition is mounted or in use. Unmount it (`umount`), close shells or apps in that path, and retry.

- **rsync progress restarts / shows lower %**  
  Normal with `--info=progress2`. Each pass/file set resets the counter. Run a second pass to finish.

- **Boot warnings about md metadata**  
  Only relevant if `/boot` lives on mdadm (not our case). Data arrays are fine with metadata 1.x.

- **TRIM on mdadm**  
  Use `fstrim.timer` (enabled earlier). Mount‑time `discard` isn’t necessary and can hurt performance.

- **After reboot, /mnt/data not mounted**  
  Check `/etc/fstab` UUID line, run `sudo mount -a`, verify `blkid` UUID matches.

---

## 12) Replicating the Process (Checklist)

1. Identify drives; create RAID partition on the **new** disk.
2. Create **degraded** RAID‑1 (`missing` as the second device).
3. Make filesystem; mount array temporarily.
4. `rsync` data (two passes; optional `--dry-run` once).
5. Unmount old mount; mount array at the live path; persist in `/etc/fstab`.
6. Save `/etc/mdadm/mdadm.conf`; `update-initramfs -u`.
7. Add the **old** partition as mirror; monitor until `[UU]`.
8. Verify health; keep (external) backups.

---

### Appendix: Handy one-liners

```bash
# Disk/FS overview
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINT

# Array summary & progress
cat /proc/mdstat
sudo mdadm --detail /dev/md0

# Confirm what backs /mnt/data
mount | grep " /mnt/data "

# Compare sizes quickly
sudo bash -c 'du -sb /mnt/data | cut -f1; du -sb /mnt/raid1_new | cut -f1'
```

---

**End of Guide** — You now have a documented, repeatable process for safe RAID‑1 migration, ongoing ops, and recovery.

