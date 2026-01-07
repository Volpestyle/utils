# video-stitch

A macOS CLI utility that speeds up videos in a folder and concatenates them into a single output file in chronological order.

**Two versions available:**
- `video-stitch` - Bash/ffmpeg version (portable, requires ffmpeg)
- `video-stitch-swift` - Native Swift/AVFoundation version (faster, macOS only)

## Quick Start

```bash
# Swift version (recommended - faster)
./video-stitch-swift -s 100 -o timelapse.mp4 ~/Videos

# Bash/ffmpeg version
./video-stitch -s 100 -o timelapse.mp4 ~/Videos
```

## Requirements

### Swift Version (Recommended)
- **macOS 13+** (Ventura or later)
- No additional dependencies - uses native AVFoundation

### Bash Version
- **macOS** (uses BSD `stat` for file timestamps)
- **ffmpeg** - Install via Homebrew:
  ```bash
  brew install ffmpeg
  ```

## Performance Comparison

| Version | 100GB @ 100x | Notes |
|---------|--------------|-------|
| Swift (AVFoundation) | ~2 hours | Uses native frame skipping, H.264 hardware encoding |
| Bash (ffmpeg) | ~4+ hours | Must decode all frames even when skipping |

The Swift version is faster because AVFoundation can efficiently skip frames without fully decoding them, while ffmpeg must decode every frame regardless of whether it's kept.

## Installation

### Swift Version (Recommended)
```bash
cd ~/web/utils/timelapse
swift build -c release
cp .build/release/video-stitch-swift .
```

### Bash Version
1. Ensure ffmpeg is installed
2. Add the script to your PATH or run it directly:

```bash
# Option A: Add to PATH (recommended)
echo 'export PATH="$PATH:~/web/utils/timelapse"' >> ~/.zshrc
source ~/.zshrc

# Option B: Run directly
~/web/utils/timelapse/video-stitch [options] <folder>
```

## Usage

```
video-stitch [OPTIONS] <input_folder>
```

### Options

| Option | Description |
|--------|-------------|
| `-s, --speed <factor>` | Speed multiplier (default: 1.0). Use 2.0 for 2x faster, 0.5 for half speed |
| `-o, --output <file>` | Output filename (default: `output_YYYYMMDD_HHMMSS.mp4`) |
| `-n, --sort-name` | Sort videos by filename instead of modification time |
| `-v, --verbose` | Show detailed ffmpeg output |
| `-k, --keep-temp` | Keep temporary files after processing |
| `-h, --help` | Show help message |

### Supported Video Formats

- MP4
- MOV
- AVI
- MKV
- WebM
- M4V

## Examples

### Basic usage (stitch at normal speed)
```bash
video-stitch ~/Videos/project
```

### Speed up videos 2x
```bash
video-stitch -s 2.0 ~/Videos/project
```

### Speed up 4x with custom output filename
```bash
video-stitch -s 4.0 -o timelapse.mp4 ~/Videos/project
```

### Sort by filename instead of date
```bash
video-stitch -n ~/Videos/project
```

### Create a 10x timelapse with verbose output
```bash
video-stitch -s 10 -v -o my-timelapse.mp4 ~/Videos/recordings
```

## How It Works

### Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  1. SCAN FOLDER                                                 │
│     Find all video files (mp4, mov, avi, mkv, webm, m4v)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. SORT CHRONOLOGICALLY                                        │
│     Order by file modification time (oldest first)              │
│     Or by filename if -n flag is used                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. PROCESS EACH VIDEO                                          │
│     - Apply speed adjustment via PTS manipulation               │
│     - Adjust audio tempo to match video speed                   │
│     - Re-encode to consistent format (H.264/AAC)                │
│     - Normalize frame rate to 30fps                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. CONCATENATE                                                 │
│     Stitch all processed videos in order                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. OUTPUT                                                      │
│     Export final unified video file                             │
└─────────────────────────────────────────────────────────────────┘
```

### Technical Details

#### Video Speed Adjustment
The script uses ffmpeg's `setpts` filter to adjust video speed:
```
setpts = PTS * (1 / speed_factor)
```
- A speed factor of 2.0 means `setpts=0.5*PTS` (2x faster)
- A speed factor of 0.5 means `setpts=2.0*PTS` (2x slower)

#### Audio Speed Adjustment
Audio is adjusted using ffmpeg's `atempo` filter. Since `atempo` only supports values between 0.5 and 2.0, the script chains multiple filters for extreme speeds:
- Speed 4x → `atempo=2.0,atempo=2.0`
- Speed 8x → `atempo=2.0,atempo=2.0,atempo=2.0`

#### Video Encoding
All videos are re-encoded to ensure compatibility when concatenating:
- **Video codec:** H.264 (libx264)
- **Audio codec:** AAC at 128kbps
- **Frame rate:** Normalized to 30fps
- **Quality:** CRF 23 (good balance of quality/size)

#### Chronological Sorting
By default, videos are sorted by file modification time (oldest first). This ensures recordings made earlier appear first in the final video. Use `-n` to sort alphabetically by filename instead.

## Output

The script displays progress and a summary:

```
═══════════════════════════════════════════════════════════════
                     video-stitch
═══════════════════════════════════════════════════════════════

[INFO] Scanning folder for videos: /path/to/folder
[INFO] Found 5 video(s) to process
[INFO] Speed factor: 4.0x
[INFO] Output file: timelapse.mp4

[INFO] Processing order:
  1. recording_001.mov
  2. recording_002.mov
  3. recording_003.mov
  4. recording_004.mov
  5. recording_005.mov

[1/5] Processing: recording_001.mov
[2/5] Processing: recording_002.mov
[3/5] Processing: recording_003.mov
[4/5] Processing: recording_004.mov
[5/5] Processing: recording_005.mov

[INFO] Concatenating videos...

[SUCCESS] Video processing complete!

  Videos processed:    5
  Original duration:   01:23:45
  Final duration:      00:20:56
  Speed factor:        4.0x
  Output file:         timelapse.mp4
  File size:           256M
```

## Troubleshooting

### "ffmpeg is not installed"
Install ffmpeg via Homebrew:
```bash
brew install ffmpeg
```

### Audio sync issues
If audio is out of sync, try running without audio:
```bash
# The script automatically retries without audio if processing fails
# Or you can manually strip audio first
ffmpeg -i input.mp4 -an -c:v copy input_noaudio.mp4
```

### Out of disk space
The script creates temporary files during processing. Ensure you have enough disk space (roughly 2x the total size of input videos). Use `-k` to inspect temp files location if needed.

### Permission denied
Ensure the script is executable:
```bash
chmod +x ~/web/utils/timelapse/video-stitch
```

## License

MIT
