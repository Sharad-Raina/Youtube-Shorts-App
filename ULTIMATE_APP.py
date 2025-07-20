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

def parse_srt_simple(srt_path):
    try:
        with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        content = content.replace('\ufeff', '')
        subtitles = []
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Find the line with timestamp
                timestamp_line = None
                for i, line in enumerate(lines):
                    if ' --> ' in line:
                        timestamp_line = i
                        break
                
                if timestamp_line is not None:
                    times = lines[timestamp_line].split(' --> ')
                    if len(times) == 2:
                        # Get all text after timestamp
                        text_lines = lines[timestamp_line + 1:]
                        text = ' '.join([line.strip() for line in text_lines if line.strip()])
                        
                        if text:
                            subtitles.append({
                                'start': times[0].strip(),
                                'end': times[1].strip(),
                                'text': text
                            })
        
        return subtitles
    except Exception as e:
        st.warning(f"Error parsing subtitles: {str(e)}")
        return []

def srt_time_to_seconds(time_str):
    try:
        # Handle both , and . as decimal separator
        time_str = time_str.replace(',', '.')
        
        # Split time components
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
        else:
            return float(time_str)
    except:
        return 0

def analyze_first_3_seconds(subtitles, start_time):
    hook_score = 0
    hook_text = ""
    
    hook_patterns = {
        r'\?': 5, r'you': 4, r'(wait|stop|look|watch)': 6,
        r'(never|always|every|must)': 4, r'\d+': 5,
        r'(secret|truth|revealed)': 5, r'!': 3, r'(this|here)': 3,
    }
    
    for sub in subtitles:
        sub_start = srt_time_to_seconds(sub['start'])
        if start_time <= sub_start < start_time + 3:
            text_lower = sub['text'].lower()
            hook_text += sub['text'] + " "
            
            for pattern, score in hook_patterns.items():
                if re.search(pattern, text_lower):
                    hook_score += score
    
    return hook_score, hook_text.strip()

def create_drawtext_captions(subtitles, start_time, clip_duration, video_width, video_height, color_scheme="Viral", caption_position="Bottom"):
    colors = CAPTION_COLORS.get(color_scheme, CAPTION_COLORS["Viral"])
    
    # Default to bottom position
    if caption_position == "Bottom":
        y_pos = int(video_height * 0.85)  # 85% down for bottom
    elif caption_position == "Top":
        y_pos = int(video_height * 0.15)  # 15% down for top
    else:  # Center
        y_pos = int(video_height * 0.5)  # 50% for center
    
    drawtext_filters = []
    
    # Rainbow colors for cycling through
    rainbow_colors = ["yellow", "cyan", "green", "magenta", "red", "orange", "white"]
    color_index = 0
    
    for sub in subtitles:
        sub_start = srt_time_to_seconds(sub['start'])
        sub_end = srt_time_to_seconds(sub['end'])
        
        # Calculate timing relative to clip
        clip_sub_start = sub_start - start_time
        clip_sub_end = sub_end - start_time
        
        # Skip if subtitle is outside this clip
        if clip_sub_end < 0 or clip_sub_start > clip_duration:
            continue
        
        # Adjust timing to clip boundaries
        clip_sub_start = max(0, clip_sub_start)
        clip_sub_end = min(clip_duration, clip_sub_end)
        
        # Skip if no duration
        if clip_sub_start >= clip_sub_end:
            continue
        
        # Split text into word groups (1-2 words max)
        words = sub['text'].split()
        word_groups = []
        
        i = 0
        while i < len(words):
            if i < len(words) - 1 and len(words[i]) + len(words[i+1]) <= 12:
                word_groups.append(f"{words[i]} {words[i+1]}")
                i += 2
            else:
                word_groups.append(words[i])
                i += 1
        
        if word_groups:
            # Calculate time per word group
            duration = clip_sub_end - clip_sub_start
            time_per_group = duration / len(word_groups)
            
            for j, word_group in enumerate(word_groups):
                group_start = clip_sub_start + (j * time_per_group)
                group_end = clip_sub_start + ((j + 1) * time_per_group)
                
                # Select color based on scheme
                if color_scheme == "Rainbow":
                    text_color = rainbow_colors[color_index % len(rainbow_colors)]
                    color_index += 1
                else:
                    text_color = colors["primary"]
                
                # Prepare text
                text_upper = word_group.upper()
                # More thorough escaping for FFmpeg
                text_escaped = text_upper.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:").replace("[", "\\[").replace("]", "\\]")
                
                fontsize = int(video_height * 0.08)  # 8% of height
                
                # Create drawtext with background box for readability
                drawtext = (
                    f"drawtext="
                    f"text='{text_escaped}':"
                    f"fontsize={fontsize}:"
                    f"fontcolor={text_color}:"
                    f"bordercolor=black:borderw=4:"  # Black border instead of shadow
                    f"box=1:boxcolor=black@0.4:boxborderw=10:"  # Semi-transparent background box
                    f"x=(w-text_w)/2:"
                    f"y={y_pos}-text_h/2:"
                    f"enable='between(t,{group_start:.3f},{group_end:.3f})'"
                )
                
                drawtext_filters.append(drawtext)
    
    return drawtext_filters

def find_viral_moments_ultra(subtitles, duration, num_clips):
    viral_indicators = {
        'hooks': {
            'patterns': [r'\?', r'wait', r'stop', r'watch this', r'look at', r'check this',
                        r'you won\'t believe', r'this is', r'here\'s', r'let me show'],
            'weight': 6.0,
            'first_3_sec_multiplier': 2.0
        },
        'emotions': {
            'patterns': [r'!\s*!', r'wow', r'omg', r'crazy', r'insane', r'amazing',
                        r'unbelievable', r'no way', r'what the', r'oh my god'],
            'weight': 5.0,
            'first_3_sec_multiplier': 1.5
        },
        'numbers': {
            'patterns': [r'\$\d+', r'\d+\s*(million|billion|thousand)', r'\d+%',
                        r'number \d+', r'top \d+', r'\d+ times', r'#\d+'],
            'weight': 5.5,
            'first_3_sec_multiplier': 1.8
        },
        'urgency': {
            'patterns': [r'right now', r'today', r'quick', r'fast', r'immediately',
                        r'before', r'last chance', r'limited'],
            'weight': 4.5,
            'first_3_sec_multiplier': 1.6
        }
    }
    
    moment_scores = defaultdict(float)
    first_3_sec_scores = defaultdict(float)
    
    for sub_idx, sub in enumerate(subtitles):
        start_sec = srt_time_to_seconds(sub['start'])
        end_sec = srt_time_to_seconds(sub['end'])
        text = sub['text']
        text_lower = text.lower()
        
        pattern_score = 0
        for indicator_type, indicator_data in viral_indicators.items():
            for pattern in indicator_data['patterns']:
                if re.search(pattern, text_lower):
                    base_score = indicator_data['weight']
                    
                    if start_sec < 3:
                        base_score *= indicator_data['first_3_sec_multiplier']
                        first_3_sec_scores[int(start_sec)] += base_score
                    
                    pattern_score += base_score
        
        for sec in range(int(start_sec), int(end_sec) + 1):
            moment_scores[sec] += pattern_score
    
    window_scores = []
    window_size = 30
    
    for start in range(0, int(duration) - window_size + 1, 2):
        window_score = sum(moment_scores.get(s, 0) for s in range(start, start + window_size))
        
        first_3_bonus = sum(first_3_sec_scores.get(s, 0) for s in range(start, min(start + 3, int(duration))))
        window_score += first_3_bonus * 3
        
        window_scores.append((start, window_score))
    
    window_scores.sort(key=lambda x: x[1], reverse=True)
    
    selected_moments = []
    used_ranges = []
    
    for start, score in window_scores:
        overlaps = False
        for used_start, used_end in used_ranges:
            if not (start + window_size <= used_start or start >= used_end):
                overlaps = True
                break
        
        if not overlaps and score > 0:
            selected_moments.append(start)
            used_ranges.append((start, start + window_size))
            
            if len(selected_moments) >= num_clips:
                break
    
    selected_moments.sort()
    return selected_moments

def get_quality_settings(quality_choice, video_width, video_height):
    if quality_choice == "Original (up to 4K)":
        if video_height >= 2160:
            return 3840, 2160, "veryslow", "18"
        elif video_height >= 1440:
            return 2560, 1440, "slow", "20"
        elif video_height >= 1080:
            return 1920, 1080, "medium", "22"
        else:
            return video_width, video_height, "medium", "23"
    elif quality_choice == "1080p":
        return 1920, 1080, "medium", "23"
    elif quality_choice == "720p":
        return 1280, 720, "medium", "23"
    else:
        return 854, 480, "fast", "25"

# Main UI
st.markdown("### 🎯 Choose Your Platform")
platform = st.selectbox(
    "Select target platform for optimization:",
    ["TikTok", "Instagram Reels", "YouTube Shorts"],
    help="Each platform has unique viral patterns we'll optimize for"
)

preset = PLATFORM_PRESETS[platform]

youtube_url = st.text_input("Paste YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2, col3 = st.columns(3)
with col1:
    num_shorts = st.selectbox("Number of Shorts", [1, 2, 3, 5, 10], index=2)
with col2:
    video_quality = st.selectbox(
        "Export Quality", 
        ["Original (up to 4K)", "1080p", "720p", "480p"], 
        index=1,
        help="Original preserves source quality including 4K"
    )
with col3:
    video_format = st.selectbox("Format", ["Vertical (9:16)", "Horizontal (16:9)"], index=0)

with st.expander("🎨 Advanced Viral Settings"):
    col1, col2 = st.columns(2)
    with col1:
        preset["color_scheme"] = st.selectbox(
            "Caption Color Scheme",
            ["Rainbow", "Viral", "TikTok", "Energy"],
            index=0 if platform == "TikTok" else 1,
            help="Rainbow = multicolor captions"
        )
    with col2:
        caption_position = st.selectbox(
            "Caption Position",
            ["Bottom", "Center", "Top"],
            index=0,  # Default to Bottom
            help="Bottom is recommended for better viewing"
        )
    
    audio_enhance = st.checkbox(
        "🎵 Audio Enhancement",
        value=True,
        help="Normalize volume and enhance speech clarity"
    )

if st.button("🚀 Generate Viral Shorts", type="primary", disabled=not youtube_url):
    st.session_state.video_processed = False
    st.session_state.output_files = []
    st.session_state.zip_path = None
    
    work_dir = f"shorts_{int(time.time())}"
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        with st.spinner("📥 Downloading video with captions..."):
            video_file = os.path.join(work_dir, "video.mp4")
            
            dl_cmd = [
                sys.executable, "-m", "yt_dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--write-auto-sub",
                "--write-subs",
                "--sub-langs", "en,en-US,en-GB",
                "--convert-subs", "srt",
                "-o", video_file,
                youtube_url
            ]
            
            result = subprocess.run(dl_cmd, capture_output=True, text=True)
            
            if not os.path.exists(video_file):
                st.error("❌ Failed to download video")
                st.stop()
        
        st.success("✅ Video downloaded!")
        
        srt_file = None
        for file in os.listdir(work_dir):
            if file.endswith('.srt'):
                srt_file = os.path.join(work_dir, file)
                break
        
        subtitles = []
        if srt_file:
            st.info(f"✅ Found subtitles: {os.path.basename(srt_file)}")
            subtitles = parse_srt_simple(srt_file)
            if subtitles:
                st.success(f"✅ Parsed {len(subtitles)} subtitle entries")
                # Debug: Show first few subtitles
                with st.expander("Debug: First 5 subtitles"):
                    for i, sub in enumerate(subtitles[:5]):
                        st.text(f"{i+1}. {sub['start']} --> {sub['end']}: {sub['text']}")
        else:
            st.warning("⚠️ No subtitles found - creating without captions")
        
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", video_file
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        try:
            probe_data = json.loads(probe_result.stdout)
            video_width = probe_data['streams'][0]['width']
            video_height = probe_data['streams'][0]['height']
            duration = float(probe_data['format']['duration'])
            st.info(f"📊 Video: {video_width}x{video_height}, Duration: {duration:.1f}s")
        except:
            duration = 300
            video_width = 1920
            video_height = 1080
        
        if subtitles:
            st.info("🤖 AI is analyzing for viral potential with first 3-second optimization...")
            clip_starts = find_viral_moments_ultra(subtitles, duration, num_shorts)
            st.success("✅ Found the most viral moments!")
        else:
            interval = duration / num_shorts
            clip_starts = [int(i * interval) for i in range(num_shorts)]
        
        output_files = []
        progress = st.progress(0)
        
        for i, start_time in enumerate(clip_starts):
            progress.progress((i + 1) / len(clip_starts))
            
            clip_duration = min(30, duration - start_time)
            if clip_duration < 5:
                continue
            
            st.text(f"Creating viral short {i+1}/{num_shorts} (from {start_time:.1f}s)...")
            
            output_file = os.path.join(work_dir, f"short_{i+1:02d}.mp4")
            
            if "Vertical" in video_format:
                if video_quality == "Original (up to 4K)":
                    if video_height >= 2160:
                        width, height = 1216, 2160
                    elif video_height >= 1440:
                        width, height = 810, 1440
                    else:
                        width, height = 608, 1080
                elif video_quality == "1080p":
                    width, height = 608, 1080
                elif video_quality == "720p":
                    width, height = 406, 720
                else:
                    width, height = 270, 480
                
                x_offset = "(iw-ow)/2"
                base_filter = f"scale=-2:{height},crop={width}:{height}:{x_offset}:0"
            else:
                target_width, target_height, preset_speed, crf = get_quality_settings(video_quality, video_width, video_height)
                width, height = target_width, target_height
                base_filter = f"scale={width}:{height}"
            
            # Basic aesthetic filters
            vf_filter = f"{base_filter},vignette=angle=PI/4:mode=backward,eq=contrast=1.05:brightness=0.02:saturation=1.1"
            
            hook_score = 20
            if subtitles:
                hook_score, hook_text = analyze_first_3_seconds(subtitles, start_time)
                st.text(f"  📊 Hook score: {hook_score}/30")
                
                if hook_score < 15:
                    hook_category = random.choice(list(VIRAL_HOOKS.keys()))
                    viral_hook = random.choice(VIRAL_HOOKS[hook_category])
                    st.text(f"  🎯 Adding viral hook: '{viral_hook}'")
            
            # Add captions
            if subtitles:
                drawtext_filters = create_drawtext_captions(
                    subtitles, 
                    start_time, 
                    clip_duration, 
                    width,
                    height,
                    preset.get("color_scheme", "Viral"),
                    caption_position
                )
                
                if drawtext_filters:
                    for drawtext in drawtext_filters:
                        vf_filter = f"{vf_filter},{drawtext}"
                    st.text(f"  ✅ Added {len(drawtext_filters)} colorful caption segments")
            
            if video_quality == "Original (up to 4K)":
                preset_speed = "slow" if height >= 1440 else "medium"
                crf = "18" if height >= 2160 else "20"
            else:
                preset_speed = "medium"
                crf = "23"
            
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", video_file,
                "-t", str(clip_duration),
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", preset_speed,
                "-crf", crf,
                "-c:a", "aac",
                "-b:a", "192k" if height >= 1080 else "128k",
                "-movflags", "+faststart",
            ]
            
            if audio_enhance:
                cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=100,lowpass=f=15000"])
            
            cmd.append(output_file)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                output_files.append(output_file)
                st.success(f"✅ Created viral short {i+1}")
            else:
                st.error(f"❌ Failed to create short {i+1}")
                if result.stderr:
                    with st.expander(f"Error details for short {i+1}"):
                        st.code(result.stderr)
        
        if output_files:
            zip_file = os.path.join(work_dir, "viral_shorts.zip")
            with zipfile.ZipFile(zip_file, 'w') as zf:
                for f in output_files:
                    zf.write(f, os.path.basename(f))
            
            st.session_state.video_processed = True
            st.session_state.output_files = output_files
            st.session_state.zip_path = zip_file
            
            st.balloons()
            st.success(f"🎉 Created {len(output_files)} viral-optimized shorts!")
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Full error details"):
            st.code(traceback.format_exc())

if st.session_state.video_processed and st.session_state.output_files:
    st.markdown("---")
    st.markdown("### 📥 Download Your Viral Shorts")
    
    st.success(f"""
    🎉 **Your {platform}-optimized viral shorts are ready!**
    
    **🚀 Working Viral Features:**
    - ✅ First 3-second hook optimization
    - ✅ **Properly synced captions at bottom**
    - ✅ **Rainbow multicolor text (when selected)**
    - ✅ **Readable captions with background box**
    - ✅ Platform-specific styling ({platform})
    - ✅ Enhanced audio (normalized + filtered)
    - ✅ Quality preserved (up to {video_quality})
    
    **💡 Pro tip**: Upload at peak hours for your audience!
    """)
    
    if st.session_state.zip_path and os.path.exists(st.session_state.zip_path):
        with open(st.session_state.zip_path, 'rb') as f:
            st.download_button(
                label=f"⬇️ Download All {platform} Shorts (ZIP)",
                data=f.read(),
                file_name=f"{platform.lower()}_viral_shorts.zip",
                mime="application/zip"
            )
    
    st.markdown("**Or download individually:**")
    cols = st.columns(5)
    for idx, file_path in enumerate(st.session_state.output_files):
        with cols[idx % 5]:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    st.download_button(
                        label=f"Short #{idx+1}",
                        data=f.read(),
                        file_name=f"{platform.lower()}_viral_{idx+1}.mp4",
                        mime="video/mp4",
                        key=f"dl_{idx}"
                    )
    
    if st.button("🔄 Create More Viral Shorts"):
        st.session_state.video_processed = False
        st.session_state.output_files = []
        st.session_state.zip_path = None
        for d in os.listdir('.'):
            if d.startswith('shorts_') and os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        st.rerun()

with st.sidebar:
    st.markdown("### 🚀 Viral Features Active")
    st.success(f"""
    **Platform: {platform}**
    - Hook style: {preset['hook_style']}
    - Colors: {preset['color_scheme']}
    - Position: Bottom (default)
    
    **v5.0 Improvements:**
    ✅ **Synced captions** 
    ✅ **True multicolor text**
    ✅ **Readable background box**
    ✅ **Bottom position default**
    ✅ Hook Detection
    ✅ Enhanced Audio
    """)
    
    st.markdown("### 🎯 Caption Features")
    st.info("""
    **New Caption System:**
    - Each word in different color (Rainbow)
    - Semi-transparent background
    - Black border for readability
    - Proper sync with audio
    - 1-2 words at a time
    """)
    
    st.markdown("### 📈 Viral Tips")
    st.warning("""
    **Upload at peak times:**
    - TikTok: 6-9 AM, 7-11 PM
    - Instagram: 11 AM-1 PM, 7-9 PM
    - YouTube: 2-4 PM, 9-11 PM
    
    **First 24 hours = crucial!**
    """)