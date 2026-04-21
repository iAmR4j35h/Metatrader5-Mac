# How to Change MetaTrader 5 Data Folder Location

When running MetaTrader 5 on macOS (via Wine/CrossOver/Parallels), you might want to change the data folder location for easier access or backup purposes.

## Why Change the Data Folder?

- **Easier access** to MQL5 files from macOS
- **Backup** your EAs, indicators, and settings
- **Multiple MT5 instances** with separate data
- **Share data** between Wine/VM and macOS

---

## Method 1: Using Portable Mode (Recommended)

The easiest way is to run MT5 in "portable" mode, which stores all data in the installation folder.

### Step 1: Create Portable Installation

1. **Download MT5 installer** from your broker or [MetaQuotes](https://www.metatrader5.com/)

2. **Install to a custom location:**
   ```bash
   # Example: Install to your Documents folder
   ~/Documents/MT5_Portable/
   ```

3. **Create a `portable` subfolder:**
   ```bash
   mkdir -p ~/Documents/MT5_Portable/portable
   ```

4. **Move or copy** these folders from the default data folder:
   - `MQL5/` (Experts, Indicators, Scripts)
   - `config/` (terminal.ini, etc.)
   - `profiles/` (chart templates)
   - `history/` (downloaded data)

### Step 2: Launch in Portable Mode

**On Windows/VM:**
```cmd
# Create a shortcut with this target:
"C:\MT5_Portable\terminal64.exe" /portable
```

**On macOS with Wine/CrossOver:**
```bash
# In CrossOver, edit the bottle configuration:
# 1. Right-click MT5 bottle → Run Command
# 2. Browse to: ~/Documents/MT5_Portable/terminal64.exe
# 3. Add argument: /portable

# Or via command line:
wine ~/Documents/MT5_Portable/terminal64.exe /portable
```

---

## Method 2: Change Default Data Folder Path

### Step 1: Find Current Data Folder

**In MT5:**
- File → Open Data Folder
- Note the path (e.g., `C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<ID>`)

### Step 2: Create Symbolic Link (macOS/Linux)

If running in Wine/CrossOver:

```bash
# 1. Move existing data to new location
mv "~/Library/Application Support/CrossOver/Bottles/MT5/drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/<ID>" \
   ~/Documents/MT5_Data/

# 2. Create symbolic link
ln -s ~/Documents/MT5_Data \
   "~/Library/Application Support/CrossOver/Bottles/MT5/drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/<ID>"
```

### Step 3: For Windows VM

In Windows (VM or native):

```cmd
# Run as Administrator
# 1. Move folder
move "C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<ID>" \
     "D:\MT5_Data"

# 2. Create junction (symbolic link)
mklink /J "C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<ID>" \
         "D:\MT5_Data"
```

---

## Method 3: Modify Registry (Windows Only)

⚠️ **Advanced users only**

1. Open Registry Editor (`regedit`)
2. Navigate to:
   ```
   HKEY_CURRENT_USER\Software\MetaQuotes\Terminal
   ```
3. Modify `DataPath` value to your new location

---

## Method 4: Use Different Terminal Instances

### Create Multiple MT5 Installations

Each MT5 instance can have its own data folder:

```bash
# Create folders for multiple instances
mkdir -p ~/MT5/Instance1
mkdir -p ~/MT5/Instance2

# Copy terminal.exe to each
# Each will create its own data folder on first run
```

---

## Common Paths on macOS

### Default CrossOver Paths:

```
# Bottle location:
~/Library/Application Support/CrossOver/Bottles/<bottle_name>/

# MT5 executable:
.../drive_c/Program Files/MetaTrader 5/terminal64.exe

# MT5 data folder:
.../drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/<ID>/
```

### Default Parallels Paths:

```
# Windows VM:
/Users/<user>/Parallels/<VM_Name>.pvm/

# Within VM:
C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<ID>
```

---

## Recommended Setup for macOS Users

### Option A: Portable Mode (Easiest)

```
~/Documents/MT5_Trading/
├── portable/              ← All data here
│   ├── MQL5/
│   │   ├── Experts/
│   │   │   └── MT5Bridge/
│   │   │       └── MT5BridgeClient.mq5
│   │   ├── Indicators/
│   │   └── Scripts/
│   ├── config/
│   ├── profiles/
│   └── history/
├── terminal64.exe
└── metaeditor64.exe
```

**Access from macOS Finder:**
- Simply open `~/Documents/MT5_Trading/portable/MQL5/Experts/`

### Option B: Symbolic Link

```bash
# 1. Create macOS-accessible folder
mkdir -p ~/Documents/MT5_Data

# 2. Find MT5 data folder ID
# (In MT5: File → Open Data Folder, note the long hex string at end)

# 3. Backup original
mv "~/Library/Application Support/CrossOver/Bottles/MT5/drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/<ID>" \
   "~/Library/Application Support/CrossOver/Bottles/MT5/drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/<ID>_backup"

# 4. Create symlink
ln -s ~/Documents/MT5_Data \
   "~/Library/Application Support/CrossOver/Bottles/MT5/drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/<ID>"

# 5. Copy data to new location
cp -r "~/Library/Application Support/CrossOver/Bottles/MT5/drive_c/users/crossover/AppData/Roaming/MetaQuotes/Terminal/<ID>_backup/"* \
   ~/Documents/MT5_Data/
```

---

## Copying the Bridge EA

After changing data folder, copy the bridge EA:

```bash
# Create directory structure
mkdir -p ~/Documents/MT5_Data/MQL5/Experts/MT5Bridge

# Copy the EA
cp /Users/r4j35h/Documents/Projects/MT5-Reverse/MQL5/Experts/MT5Bridge/MT5BridgeClient.mq5 \
   ~/Documents/MT5_Data/MQL5/Experts/MT5Bridge/

# Now open in MetaEditor and compile
```

---

## Quick Reference: Finding Your Data Folder

### In MetaTrader 5:
1. Click **File** → **Open Data Folder**
2. This opens the data folder in Windows Explorer/Finder
3. Note the path shown in the address bar

### Via Terminal:

```bash
# Find all MT5 data folders on macOS:
find ~/Library/Application\ Support -name "terminal.exe" -o -name "terminal64.exe" 2>/dev/null

# Find MT5 data folders:
find ~/Library/Application\ Support -type d -name "Terminal" 2>/dev/null | grep MetaQuotes

# List all MT5 instances:
ls -la ~/Library/Application\ Support/CrossOver/Bottles/*/drive_c/users/*/AppData/Roaming/MetaQuotes/Terminal/
```

---

## Troubleshooting

### Issue: MT5 Can't Find Data After Moving

**Solution:** Check permissions:
```bash
# Fix permissions on macOS
chmod -R 755 ~/Documents/MT5_Data
```

### Issue: Bridge EA Not Showing in Navigator

**Solution:** Refresh in MT5:
1. Right-click in Navigator window
2. Click **Refresh**
3. Or press **F5**

### Issue: Settings Reset After Moving

**Solution:** Copy entire Terminal folder, not just MQL5:
```bash
# Copy everything
cp -r <old_path>/Terminal/<ID>/* <new_path>/
```

---

## Best Practices

1. **Always backup** before moving data
2. **Use portable mode** for easy management
3. **Keep MQL5 folder** in version control (Git) for your EAs
4. **Document your paths** for future reference
5. **Test** after moving to ensure everything works

---

## Example: Complete Setup Script

```bash
#!/bin/bash
# setup_mt5_macos.sh

MT5_DIR="$HOME/Documents/MT5_Portable"
REPO_DIR="$HOME/Documents/Projects/MT5-Reverse"

# Create portable MT5 structure
mkdir -p "$MT5_DIR/portable/MQL5/Experts/MT5Bridge"
mkdir -p "$MT5_DIR/portable/config"

# Copy Bridge EA
cp "$REPO_DIR/MQL5/Experts/MT5Bridge/MT5BridgeClient.mq5" \
   "$MT5_DIR/portable/MQL5/Experts/MT5Bridge/"

echo "MT5 portable setup complete!"
echo "Data folder: $MT5_DIR/portable/"
echo "Bridge EA: $MT5_DIR/portable/MQL5/Experts/MT5Bridge/MT5BridgeClient.mq5"
```

---

**Need more help?** Check the [MetaTrader 5 documentation](https://www.mql5.com/en/docs) or open an issue on [GitHub](https://github.com/iAmR4j35h/Metatrader5-Mac/issues).
