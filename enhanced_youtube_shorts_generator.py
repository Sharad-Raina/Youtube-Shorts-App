import streamlit as st
import subprocess
import os
import sys
import zipfile
import time
import shutil
import json
import re
import random
from collections import defaultdict
import yt_dlp
import tempfile
from pathlib import Path

st.set_page_config(page_title="YouTube Shorts Generator", page_icon="🎬", layout="wide")

if 'video_processed' not in st.session_state:
    st.session_state.video_processed = False
if 'output_files' not in st.session_state:
    st.session_state.output_files = []
if 'zip_path' not in st.session_state:
    st.session_state.zip_path = None

st.title("🎬 YouTube Viral Shorts Generator - Pro Max")
st.markdown("### Create viral shorts that get 1M+ views with AI-powered optimization!")
st.markdown("---")

PLATFORM_PRESETS = {
    "TikTok": {
        "hook_style": "aggressive",
        "caption_animation": "bounce",
        "color_scheme": "Rainbow",
        "audio_style": "trendy",
        "overlay_style": "gen_z"
    },
    "Instagram Reels": {
        "hook_style": "aesthetic",
        "caption_animation": "smooth",
        "color_scheme": "Viral",
        "audio_style": "balanced",
        "overlay_style": "millennial"
    },
    "YouTube Shorts": {
        "hook_style": "informative",
        "caption_animation": "professional",
        "color_scheme": "Energy",
        "audio_style": "clear",
        "overlay_style": "classic"
    }
}

CAPTION_COLORS = {
    "TikTok": {"primary": "white", "shadow": "black", "accent": "magenta"},
    "Viral": {"primary": "yellow", "shadow": "black", "accent": "green"},
    "Energy": {"primary": "orange", "shadow": "black", "accent": "white"},
    "Rainbow": {"primary": "red", "shadow": "black", "accent": "white"}
}

VIRAL_HOOKS = {
    "curiosity": ["Wait for it...", "You won't believe this...", "This changes everything..."],
    "number": ["3 things that...", "The #1 reason why...", "5 secrets about..."],
    "challenge": ["Don't try this...", "Can you spot the...", "99% fail this..."],
    "reveal": ["The truth about...", "What they don't tell you...", "Finally revealed..."],
    "emotion": ["This made me cry...", "I'm still shocked...", "Mind = Blown"]
}

def create_temp_dir():
    """Create a temporary directory for processing"""
    temp_dir = f"shorts_{hash(os.urandom(8)) % 1000000000}"
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def download_video_and_subtitles(url, temp_dir):
    """Download video and subtitles using yt-dlp"""
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[height<=1080]/best',
            'outtmpl': f'{temp_dir}/video.%(ext)s',
            'writeautomaticsub': True,
            'writesubtitles': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB'],
            'subtitlesformat': 'vtt',
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            # Download video and subtitles
            ydl.download([url])
            
            # Find downloaded video file
            video_files = list(Path(temp_dir).glob('video.*'))
            if not video_files:
                raise Exception("No video file downloaded")
            
            video_path = str(video_files[0])
            
            # Find subtitle file
            subtitle_files = list(Path(temp_dir).glob('*.vtt'))
            subtitle_path = str(subtitle_files[0]) if subtitle_files else None
            
            return video_path, subtitle_path, title, duration
            
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
        return None, None, None, None

def parse_vtt_subtitles(subtitle_path):
    """Parse VTT subtitle file"""
    subtitles = []
    if not subtitle_path or not os.path.exists(subtitle_path):
        return subtitles
    
    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
                            start_time = parse_timestamp(timestamps[0])
                            end_time = parse_timestamp(timestamps[1])
                            
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
        
        return sorted(subtitles, key=lambda x: x['start'])
        
    except Exception as e:
        st.warning(f"Error parsing subtitles: {str(e)}")
        return []

def parse_timestamp(timestamp_str):
    """Parse VTT timestamp to seconds"""
    try:
        # Remove any additional formatting
        timestamp_str = timestamp_str.strip().split()[0]
        
        # Handle different timestamp formats
        if '.' in timestamp_str:
            time_part, ms_part = timestamp_str.split('.')
            ms = float('0.' + ms_part.replace(',', ''))
        else:
            time_part = timestamp_str
            ms = 0
        
        # Parse time components
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
        
        # Check for viral patterns
        for pattern in viral_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches * 2
        
        # Check for questions and exclamations
        score += text.count('?') * 3
        score += text.count('!') * 2
        
        # Check for capital words (emphasis)
        capital_words = len(re.findall(r'\b[A-Z]{2,}\b', subtitle['text']))
        score += capital_words * 1
        
        if score > 0:
            # Try to create clips of different durations around this moment
            for duration in [15, 30, 45, 60]:
                if duration < min_clip_duration or duration > max_clip_duration:
                    continue
                
                start_time = max(0, subtitle['start'] - duration/3)
                end_time = start_time + duration
                
                # Get subtitles for this time range
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
    
    # Sort by score and remove duplicates
    moments = sorted(moments, key=lambda x: x['score'], reverse=True)
    
    # Remove overlapping moments (keep highest scoring)
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
    
    return filtered_moments[:10]  # Return top 10 moments

def escape_text_for_ffmpeg(text):
    """Properly escape text for FFmpeg drawtext filter"""
    # Replace problematic characters
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace(",", "\\,")
    text = text.replace(";", "\\;")
    text = text.replace("\\", "\\\\")
    text = text.replace("%", "\\%")
    text = text.replace("=", "\\=")
    return text

def create_filtergraph_file(video_path, subtitles, background_style, visual_preset, motion_effects, temp_dir):
    """Create a filtergraph file to avoid command line length limits"""
    
    # Color schemes for different presets
    color_schemes = {
        'platform_optimized': ['#FFD700', '#FF69B4', '#00FFFF', '#FF4500', '#32CD32'],
        'cinematic': ['#F4D03F', '#E8DAEF', '#AED6F1', '#FADBD8', '#D5F4E6'],
        'high_energy': ['#FF0080', '#00FF80', '#8000FF', '#FF8000', '#0080FF'],
        'minimal': ['#FFFFFF', '#F0F0F0', '#E0E0E0', '#D0D0D0', '#C0C0C0']
    }
    
    colors = color_schemes.get(visual_preset, color_schemes['platform_optimized'])
    
    # Create filtergraph
    filtergraph = []
    
    # Input and scaling
    filtergraph.append("[0:v]scale=1080:1920:force_original_aspect_ratio=increase[scaled]")
    
    # Background creation based on style
    if background_style == "blurred":
        filtergraph.append("[scaled]split=2[main][bg]")
        filtergraph.append("[bg]scale=1080:1920:force_original_aspect_ratio=increase,gblur=sigma=20[blurred_bg]")
        filtergraph.append("[blurred_bg][main]overlay=(W-w)/2:(H-h)/2[composed]")
    elif background_style == "gradient":
        filtergraph.append("[scaled]split=2[main][bg]")
        filtergraph.append("color=c=#1a1a2e:size=1080x1920:duration=1[gradient_bg]")
        filtergraph.append("[gradient_bg][main]overlay=(W-w)/2:(H-h)/2[composed]")
    else:  # original_crop
        filtergraph.append("[scaled]crop=1080:1920:(iw-1080)/2:(ih-1920)/2[composed]")
    
    # Apply visual enhancements based on preset
    if visual_preset == 'cinematic':
        filtergraph.append("[composed]eq=contrast=1.15:brightness=0.05:saturation=1.25:gamma=0.95[enhanced]")
        filtergraph.append("[enhanced]curves=red='0/0 0.5/0.58 1/1':green='0/0 0.5/0.52 1/1':blue='0/0 0.5/0.48 1/1'[graded]")
    elif visual_preset == 'high_energy':
        filtergraph.append("[composed]eq=contrast=1.3:brightness=0.1:saturation=1.4:gamma=0.9[enhanced]")
        filtergraph.append("[enhanced]hue=s=1.2[graded]")
    elif visual_preset == 'platform_optimized':
        filtergraph.append("[composed]eq=contrast=1.2:brightness=0.08:saturation=1.3:gamma=0.92[graded]")
    else:  # minimal
        filtergraph.append("[composed]eq=contrast=1.05:brightness=0.02:saturation=1.1[graded]")
    
    # Add motion effects if enabled
    if motion_effects:
        filtergraph.append("[graded]zoompan=z='if(lte(on,1),1.1,max(1.0,1.1-0.02*(on-1)))':d=25*2:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'[motion]")
        base_video = "motion"
    else:
        base_video = "graded"
    
    # Add subtitle overlays
    current_output = base_video
    for i, subtitle in enumerate(subtitles):
        color = colors[i % len(colors)]
        escaped_text = escape_text_for_ffmpeg(subtitle['text'])
        
        # Simplified drawtext parameters to reduce length
        drawtext_filter = (f"drawtext=text='{escaped_text}'"
                          f":fontsize=80"
                          f":fontcolor={color}"
                          f":bordercolor=black:borderw=4"
                          f":shadowcolor=black@0.7:shadowx=3:shadowy=3"
                          f":box=1:boxcolor=black@0.5:boxborderw=10"
                          f":x=(w-text_w)/2:y=h-200-text_h"
                          f":enable='between(t,{subtitle['start']:.3f},{subtitle['end']:.3f})'")
        
        next_output = f"sub{i}"
        filtergraph.append(f"[{current_output}]{drawtext_filter}[{next_output}]")
        current_output = next_output
    
    # Final output
    filtergraph.append(f"[{current_output}]format=yuv420p[out]")
    
    # Write filtergraph to file
    filtergraph_file = os.path.join(temp_dir, "filtergraph.txt")
    with open(filtergraph_file, 'w') as f:
        f.write(';\n'.join(filtergraph))
    
    return filtergraph_file

def create_shorts_clip(video_path, moment, background_style, visual_preset, motion_effects, temp_dir, clip_index):
    """Create a single shorts clip using filtergraph file"""
    try:
        # Create filtergraph file
        filtergraph_file = create_filtergraph_file(
            video_path, moment['subtitles'], background_style, visual_preset, motion_effects, temp_dir
        )
        
        # Output filename
        output_file = os.path.join(temp_dir, f'clip_{clip_index+1}.mp4')
        
        # Build FFmpeg command using filtergraph file
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(moment['start_time']),
            '-i', video_path,
            '-t', str(moment['duration']),
            '-filter_complex_script', filtergraph_file,
            '-map', '[out]',
            '-map', '0:a',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-movflags', '+faststart',
            output_file
        ]
        
        # Run FFmpeg command
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if process.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # Size in MB
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
    """Create a ZIP file with all clips for download"""
    zip_path = os.path.join(temp_dir, 'shorts_clips.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for clip in clips:
            if clip and os.path.exists(clip['file']):
                zipf.write(clip['file'], clip['filename'])
    
    return zip_path

# Streamlit UI
st.title("🎬 Enhanced YouTube Shorts Generator")
st.write("Generate engaging, professionally styled YouTube Shorts with cinematic backgrounds and dynamic captions!")

# Sidebar for settings
st.sidebar.header("🎨 Visual Settings")

background_style = st.sidebar.selectbox(
    "Background Style",
    ["blurred", "gradient", "original_crop"],
    help="Choose how to handle the background for vertical format"
)

visual_preset = st.sidebar.selectbox(
    "Visual Preset",
    ["platform_optimized", "cinematic", "high_energy", "minimal"],
    help="Different color grading and styling presets"
)

motion_effects = st.sidebar.checkbox(
    "Enable Motion Effects",
    value=True,
    help="Add subtle zoom and motion effects"
)

clip_duration = st.sidebar.slider(
    "Clip Duration (seconds)",
    min_value=15,
    max_value=60,
    value=30,
    help="Duration of each generated clip"
)

max_clips = st.sidebar.slider(
    "Maximum Clips",
    min_value=1,
    max_value=10,
    value=5,
    help="Maximum number of clips to generate"
)

# Main input
url = st.text_input(
    "Enter YouTube URL:",
    placeholder="https://www.youtube.com/watch?v=...",
    help="Paste any YouTube video URL here"
)

if st.button("🚀 Generate Shorts", type="primary", use_container_width=True):
    if not url:
        st.error("Please enter a YouTube URL")
    else:
        # Initialize session state
        if 'clips' not in st.session_state:
            st.session_state.clips = []
        if 'temp_dir' not in st.session_state:
            st.session_state.temp_dir = None
        
        # Create temporary directory
        temp_dir = create_temp_dir()
        st.session_state.temp_dir = temp_dir
        
        with st.spinner("📥 Downloading video and subtitles..."):
            video_path, subtitle_path, title, duration = download_video_and_subtitles(url, temp_dir)
        
        if not video_path:
            st.error("Failed to download video. Please check the URL and try again.")
            st.stop()
        
        st.success(f"✅ Downloaded: {title}")
        st.info(f"📹 Duration: {duration//60}:{duration%60:02d} minutes")
        
        with st.spinner("📝 Analyzing subtitles for viral moments..."):
            subtitles = parse_vtt_subtitles(subtitle_path)
        
        if not subtitles:
            st.warning("⚠️ No subtitles found. Clips will be generated without captions.")
            # Create a simple moment for the first part of the video
            moments = [{
                'start_time': 0,
                'end_time': min(clip_duration, duration),
                'duration': min(clip_duration, duration),
                'score': 1,
                'trigger_text': 'No subtitles available',
                'subtitles': []
            }]
        else:
            st.success(f"📊 Found {len(subtitles)} subtitle segments")
            moments = find_viral_moments(subtitles, clip_duration, clip_duration)
        
        if not moments:
            st.warning("⚠️ No viral moments detected. Creating clips from the beginning.")
            # Create moments manually
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
        
        st.info(f"🎯 Found {len(moments)} potential viral moments")
        
        # Limit to max_clips
        moments = moments[:max_clips]
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        clips_container = st.container()
        
        clips = []
        
        for i, moment in enumerate(moments):
            status_text.text(f"🎬 Creating clip {i+1}/{len(moments)}...")
            progress_bar.progress((i) / len(moments))
            
            clip = create_shorts_clip(
                video_path, moment, background_style, visual_preset, motion_effects, temp_dir, i
            )
            
            if clip:
                clips.append(clip)
                
                # Display clip info
                with clips_container.expander(f"📹 Clip {i+1} - {clip['duration']}s ({clip['size_mb']} MB)", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Score:** {clip['score']}")
                        st.write(f"**Start Time:** {clip['start_time']:.1f}s")
                    with col2:
                        st.write(f"**Duration:** {clip['duration']}s")
                        st.write(f"**Size:** {clip['size_mb']} MB")
                    st.write(f"**Trigger:** {clip['trigger_text']}")
        
        progress_bar.progress(1.0)
        status_text.text("✅ All clips created successfully!")
        
        st.session_state.clips = clips
        
        if clips:
            st.success(f"🎉 Successfully created {len(clips)} shorts clips!")
            
            # Create download ZIP
            with st.spinner("📦 Creating download package..."):
                zip_path = create_download_zip(clips, temp_dir)
            
            # Download button
            if os.path.exists(zip_path):
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                st.download_button(
                    label="📥 Download All Clips (ZIP)",
                    data=zip_data,
                    file_name="youtube_shorts_clips.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            
            # Individual download buttons
            st.subheader("📁 Individual Downloads")
            for clip in clips:
                if os.path.exists(clip['file']):
                    with open(clip['file'], 'rb') as f:
                        video_data = f.read()
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{clip['filename']}** - {clip['duration']}s ({clip['size_mb']} MB)")
                    with col2:
                        st.download_button(
                            label="⬇️ Download",
                            data=video_data,
                            file_name=clip['filename'],
                            mime="video/mp4",
                            key=f"download_{clip['filename']}"
                        )
        else:
            st.error("❌ No clips were created successfully. Please try again.")

# Display tips
with st.expander("💡 Tips for Best Results"):
    st.write("""
    **Visual Settings Guide:**
    - **Blurred Background**: Creates cinematic depth with blurred original video as background
    - **Gradient Background**: Modern, clean look with gradient overlay
    - **Original Crop**: Simple center crop of original video
    
    **Visual Presets:**
    - **Platform Optimized**: Balanced colors perfect for TikTok, Instagram, YouTube
    - **Cinematic**: Film-like color grading with warm tones
    - **High Energy**: Vibrant, saturated colors for exciting content
    - **Minimal**: Clean, subtle enhancement for professional content
    
    **Best Practices:**
    - Use videos with clear speech and engaging content
    - 30-second clips work best for most platforms
    - Enable motion effects for more dynamic videos
    - Longer source videos provide more viral moment options
    """)

# Footer
st.markdown("---")
st.markdown("🎬 **Enhanced YouTube Shorts Generator** - Transform long-form content into engaging shorts with professional styling!")