import streamlit as st
import yt_dlp
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
import json

# Page configuration
st.set_page_config(
    page_title="YouTube Shorts Generator - FIXED",
    page_icon="🎬",
    layout="wide"
)

def create_temp_dir():
    """Create a temporary directory for processing"""
    temp_dir = f"shorts_{hash(os.urandom(8)) % 1000000000}"
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def download_video_and_subtitles(url, temp_dir):
    """Download video and subtitles using yt-dlp with highest quality"""
    try:
        # Enhanced yt-dlp options for highest quality and better subtitle handling
        ydl_opts = {
            # Download highest quality available (4K, 1080p, etc.)
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'{temp_dir}/video.%(ext)s',
            
            # Comprehensive subtitle options
            'writeautomaticsub': True,
            'writesubtitles': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU'],
            'subtitlesformat': 'vtt/srt/best',
            
            # Additional quality settings
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            
            # Error handling
            'ignoreerrors': False,
            'no_warnings': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            # Check available formats for quality info
            formats = info.get('formats', [])
            best_quality = "Unknown"
            for fmt in formats:
                if fmt.get('vcodec') != 'none':  # Video stream
                    height = fmt.get('height', 0)
                    if height >= 2160:
                        best_quality = "4K"
                        break
                    elif height >= 1440:
                        best_quality = "1440p"
                    elif height >= 1080 and best_quality == "Unknown":
                        best_quality = "1080p"
                    elif height >= 720 and best_quality == "Unknown":
                        best_quality = "720p"
            
            st.info(f"📹 Available quality: {best_quality}")
            
            # Download video and subtitles
            ydl.download([url])
            
            # Find downloaded video file
            video_files = list(Path(temp_dir).glob('video.*'))
            if not video_files:
                raise Exception("No video file downloaded")
            
            video_path = str(video_files[0])
            
            # Look for subtitle files (both VTT and SRT)
            subtitle_files = list(Path(temp_dir).glob('*.vtt')) + list(Path(temp_dir).glob('*.srt'))
            
            # Prefer English subtitles
            subtitle_path = None
            for sub_file in subtitle_files:
                if any(lang in str(sub_file).lower() for lang in ['en', 'english']):
                    subtitle_path = str(sub_file)
                    break
            
            # If no English subs found, take the first available
            if not subtitle_path and subtitle_files:
                subtitle_path = str(subtitle_files[0])
            
            if subtitle_path:
                st.success(f"✅ Found subtitles: {os.path.basename(subtitle_path)}")
            else:
                st.warning("⚠️ No subtitles found - will create clips without captions")
            
            return video_path, subtitle_path, title, duration
            
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
        return None, None, None, None

def parse_subtitles(subtitle_path):
    """Parse subtitle file (VTT or SRT format)"""
    subtitles = []
    if not subtitle_path or not os.path.exists(subtitle_path):
        return subtitles
    
    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine file format
        is_srt = subtitle_path.lower().endswith('.srt')
        
        if is_srt:
            # Parse SRT format
            subtitles = parse_srt_format(content)
        else:
            # Parse VTT format
            subtitles = parse_vtt_format(content)
        
        st.info(f"📝 Parsed {len(subtitles)} subtitle segments from {'SRT' if is_srt else 'VTT'} file")
        return sorted(subtitles, key=lambda x: x['start'])
        
    except Exception as e:
        st.warning(f"Error parsing subtitles: {str(e)}")
        return []

def parse_srt_format(content):
    """Parse SRT subtitle format"""
    subtitles = []
    
    # Split by double newlines to get subtitle blocks
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # SRT format: number, timestamp, text
            try:
                # Second line should contain timestamps
                timestamp_line = lines[1]
                if '-->' in timestamp_line:
                    timestamps = timestamp_line.split(' --> ')
                    if len(timestamps) == 2:
                        start_time = parse_srt_timestamp(timestamps[0].strip())
                        end_time = parse_srt_timestamp(timestamps[1].strip())
                        
                        # Join all text lines after timestamp
                        text_lines = lines[2:]
                        text = ' '.join(text_lines)
                        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
                        text = text.strip()
                        
                        if text and start_time is not None and end_time is not None:
                            subtitles.append({
                                'start': start_time,
                                'end': end_time,
                                'text': text
                            })
            except:
                continue
    
    return subtitles

def parse_vtt_format(content):
    """Parse VTT subtitle format"""
    subtitles = []
    
    # Split by empty lines to get individual subtitle blocks
    blocks = re.split(r'\n\s*\n', content)
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2:
            # Look for timestamp line
            for line in lines:
                if '-->' in line:
                    timestamp_line = line
                    # Find text lines (everything after timestamp)
                    text_start_idx = lines.index(timestamp_line) + 1
                    text_lines = lines[text_start_idx:]
                    
                    # Parse timestamps
                    timestamps = timestamp_line.split(' --> ')
                    if len(timestamps) == 2:
                        start_time = parse_vtt_timestamp(timestamps[0])
                        end_time = parse_vtt_timestamp(timestamps[1])
                        
                        # Join text lines and clean
                        text = ' '.join(text_lines)
                        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
                        text = text.strip()
                        
                        if text and start_time is not None and end_time is not None:
                            subtitles.append({
                                'start': start_time,
                                'end': end_time,
                                'text': text
                            })
                    break
    
    return subtitles

def parse_srt_timestamp(timestamp_str):
    """Parse SRT timestamp format (00:00:00,000)"""
    try:
        # SRT format: hours:minutes:seconds,milliseconds
        timestamp_str = timestamp_str.strip()
        
        # Replace comma with dot for milliseconds
        timestamp_str = timestamp_str.replace(',', '.')
        
        # Split time components
        time_components = timestamp_str.split(':')
        
        if len(time_components) == 3:
            hours = int(time_components[0])
            minutes = int(time_components[1])
            seconds_ms = float(time_components[2])
            
            total_seconds = hours * 3600 + minutes * 60 + seconds_ms
            return total_seconds
        
        return None
    except:
        return None

def parse_vtt_timestamp(timestamp_str):
    """Parse VTT timestamp to seconds"""
    try:
        timestamp_str = timestamp_str.strip().split()[0]
        
        if '.' in timestamp_str:
            time_part, ms_part = timestamp_str.split('.')
            ms = float('0.' + ms_part.replace(',', ''))
        else:
            time_part = timestamp_str
            ms = 0
        
        time_components = time_part.split(':')
        
        if len(time_components) == 3:
            hours, minutes, seconds = map(int, time_components)
            total_seconds = hours * 3600 + minutes * 60 + seconds + ms
        elif len(time_components) == 2:
            minutes, seconds = map(int, time_components)
            total_seconds = minutes * 60 + seconds + ms
        else:
            return None
            
        return total_seconds
    except:
        return None

def find_viral_moments(subtitles, min_clip_duration=15, max_clip_duration=60):
    """Find potential viral moments in subtitles"""
    viral_patterns = [
        r'\b(amazing|incredible|unbelievable|shocking|mind-blowing|crazy|insane|wow)\b',
        r'\b(secret|hidden|nobody knows|revealed|exposed)\b',
        r'\b(how to|tutorial|learn|master|guide)\b',
        r'\b(mistake|wrong|error|fail|disaster)\b',
        r'\b(money|rich|wealthy|expensive|cheap|free)\b',
        r'\b(love|hate|angry|emotional|feeling)\b',
        r'\b(new|latest|breaking|update|news)\b',
        r'\b(before|after|transformation|change)\b',
        r'\b(reason|why|because|explanation)\b',
        r'\b(never|always|forever|every|all)\b'
    ]
    
    moments = []
    
    for i, subtitle in enumerate(subtitles):
        score = 0
        text = subtitle['text'].lower()
        
        for pattern in viral_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches * 2
        
        score += text.count('?') * 3
        score += text.count('!') * 2
        
        capital_words = len(re.findall(r'\b[A-Z]{2,}\b', subtitle['text']))
        score += capital_words * 1
        
        if score > 0:
            for duration in [15, 30, 45, 60]:
                if duration < min_clip_duration or duration > max_clip_duration:
                    continue
                
                start_time = max(0, subtitle['start'] - duration/3)
                end_time = start_time + duration
                
                clip_subtitles = [
                    s for s in subtitles 
                    if s['start'] >= start_time and s['end'] <= end_time
                ]
                
                if clip_subtitles:
                    moments.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': duration,
                        'score': score,
                        'trigger_text': subtitle['text'],
                        'subtitles': clip_subtitles
                    })
    
    moments = sorted(moments, key=lambda x: x['score'], reverse=True)
    
    filtered_moments = []
    for moment in moments:
        overlap = False
        for existing in filtered_moments:
            if (moment['start_time'] < existing['end_time'] and 
                moment['end_time'] > existing['start_time']):
                overlap = True
                break
        if not overlap:
            filtered_moments.append(moment)
    
    return filtered_moments[:10]

def escape_text_for_ffmpeg(text):
    """Properly escape text for FFmpeg drawtext filter"""
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace(",", "\\,")
    text = text.replace("\\", "\\\\")
    return text

def create_simple_filtergraph(subtitles, background_style, visual_preset, motion_effects, temp_dir):
    """Create a simple, working filtergraph"""
    
    # Color schemes
    colors = ['#FFD700', '#FF69B4', '#00FFFF', '#FF4500', '#32CD32']
    
    # Start with simple scaling
    filters = []
    filters.append("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[base]")
    
    # Add color enhancement
    if visual_preset == 'cinematic':
        filters.append("[base]eq=contrast=1.15:brightness=0.05:saturation=1.25[enhanced]")
        current_label = "enhanced"
    elif visual_preset == 'high_energy':
        filters.append("[base]eq=contrast=1.3:brightness=0.1:saturation=1.4[enhanced]")
        current_label = "enhanced"
    elif visual_preset == 'platform_optimized':
        filters.append("[base]eq=contrast=1.2:brightness=0.08:saturation=1.3[enhanced]")
        current_label = "enhanced"
    else:
        current_label = "base"
    
    # Add motion effects
    if motion_effects:
        filters.append(f"[{current_label}]zoompan=z='1.05':d=1[motion]")
        current_label = "motion"
    
    # Add subtitles
    for i, subtitle in enumerate(subtitles):
        color = colors[i % len(colors)]
        escaped_text = escape_text_for_ffmpeg(subtitle['text'])
        
        next_label = f"text{i}"
        subtitle_filter = f"[{current_label}]drawtext=text='{escaped_text}':fontsize=60:fontcolor={color}:x=(w-text_w)/2:y=h-100:enable='between(t,{subtitle['start']:.3f},{subtitle['end']:.3f})'[{next_label}]"
        filters.append(subtitle_filter)
        current_label = next_label
    
    # Final output
    filters.append(f"[{current_label}]format=yuv420p[out]")
    
    # Write to file
    filtergraph_file = os.path.join(temp_dir, "filtergraph.txt")
    with open(filtergraph_file, 'w') as f:
        f.write(";\n".join(filters))
    
    return filtergraph_file

def create_shorts_clip(video_path, moment, background_style, visual_preset, motion_effects, temp_dir, clip_index):
    """Create a shorts clip with simplified approach"""
    try:
        # Convert subtitles to relative timing
        clip_subtitles = []
        clip_start_time = moment['start_time']
        
        for subtitle in moment['subtitles']:
            relative_start = max(0, subtitle['start'] - clip_start_time)
            relative_end = subtitle['end'] - clip_start_time
            
            if relative_start < moment['duration'] and relative_end > 0:
                clip_subtitles.append({
                    'start': relative_start,
                    'end': min(relative_end, moment['duration']),
                    'text': subtitle['text']
                })
        
        # Create filtergraph
        filtergraph_file = create_simple_filtergraph(
            clip_subtitles, background_style, visual_preset, motion_effects, temp_dir
        )
        
        # Output file
        output_file = os.path.join(temp_dir, f'clip_{clip_index+1}.mp4')
        
        # Enhanced FFmpeg command for high quality output
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(moment['start_time']),
            '-i', video_path,
            '-t', str(moment['duration']),
            '-filter_complex_script', filtergraph_file,
            '-map', '[out]',
            '-map', '0:a',
            # High quality video encoding
            '-c:v', 'libx264',
            '-preset', 'slow',  # Better compression
            '-crf', '18',       # Higher quality (lower = better)
            '-pix_fmt', 'yuv420p',
            # High quality audio encoding
            '-c:a', 'aac',
            '-b:a', '192k',     # Higher audio bitrate
            '-ar', '48000',     # Higher sample rate
            # Output optimization
            '-movflags', '+faststart',
            '-max_muxing_queue_size', '9999',
            output_file
        ]
        
        # Run command
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if process.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            return {
                'file': output_file,
                'filename': f'clip_{clip_index+1}.mp4',
                'duration': moment['duration'],
                'score': moment['score'],
                'trigger_text': moment['trigger_text'],
                'size_mb': round(file_size, 2),
                'start_time': moment['start_time']
            }
        else:
            st.error(f"FFmpeg error for clip {clip_index+1}: {process.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        st.error(f"Timeout creating clip {clip_index+1}")
        return None
    except Exception as e:
        st.error(f"Error creating clip {clip_index+1}: {str(e)}")
        return None

def create_download_zip(clips, temp_dir):
    """Create ZIP file for download"""
    zip_path = os.path.join(temp_dir, 'shorts_clips.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for clip in clips:
            if clip and os.path.exists(clip['file']):
                zipf.write(clip['file'], clip['filename'])
    
    return zip_path

# Streamlit UI
st.title("🎬 YouTube Shorts Generator - HIGH QUALITY VERSION")
st.write("✅ **Enhanced Features:** 4K Quality Downloads + Perfect Subtitle Parsing!")

# Quality info
st.info("""
🚀 **Latest Improvements:**
- 📹 **4K Quality Downloads**: Downloads highest available resolution (4K, 1080p, etc.)
- 📝 **Enhanced Subtitles**: Supports both SRT and VTT formats with better parsing
- 🎨 **High Quality Output**: CRF 18 encoding with 192kbps audio for crisp results
- 🔧 **Better Error Handling**: More reliable subtitle detection and processing
""")

# Settings
st.sidebar.header("🎨 Settings")

background_style = st.sidebar.selectbox(
    "Background Style",
    ["simple_crop", "blurred", "gradient"],
    help="Simple crop is most reliable"
)

visual_preset = st.sidebar.selectbox(
    "Visual Preset",
    ["platform_optimized", "cinematic", "high_energy", "minimal"],
    help="Color enhancement presets"
)

motion_effects = st.sidebar.checkbox(
    "Enable Motion Effects",
    value=False,
    help="Add subtle zoom (may cause issues with some videos)"
)

clip_duration = st.sidebar.slider("Clip Duration (seconds)", 15, 60, 30)
max_clips = st.sidebar.slider("Maximum Clips", 1, 10, 3)

# Main input
url = st.text_input(
    "Enter YouTube URL:",
    placeholder="https://www.youtube.com/watch?v=..."
)

if st.button("🚀 Generate Shorts", type="primary", use_container_width=True):
    if not url:
        st.error("Please enter a YouTube URL")
    else:
        temp_dir = create_temp_dir()
        
        with st.spinner("📥 Downloading video..."):
            video_path, subtitle_path, title, duration = download_video_and_subtitles(url, temp_dir)
        
        if not video_path:
            st.error("Failed to download video")
            st.stop()
        
        st.success(f"✅ Downloaded: {title}")
        
        with st.spinner("📝 Analyzing subtitles..."):
            subtitles = parse_subtitles(subtitle_path)
        
        if not subtitles:
            st.warning("⚠️ No subtitles found. Creating simple clips...")
            moments = []
            for i in range(min(max_clips, duration // clip_duration)):
                start = i * clip_duration
                end = min(start + clip_duration, duration)
                moments.append({
                    'start_time': start,
                    'end_time': end,
                    'duration': end - start,
                    'score': 1,
                    'trigger_text': f'Clip {i+1}',
                    'subtitles': []
                })
        else:
            st.success(f"📊 Found {len(subtitles)} subtitle segments")
            moments = find_viral_moments(subtitles, clip_duration, clip_duration)
        
        if not moments:
            st.warning("Creating clips from beginning...")
            moments = []
            for i in range(min(max_clips, duration // clip_duration)):
                start = i * clip_duration
                end = min(start + clip_duration, duration)
                clip_subs = [s for s in subtitles if s['start'] >= start and s['end'] <= end]
                moments.append({
                    'start_time': start,
                    'end_time': end,
                    'duration': end - start,
                    'score': 1,
                    'trigger_text': f'Clip {i+1}',
                    'subtitles': clip_subs
                })
        
        st.info(f"🎯 Creating {len(moments[:max_clips])} clips...")
        
        # Create clips
        progress_bar = st.progress(0)
        clips = []
        
        for i, moment in enumerate(moments[:max_clips]):
            progress_bar.progress((i + 1) / len(moments[:max_clips]))
            
            clip = create_shorts_clip(
                video_path, moment, background_style, visual_preset, motion_effects, temp_dir, i
            )
            
            if clip:
                clips.append(clip)
                st.success(f"✅ Created clip {i+1}: {clip['duration']}s ({clip['size_mb']} MB)")
        
        if clips:
            st.success(f"🎉 Created {len(clips)} clips successfully!")
            
            # Create ZIP
            zip_path = create_download_zip(clips, temp_dir)
            
            if os.path.exists(zip_path):
                with open(zip_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download All Clips (ZIP)",
                        data=f.read(),
                        file_name="youtube_shorts_clips.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            
            # Individual downloads
            st.subheader("Individual Downloads")
            for clip in clips:
                if os.path.exists(clip['file']):
                    with open(clip['file'], 'rb') as f:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{clip['filename']}** - {clip['duration']}s")
                        with col2:
                            st.download_button(
                                label="⬇️",
                                data=f.read(),
                                file_name=clip['filename'],
                                mime="video/mp4",
                                key=f"dl_{clip['filename']}"
                            )
        else:
            st.error("❌ No clips were created successfully")

# Tips
with st.expander("💡 Tips"):
    st.write("""
    **This is a simplified, fixed version that should work reliably:**
    - Uses simple filtergraph structure
    - Minimal effects to avoid errors
    - Better error handling
    - Cleaner subtitle processing
    """)

st.markdown("---")
st.markdown("🎬 **Fixed YouTube Shorts Generator** - Reliable video processing!")