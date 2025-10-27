# YouTube Shorts Generator - VIRAL OPTIMIZED

A Streamlit app that converts YouTube videos into viral-ready vertical shorts (9:16 format) with **advanced subject detection**, **viral hook enhancement**, and **perfect subtitle timing**.

## ✅ Latest Features (v5.0) - VIRAL OPTIMIZATION UPDATE

### **🎯 Enhanced Smart Cropping**
- **Multi-Subject Detection**: Faces, profiles, bodies, and moving objects
- **Confidence Scoring**: Weighted detection with priority ranking
- **All Speakers in Frame**: Keeps multiple people visible during conversations
- **Detection Feedback**: Shows what was detected and confidence levels

### **🎣 Viral Hook Detection & Enhancement**
- **AI Pattern Recognition**: Detects shocking, emotional, and engaging phrases
- **3-Second Hook Extraction**: Perfect for TikTok/YouTube Shorts algorithms
- **Visual Enhancement**: Bold text, zoom effects, special colors for hooks
- **Smart Placement**: Hooks positioned at video start for maximum impact

### **📱 Sequential Subtitle System**
- **NO MORE OVERLAP**: Fixed rainbow subtitle chaos - words appear one by one
- **Global Color Cycling**: Consistent color progression throughout video
- **Perfect Timing**: 0.6-0.8 seconds per word group with no overlap
- **Mobile Optimized**: Large fonts, bottom positioning, high contrast

### **🚫 Double Caption Fix**
- **Burned-in Caption Avoidance**: Smart format selection to avoid YouTube's embedded captions
- **Clean Overlays**: Only your custom subtitles appear, no duplication
- **Format Validation**: Ensures video files (not subtitle files) are processed

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

## 🎯 How to Use

1. **Start the app**: `streamlit run streamlit_app.py`
2. **Enter YouTube URL** in the text input
3. **Configure advanced settings** in the sidebar:
   - ✅ **Enable "YouTube Shorts optimized subtitles"** 
   - ✅ **Enable "Viral hook detection"** (finds best 3-sec moment)
   - ✅ **Enable "Smart subject detection"** (keeps speakers in frame)
   - ✅ **Enable "Avoid videos with burned-in captions"**
   - Choose hook enhancement style (Bold + zoom recommended)
   - Set clip duration and output format
4. **Download video** - App analyzes for best quality
5. **Generate clips** - Creates viral moments with enhanced hooks
6. **Download results** - Individual clips or ZIP file

## 🎣 Viral Hook Features

**Hook Detection Process:**
1. **Pattern Analysis**: Scans for shocking, emotional, question, and number patterns
2. **Timing Optimization**: Extracts perfect 3-second hook segments  
3. **Visual Enhancement**: Applies bold text, larger fonts, special colors
4. **Strategic Placement**: Positions hook at clip beginning for maximum engagement

**Hook Enhancement Options:**
- **Bold text + zoom**: 40% larger font, yellow color, red background
- **Extra large text**: 60% larger font, prominent positioning
- **Pulsing effect**: Animated-style emphasis with orange background
- **None**: Standard subtitle formatting

## 📱 Advanced Subtitle System

**Sequential Word Display:**
- **No Overlap**: Words appear one at a time in perfect sequence
- **0.6-0.8 second timing** per word group (optimal for retention)
- **Global color cycling**: Consistent color progression across entire video
- **Smart grouping**: 1-2 words per segment based on sentence length

**Subject Detection & Cropping:**
- **Multi-modal detection**: Faces, profiles, bodies, moving objects
- **Confidence scoring**: Weighted positioning based on detection quality
- **All speakers visible**: Keeps conversations properly framed
- **Real-time feedback**: Shows detection results and confidence levels

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

**Error: "FFmpeg filter syntax error" (even with subtitles disabled)**
- ✅ **FIXED**: App now automatically recovers with simpler processing
- Enable "Ultra-simple video processing" in sidebar for immediate relief
- The app will try 3 different approaches automatically

**Error: "Invalid argument" or "No such filter"**
- ✅ **FIXED**: Progressive fallback system handles these automatically
- Check the debug files saved for detailed error analysis
- Ultra-simple mode bypasses all complex filters

**Error: "FFmpeg drawtext filter not available"**
- Reinstall FFmpeg with full codec support
- On Linux: `sudo apt install ffmpeg libavcodec-extra`
- Enable "Ultra-simple video processing" to bypass text rendering

**Error: "Font rendering failed"**
- ✅ **IMPROVED**: Automatic fallback to simpler text rendering
- Check if system fonts exist (tested automatically)
- Enable simple subtitle mode or disable subtitles entirely

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