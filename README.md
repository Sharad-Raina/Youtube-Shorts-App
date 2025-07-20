# YouTube Shorts Generator - FIXED VERSION

A Streamlit app that converts YouTube videos into viral-ready vertical shorts (9:16 format) with automatic subtitle handling, smart cropping, and face detection.

## ✅ Latest Fixes (v2.0)

- **🔧 Robust FFmpeg Integration**: Fixed filter complex syntax errors
- **🔤 Simplified Text Processing**: Removes problematic characters causing rendering issues
- **👤 Smart Face Detection**: Automatically crops to keep speakers in frame
- **🎨 Multiple Subtitle Styles**: Box, shadow, and outline options
- **⚙️ Fallback Modes**: Simple subtitle mode for maximum compatibility
- **🧪 Font Testing**: Built-in testing to verify FFmpeg setup
- **📋 Debug Output**: Saves command logs for troubleshooting

## 🛠️ Setup Instructions

### 1. Install FFmpeg

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**
- Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
- Add to PATH environment variable

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
streamlit run streamlit_app.py
```

## 🚀 Features

### Video Processing
- **9:16 Aspect Ratio**: Perfect for YouTube Shorts, TikTok, Instagram Reels
- **Smart Cropping**: Face detection keeps speakers centered
- **Multiple Qualities**: 480p to 4K output options
- **Background Styles**: Simple crop or blurred cinematic effect

### Subtitle Handling
- **Auto-Detection**: Finds manual or auto-generated captions
- **Multiple Languages**: Prioritizes English, accepts others as fallback
- **Robust Processing**: Handles problematic characters and special symbols
- **Style Options**: Box, shadow, or outline subtitle styles
- **Simple Mode**: Fallback for compatibility issues

### Smart Features
- **Viral Moment Detection**: Finds engaging segments automatically
- **Face Tracking**: Crops to include speakers
- **Quality Presets**: Optimized for different platforms
- **Persistent Downloads**: Clips remain available after generation

## 🔧 Troubleshooting

### FFmpeg Issues

1. **Test FFmpeg Installation:**
   - Use the "Test Font Rendering" button in Advanced Options
   - Check if FFmpeg is in your PATH: `ffmpeg -version`

2. **Font Rendering Problems:**
   - Enable "Simple subtitle mode" in sidebar
   - Try "ASCII-only mode" to remove special characters
   - Disable subtitles temporarily if issues persist

3. **Filter Complex Errors:**
   - Check the debug files saved in temp directory
   - Try simple mode first
   - Ensure FFmpeg version is recent (4.0+)

### Common Fixes

**Error: "FFmpeg drawtext filter not available"**
- Reinstall FFmpeg with full codec support
- On Linux: `sudo apt install ffmpeg libavcodec-extra`

**Error: "Font rendering failed"**
- Check if system fonts exist (tested automatically)
- Enable simple subtitle mode
- Try without font styling

**Error: "No subtitles available"**
- Enable "Force auto-generated captions"
- Try "Accept subtitles in any language"
- Some videos may not have captions available

### Platform-Specific Notes

**macOS:**
- Uses Arial or Helvetica fonts by default
- Face detection works with built-in camera support

**Windows:**
- Uses Arial font from system fonts
- May need Visual C++ redistributables

**Linux:**
- Uses DejaVu Sans or Liberation fonts
- Install `python3-opencv` if face detection fails

## 📱 Output Formats

| Quality | Resolution | Use Case |
|---------|------------|----------|
| 480p | 480×854 | Quick testing, low bandwidth |
| 720p | 720×1280 | Standard mobile viewing |
| 1080p | 1080×1920 | Recommended for most platforms |
| 4K | 1080×1920* | High quality (same res, better encoding) |

*Note: 4K setting uses better encoding parameters, not larger resolution

## 🎨 Subtitle Styles

- **Box**: White text on black background box
- **Shadow**: White text with black drop shadow
- **Outline**: White text with black border outline

## 🔍 Debug Information

The app saves debug files for each clip:
- `clip_X_command.txt`: FFmpeg command used
- `clip_X_filters.txt`: Filter complex string
- `clip_X_subtitles.txt`: Processed subtitle text
- `clip_X_error.txt`: Error logs if issues occur

## 🆘 Support

If you encounter issues:
1. Check the debug files generated
2. Try simple subtitle mode
3. Test FFmpeg with the built-in test function
4. Disable subtitles as a last resort

## 📋 Requirements

- Python 3.8+
- FFmpeg with drawtext support
- Sufficient disk space for video processing
- Internet connection for video downloads

## 🎯 Best Practices

1. **Enable Smart Crop** for videos with people
2. **Use 1080p quality** for best platform compatibility
3. **30-second clips** perform best on social media
4. **Test with sample video** before bulk processing
5. **Check subtitle availability** before processing long videos

---

**Built with Streamlit** | **Powered by yt-dlp & FFmpeg** | **Enhanced with OpenCV**