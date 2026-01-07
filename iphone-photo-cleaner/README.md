# iPhone Photo Cleaner - Retro Edition

A nostalgic Windows 95 / Mac OS 9 styled app to batch delete old photos from your iPhone.

```
╔══════════════════════════════════════════════════════════════╗
║           iPhone Photo Cleaner - Retro Edition               ║
║                   Est. 1995 Aesthetics                       ║
╚══════════════════════════════════════════════════════════════╝
```

## Features

- **Retro UI** - Classic Windows 95/Mac OS 9 look with beveled buttons, navy title bar, and gray backgrounds
- **Date-based filtering** - Select a cutoff date and find all photos older than that
- **Thumbnail preview** - See previews of photos before deleting (first 100 shown)
- **Dry run mode** - Test what would be deleted without actually removing files (enabled by default)
- **HEIC support** - View iPhone's native HEIC format thumbnails
- **Video support** - Also finds and deletes MOV/MP4 videos
- **Progress tracking** - Retro-styled progress dialogs
- **Safety features** - Double confirmation before actual deletion

## Installation

### 1. Install Python dependencies

```bash
cd ~/utils/iphone-photo-cleaner
pip install -r requirements.txt
```

Or install individually:

```bash
pip install pymobiledevice3 Pillow pillow-heif
```

### 2. macOS permissions

You may need to grant terminal/Python access to USB devices. If you get permission errors:

```bash
# Try running with sudo
sudo python iphone_photo_cleaner.py
```

Or go to **System Preferences > Security & Privacy > Privacy** and ensure Terminal has necessary permissions.

## Usage

### 1. Connect your iPhone

1. Plug iPhone into Mac via USB cable
2. **Unlock your iPhone**
3. Tap **"Trust"** when prompted on the iPhone
4. Enter your passcode if asked

### 2. Run the app

```bash
cd ~/utils/iphone-photo-cleaner
python iphone_photo_cleaner.py
```

### 3. Using the UI

```
┌─────────────────────────────────────────────────────────────┐
│ 📱 iPhone Photo Cleaner                        [─] [□] [✕]  │
├─────────────────────────────────────────────────────────────┤
│ File  Edit  View  Help                                      │
├─────────────────────────────────────────────────────────────┤
│ 🔴 Status │ [Connect] │ Date: [Month][Day][Year] │ [Scan]  │
├───────────┬─────────────────────────────────────────────────┤
│ Stats     │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               │
│           │  │ IMG │ │ IMG │ │ IMG │ │ IMG │               │
│ Total: 0  │  └─────┘ └─────┘ └─────┘ └─────┘               │
│ Selected: │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               │
│ Size: 0MB │  │ IMG │ │ IMG │ │ IMG │ │ IMG │               │
│           │  └─────┘ └─────┘ └─────┘ └─────┘               │
│ [Select]  │                                                 │
│ [Deselect]│                                                 │
│           │                                                 │
│ ☑ Dry Run │                                                 │
│           │                                                 │
│ [DELETE]  │                                                 │
├───────────┴─────────────────────────────────────────────────┤
│ Ready.                                             10:45 PM │
└─────────────────────────────────────────────────────────────┘
```

**Step by step:**

1. Click **"Connect iPhone"** - wait for green status
2. Set the **cutoff date** (photos BEFORE this date will be found)
3. Click **"Scan Photos"** - wait for scan to complete
4. Review thumbnails in the grid
5. **Dry Run is ON by default** - click Delete to see what WOULD be deleted
6. Uncheck **"Dry Run Mode"** when ready for actual deletion
7. Click **"DELETE SELECTED"** and confirm twice

## Safety Features

### Dry Run Mode (Default: ON)
When enabled, clicking Delete will only SIMULATE deletion. No files are actually removed. This lets you verify what would be deleted before committing.

### Double Confirmation
When Dry Run is OFF, you must confirm TWICE before any files are deleted:
1. First confirmation shows count and size
2. Second "Final Warning" confirmation

### Logging
All operations are logged to the console. You can see exactly what's happening:
- Connection status
- Files scanned
- Files deleted (or would be deleted in dry run)
- Any errors encountered

## Supported File Types

- **Images**: JPG, JPEG, PNG, HEIC, HEIF
- **Videos**: MOV, MP4, M4V

## Troubleshooting

### "No iPhone detected"
- Make sure iPhone is plugged in with a **data cable** (not charge-only)
- Try a different USB port
- Restart the iPhone

### "iPhone not trusted"
- Unlock your iPhone
- Look for the "Trust This Computer?" popup
- Tap "Trust" and enter your passcode

### "Permission denied"
- Try running with `sudo python iphone_photo_cleaner.py`
- Check System Preferences > Security & Privacy

### HEIC thumbnails not showing
- Install pillow-heif: `pip install pillow-heif`
- HEIC files will still be deleted even without thumbnail preview

### Connection keeps failing
- Close iTunes/Finder if they're accessing the iPhone
- Unplug and replug the iPhone
- Restart the app

## Technical Details

- Uses `pymobiledevice3` for USB communication with iPhone
- Accesses photos via AFC (Apple File Conduit) service
- Reads from `/DCIM/` directory on iPhone
- Uses file modification time (`st_mtime`) for date filtering
- Thumbnails loaded into memory (limited to 100 for performance)

## Requirements

- macOS (tested on macOS 11+)
- Python 3.8+
- iPhone with iOS 14+
- USB cable (data-capable)

## License

Free to use. Delete responsibly!
