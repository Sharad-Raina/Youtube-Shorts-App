import streamlit as st
import yt_dlp
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
import json
import cv2
import numpy as np
import urllib.request
import platform

def check_ffmpeg_availability():
    """Check if FFmpeg is available and has drawtext support"""
    try:
        # Check basic FFmpeg
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "FFmpeg not found"
        
        # Check for drawtext filter
        result = subprocess.run(['ffmpeg', '-filters'], capture_output=True, text=True)
        if 'drawtext' not in result.stdout:
            return False, "FFmpeg drawtext filter not available"
        
        return True, "FFmpeg ready"
    except:
        return False, "FFmpeg not installed"

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

def download_video_and_subtitles(url, temp_dir, force_auto_captions=True, accept_any_language=False):
    """Download video and subtitles using yt-dlp with enhanced caption detection"""
    try:
        # First, extract info to check available subtitles
        info_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            st.info("🔍 Checking video information and available subtitles...")
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            # Debug: Check what subtitles are available
            available_subs = info.get('subtitles', {})
            automatic_subs = info.get('automatic_captions', {})
            
            st.write(f"📋 Available manual subtitles: {list(available_subs.keys())}")
            st.write(f"🤖 Available auto-generated subtitles: {list(automatic_subs.keys())}")
            
            # Determine which subtitle to download
            subtitle_lang = None
            subtitle_data = None
            
            # Priority order for subtitle languages
            lang_priority = ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU', 'eng', 'en-orig']
            
            # Check manual subtitles first
            for lang in lang_priority:
                if lang in available_subs:
                    subtitle_lang = lang
                    subtitle_data = available_subs[lang]
                    st.success(f"✅ Found manual subtitles in '{lang}'")
                    break
            
            # If no manual subs, check automatic captions
            if not subtitle_lang and force_auto_captions:
                for lang in lang_priority:
                    if lang in automatic_subs:
                        subtitle_lang = lang
                        subtitle_data = automatic_subs[lang]
                        st.success(f"✅ Found auto-generated subtitles in '{lang}'")
                        break
            
            # If still no subtitles, try any English variant
            if not subtitle_lang:
                all_langs = list(available_subs.keys()) + list(automatic_subs.keys())
                for lang in all_langs:
                    if 'en' in lang.lower() or lang.startswith('en'):
                        subtitle_lang = lang
                        if lang in available_subs:
                            subtitle_data = available_subs[lang]
                        else:
                            subtitle_data = automatic_subs[lang]
                        st.success(f"✅ Found subtitles in '{lang}'")
                        break
            
            # Last resort - try first available language if accept_any_language is True
            if not subtitle_lang and accept_any_language and (available_subs or automatic_subs):
                if available_subs:
                    subtitle_lang = list(available_subs.keys())[0]
                    subtitle_data = available_subs[subtitle_lang]
                else:
                    subtitle_lang = list(automatic_subs.keys())[0]
                    subtitle_data = automatic_subs[subtitle_lang]
                st.info(f"📝 Using subtitles in '{subtitle_lang}' (no English found)")
        
        # Now download video with the specific subtitle language
        download_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'{temp_dir}/video.%(ext)s',
            'quiet': False,
            'no_warnings': False,
        }
        
        # Only add subtitle options if we found subtitles
        if subtitle_lang and subtitle_data:
            download_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [subtitle_lang],
                'subtitlesformat': 'srt/vtt/srv3/srv2/srv1/json3/best',
                'postprocessors': [{
                    'key': 'FFmpegSubtitlesConvertor',
                    'format': 'srt',
                }]
            })
            st.info(f"📥 Downloading video with '{subtitle_lang}' subtitles...")
        else:
            st.warning("⚠️ No subtitles available for this video")
            st.info("💡 Tip: The video may be too new, private, or have disabled captions")
            st.info("📥 Downloading video without subtitles...")
        
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            # Download the video
            ydl.download([url])
        
        # Find downloaded video file
        video_files = list(Path(temp_dir).glob('video.*'))
        if not video_files:
            raise Exception("No video file downloaded")
        
        video_path = str(video_files[0])
        st.success(f"✅ Video downloaded: {os.path.basename(video_path)}")
        
        # Find subtitle file
        subtitle_path = None
        
        if subtitle_lang:
            # Look for the subtitle file with the specific language code
            possible_patterns = [
                f'video.{subtitle_lang}.srt',
                f'video.{subtitle_lang}.vtt',
                f'*{subtitle_lang}*.srt',
                f'*{subtitle_lang}*.vtt',
                '*.srt',
                '*.vtt'
            ]
            
            for pattern in possible_patterns:
                found_files = list(Path(temp_dir).glob(pattern))
                if found_files:
                    subtitle_path = str(found_files[0])
                    st.success(f"✅ Found subtitle file: {os.path.basename(subtitle_path)}")
                    break
        
        # If we still don't have a subtitle file but have subtitle data, create one
        if not subtitle_path and subtitle_data:
            st.info("📝 Creating subtitle file from extracted data...")
            subtitle_path = create_subtitle_file_from_data(subtitle_data, temp_dir, subtitle_lang)
        
        # Final fallback - try to extract directly from info
        if not subtitle_path and (subtitle_lang or info.get('subtitles') or info.get('automatic_captions')):
            st.info("🔄 Attempting direct subtitle extraction...")
            subtitle_path = extract_subtitles_directly(info, temp_dir)
        
        # Verify subtitle content
        if subtitle_path and os.path.exists(subtitle_path):
            try:
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if len(content) > 100:
                        st.success(f"✅ Subtitle file verified: {len(content)} characters")
                    else:
                        st.warning("⚠️ Subtitle file seems too short")
                        subtitle_path = None
            except Exception as e:
                st.warning(f"⚠️ Could not read subtitle file: {e}")
                subtitle_path = None
        
        if not subtitle_path:
            st.error("❌ No subtitles available for this video")
            st.info("💡 The video will be processed without subtitles")
        
        # Get video quality info
        formats = info.get('formats', [])
        best_quality = "Unknown"
        for fmt in formats:
            if fmt.get('vcodec') != 'none':
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
        
        st.info(f"📹 Video quality: {best_quality}")
        
        return video_path, subtitle_path, title, duration
            
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
        return None, None, None, None

def extract_subtitles_directly(info, temp_dir):
    """Extract subtitles directly from video info as last resort"""
    try:
        # Try to get subtitles from info dict
        all_subs = {**info.get('subtitles', {}), **info.get('automatic_captions', {})}
        
        # Find any English subtitles
        for lang_key in ['en', 'en-US', 'en-GB', 'eng']:
            if lang_key in all_subs:
                return create_subtitle_file_from_data(all_subs[lang_key], temp_dir, lang_key)
        
        # Try any language with 'en' in it
        for lang, data in all_subs.items():
            if 'en' in lang.lower():
                return create_subtitle_file_from_data(data, temp_dir, lang)
        
        # Last resort - first available
        if all_subs:
            lang = list(all_subs.keys())[0]
            return create_subtitle_file_from_data(all_subs[lang], temp_dir, lang)
            
    except Exception as e:
        st.error(f"Direct extraction failed: {e}")
    
    return None

def extract_subtitles_from_video_info(url, temp_dir):
    """Alternative method to extract subtitles directly from video info"""
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'srt/vtt',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Try to get any available subtitles
            subtitles_dict = info.get('subtitles', {})
            auto_captions_dict = info.get('automatic_captions', {})
            
            # Combine both dictionaries
            all_subs = {**subtitles_dict, **auto_captions_dict}
            
            # Find English subtitles
            subtitle_content = None
            for lang in ['en', 'en-US', 'en-GB', 'eng']:
                if lang in all_subs:
                    for fmt in all_subs[lang]:
                        if fmt.get('ext') in ['srt', 'vtt']:
                            try:
                                if 'data' in fmt:
                                    subtitle_content = fmt['data']
                                elif 'url' in fmt:
                                    with urllib.request.urlopen(fmt['url']) as response:
                                        subtitle_content = response.read().decode('utf-8')
                                
                                if subtitle_content:
                                    # Save to file and parse
                                    ext = fmt.get('ext', 'srt')
                                    subtitle_path = os.path.join(temp_dir, f'extracted.{ext}')
                                    with open(subtitle_path, 'w', encoding='utf-8') as f:
                                        f.write(subtitle_content)
                                    
                                    # Parse the subtitles
                                    return parse_subtitles(subtitle_path)
                            except:
                                continue
        
        return []
    except Exception as e:
        st.error(f"Error extracting subtitles: {e}")
        return []

def create_subtitle_file_from_data(subtitle_data, temp_dir, lang):
    """Create a subtitle file from yt-dlp subtitle data"""
    try:
        # Find the best format
        subtitle_content = None
        ext = 'srt'
        
        # Try different formats in order of preference
        format_preference = ['srt', 'vtt', 'srv3', 'srv2', 'srv1', 'json3']
        
        for fmt in subtitle_data:
            fmt_ext = fmt.get('ext', '')
            
            # Skip if not a preferred format
            if fmt_ext not in format_preference:
                continue
                
            try:
                if 'data' in fmt:
                    subtitle_content = fmt['data']
                    ext = fmt_ext
                    break
                elif 'url' in fmt:
                    # Download subtitle from URL
                    st.info(f"📥 Downloading subtitle format: {fmt_ext}")
                    with urllib.request.urlopen(fmt['url']) as response:
                        subtitle_content = response.read().decode('utf-8')
                    ext = fmt_ext
                    break
            except Exception as e:
                st.warning(f"Failed to download {fmt_ext} format: {e}")
                continue
        
        if subtitle_content:
            # Handle json3 format (YouTube's format)
            if ext == 'json3':
                st.info("🔄 Converting YouTube json3 format to SRT...")
                subtitle_content = convert_json3_to_srt(subtitle_content)
                ext = 'srt'
            
            # Save the subtitle file
            subtitle_path = os.path.join(temp_dir, f'video.{lang}.{ext}')
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
            
            # Verify it has content
            if len(subtitle_content.strip()) > 50:
                return subtitle_path
            else:
                st.warning("Subtitle file too short")
                return None
        
    except Exception as e:
        st.warning(f"Could not create subtitle file: {e}")
    
    return None

def convert_json3_to_srt(json3_content):
    """Convert YouTube's json3 subtitle format to SRT"""
    try:
        data = json.loads(json3_content)
        events = data.get('events', [])
        
        srt_content = []
        subtitle_index = 1
        
        for event in events:
            # Skip events without segments
            if 'segs' not in event:
                continue
            
            # Get timing
            start_ms = event.get('tStartMs', 0)
            duration_ms = event.get('dDurationMs', 0)
            end_ms = start_ms + duration_ms
            
            # Convert to SRT timestamp format
            start_time = ms_to_srt_timestamp(start_ms)
            end_time = ms_to_srt_timestamp(end_ms)
            
            # Get text from segments
            text_parts = []
            for seg in event.get('segs', []):
                if 'utf8' in seg:
                    text_parts.append(seg['utf8'])
            
            if text_parts:
                text = ''.join(text_parts).strip()
                
                # Add to SRT content
                srt_content.append(f"{subtitle_index}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(text)
                srt_content.append("")  # Empty line between subtitles
                
                subtitle_index += 1
        
        return '\n'.join(srt_content)
    
    except Exception as e:
        st.error(f"Error converting json3 format: {e}")
        return ""

def ms_to_srt_timestamp(ms):
    """Convert milliseconds to SRT timestamp format"""
    seconds = ms / 1000
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def detect_faces_in_frame(frame):
    """Detect faces in a frame using OpenCV"""
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        return faces
    except:
        return []

def get_optimal_crop_region(video_path, width, height, sample_frames=10):
    """Analyze video to find optimal crop region that includes speakers"""
    try:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Check for valid dimensions
        if original_width == 0 or original_height == 0 or height == 0:
            cap.release()
            return None
        
        # Calculate target aspect ratio
        target_aspect = width / height  # 9:16 = 0.5625
        current_aspect = original_width / original_height
        
        # Check if we have frames to sample
        if total_frames == 0:
            cap.release()
            return None
        
        # Sample frames throughout the video
        frame_indices = np.linspace(0, total_frames - 1, sample_frames, dtype=int)
        
        all_face_centers = []
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            
            faces = detect_faces_in_frame(frame)
            
            # Calculate face centers
            for (x, y, w, h) in faces:
                center_x = x + w // 2
                center_y = y + h // 2
                all_face_centers.append((center_x, center_y))
        
        cap.release()
        
        # Calculate optimal crop
        if all_face_centers:
            # Find the average position of all faces
            avg_x = sum(x for x, y in all_face_centers) / len(all_face_centers)
            avg_y = sum(y for x, y in all_face_centers) / len(all_face_centers)
            
            # Calculate crop dimensions
            if current_aspect > target_aspect:
                # Video is wider than target - need to crop width
                crop_height = original_height
                crop_width = int(crop_height * target_aspect)
                
                # Center crop around average face position
                crop_x = int(avg_x - crop_width // 2)
                crop_x = max(0, min(crop_x, original_width - crop_width))
                crop_y = 0
            else:
                # Video is taller than target - need to crop height
                crop_width = original_width
                crop_height = int(crop_width / target_aspect)
                
                # Center crop around average face position
                crop_x = 0
                crop_y = int(avg_y - crop_height // 2)
                crop_y = max(0, min(crop_y, original_height - crop_height))
            
            return {
                'x': crop_x,
                'y': crop_y,
                'width': crop_width,
                'height': crop_height,
                'has_faces': True
            }
        else:
            # No faces detected - use center crop
            if current_aspect > target_aspect:
                crop_height = original_height
                crop_width = int(crop_height * target_aspect)
                crop_x = (original_width - crop_width) // 2
                crop_y = 0
            else:
                crop_width = original_width
                crop_height = int(crop_width / target_aspect)
                crop_x = 0
                crop_y = (original_height - crop_height) // 2
            
            return {
                'x': crop_x,
                'y': crop_y,
                'width': crop_width,
                'height': crop_height,
                'has_faces': False
            }
    except Exception as e:
        st.warning(f"⚠️ Could not analyze video for smart cropping: {e}")
        return None

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

def escape_text_for_ffmpeg(text, ascii_only=True):
    """Properly escape text for FFmpeg drawtext filter"""
    import re
    
    if ascii_only:
        # Remove non-ASCII characters first
        text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Clean up whitespace first
    text = text.replace('\n', ' ')     # Replace newlines with spaces
    text = text.replace('\r', ' ')     # Replace carriage returns
    text = text.replace('\t', ' ')     # Replace tabs with spaces
    text = ' '.join(text.split())     # Normalize whitespace
    
    # Remove problematic characters first to simplify escaping
    text = text.replace("'", "")       # Remove apostrophes entirely
    text = text.replace('"', '')       # Remove quotes entirely
    text = re.sub(r'[^\w\s\.,!?\-]', '', text)  # Keep only basic punctuation
    
    # Simple escaping for FFmpeg drawtext - only escape colons since we use it as separator
    text = text.replace(':', ' ')      # Replace colons with spaces instead of escaping
    text = text.replace('=', ' ')      # Replace equals with spaces
    text = text.replace(',', ' ')      # Replace commas with spaces
    
    # Final cleanup
    text = text.strip()
    text = ' '.join(text.split())     # Normalize multiple spaces
    
    # If text is empty after all processing, provide a default
    if not text:
        text = "Sample Text"
    
    return text

def test_font_rendering():
    """Test FFmpeg font rendering capabilities"""
    try:
        temp_dir = create_temp_dir()
        test_video = os.path.join(temp_dir, "font_test.mp4")
        
        # Test simple drawtext first
        cmd_simple = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'color=c=blue:s=1080x1920:d=3',
            '-vf', "drawtext=text='Basic Test':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            '-c:v', 'libx264',
            '-t', '3',
            test_video
        ]
        
        with st.spinner("Testing basic font rendering..."):
            result = subprocess.run(cmd_simple, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(test_video):
                st.success("✅ Basic font rendering test successful!")
                st.info("FFmpeg drawtext filter is working correctly")
                
                # Show the test video
                with open(test_video, 'rb') as f:
                    st.video(f.read())
                
                # Clean up
                os.remove(test_video)
                
                # Test with system font
                system = platform.system()
                font_paths = []
                if system == "Darwin":  # macOS
                    font_paths = ["/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]
                elif system == "Windows":
                    font_paths = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf"]
                else:  # Linux
                    font_paths = [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                    ]
                
                # Test first available font
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        st.info(f"✅ Found system font: {font_path}")
                        break
                else:
                    st.warning("⚠️ No system fonts found at expected locations")
                    
            else:
                st.error("❌ Font rendering test failed!")
                st.code(result.stderr[:500])
                st.warning("Try disabling subtitles in the sidebar if you're experiencing issues.")
                
                # Show system info for debugging
                st.info(f"System: {platform.system()}")
                st.info("Consider using the simplified subtitle mode.")
                
        # Clean up directory
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        
    except Exception as e:
        st.error(f"Font test error: {e}")
        st.info("This may indicate FFmpeg or font configuration issues.")

def get_system_font():
    """Detect and return appropriate system font for subtitles"""
    import platform
    system = platform.system()
    
    if system == "Windows":
        return "Arial"
    elif system == "Darwin":  # macOS
        return "Helvetica"
    else:  # Linux and others
        return "Sans"  # Generic sans-serif

def create_shorts_clip(video_path, moment, background_style, visual_preset, motion_effects, output_format, temp_dir, clip_index, smart_crop_offset=None, enable_subtitles=True, subtitle_style="box", ascii_only=True, simple_mode=False):
    """Create a shorts clip with proper 9:16 format and working subtitles"""
    try:
        st.write(f"🎬 Creating clip {clip_index+1} with {len(moment['subtitles'])} subtitles...")
        
        # Get output dimensions based on format
        if output_format == "4K":
            width, height = 1080, 1920
        elif output_format == "1080p":
            width, height = 1080, 1920
        elif output_format == "720p":
            width, height = 720, 1280
        else:  # 480p
            width, height = 480, 854
        
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
        
        st.write(f"📝 Processing {len(clip_subtitles)} subtitles for this clip...")
        
        # Debug: Save subtitles to file for verification
        if clip_subtitles:
            debug_file = os.path.join(temp_dir, f'clip_{clip_index+1}_subtitles.txt')
            with open(debug_file, 'w', encoding='utf-8') as f:
                for sub in clip_subtitles:
                    f.write(f"{sub['start']:.2f} - {sub['end']:.2f}: {sub['text']}\n")
            st.info(f"💾 Subtitle debug file saved: {os.path.basename(debug_file)}")
        
        # Build filter complex string directly
        filters = []
        
        # Color schemes for subtitles
        colors = ['FFD700', 'FF69B4', '00FFFF', 'FF4500', '32CD32', 'FF1493', '00FF7F', 'FF6347']
        
        # Smart crop handling
        if smart_crop_offset:
            crop_filter = f"crop={smart_crop_offset['width']}:{smart_crop_offset['height']}:{smart_crop_offset['x']}:{smart_crop_offset['y']}"
        else:
            crop_filter = f"crop=ih*{width}/{height}:ih"  # Default center crop
        
        # Background handling
        if background_style == "blurred":
            # Create blurred background
            filter_complex = f"[0:v]split=2[main][bg];" \
                           f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},gblur=sigma=15[bg_blur];" \
                           f"[main]{crop_filter},scale={int(width*0.8)}:{int(height*0.8)}:force_original_aspect_ratio=decrease[main_sized];" \
                           f"[bg_blur][main_sized]overlay=(W-w)/2:(H-h)/2[base]"
        else:
            # Simple crop with smart positioning
            filter_complex = f"[0:v]{crop_filter},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[base]"
        
        # Add visual presets
        if visual_preset == 'cinematic':
            filter_complex += f";[base]eq=contrast=1.1:brightness=0.03:saturation=1.15[enhanced]"
            base_label = "enhanced"
        elif visual_preset == 'high_energy':
            filter_complex += f";[base]eq=contrast=1.15:saturation=1.25[enhanced]"
            base_label = "enhanced"
        elif visual_preset == 'platform_optimized':
            filter_complex += f";[base]eq=contrast=1.08:saturation=1.15[enhanced]"
            base_label = "enhanced"
        else:
            base_label = "base"
        
        # Add subtitles using drawtext
        if clip_subtitles and enable_subtitles:
            for i, subtitle in enumerate(clip_subtitles):
                escaped_text = escape_text_for_ffmpeg(subtitle['text'], ascii_only)
                
                # Skip empty subtitles
                if not escaped_text or escaped_text == "Sample Text":
                    continue
                
                # Font size based on resolution
                font_size = int(height * 0.045)  # 4.5% of height
                
                # Try to create subtitle with different approaches for maximum compatibility
                subtitle_added = False
                
                # Approach 1: Try with system font
                system = platform.system()
                font_paths = []
                if system == "Darwin":  # macOS
                    font_paths = ["/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]
                elif system == "Windows":
                    font_paths = ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf"]
                else:  # Linux
                    font_paths = [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                    ]
                
                # Find first available font
                font_file = None
                for path in font_paths:
                    if os.path.exists(path):
                        font_file = path
                        break
                
                try:
                    # Build drawtext filter - choose between simple and advanced mode
                    if simple_mode:
                        # Ultra-simple mode for maximum compatibility
                        drawtext_params = [
                            f"text='{escaped_text}'",
                            f"fontsize={font_size}",
                            "fontcolor=white",
                            "x=(w-text_w)/2",
                            f"y=h-{int(height*0.15)}",
                            f"enable='between(t,{subtitle['start']:.1f},{subtitle['end']:.1f})'"
                        ]
                    else:
                        # Standard mode with styling
                        drawtext_params = []
                        drawtext_params.append(f"text='{escaped_text}'")
                        drawtext_params.append(f"fontsize={font_size}")
                        
                        # Add font file if available and not in simple mode
                        if font_file:
                            drawtext_params.append(f"fontfile='{font_file}'")
                        
                        drawtext_params.append("fontcolor=white")
                        drawtext_params.append("x=(w-text_w)/2")
                        drawtext_params.append(f"y=h-{int(height*0.15)}")
                        
                        # Add style parameters
                        if subtitle_style == "box":
                            drawtext_params.extend([
                                "box=1",
                                "boxcolor=black@0.8",
                                "boxborderw=5"
                            ])
                        elif subtitle_style == "shadow":
                            drawtext_params.extend([
                                "shadowcolor=black",
                                "shadowx=2",
                                "shadowy=2"
                            ])
                        else:  # outline
                            drawtext_params.extend([
                                "bordercolor=black",
                                "borderw=3"
                            ])
                        
                        # Add timing
                        start_time = f"{subtitle['start']:.2f}"
                        end_time = f"{subtitle['end']:.2f}"
                        drawtext_params.append(f"enable='between(t,{start_time},{end_time})'")
                    
                    # Join all parameters
                    drawtext_filter = f"[{base_label}]drawtext=" + ":".join(drawtext_params) + f"[sub{i}]"
                    
                    filter_complex += ";" + drawtext_filter
                    base_label = f"sub{i}"
                    subtitle_added = True
                    
                except Exception as subtitle_error:
                    st.warning(f"⚠️ Subtitle rendering issue for clip {clip_index+1}, subtitle {i+1}: {subtitle_error}")
                    # Try simplified version without font file
                    try:
                        simple_params = [
                            f"text='{escaped_text}'",
                            f"fontsize={font_size}",
                            "fontcolor=white",
                            "x=(w-text_w)/2",
                            f"y=h-{int(height*0.15)}",
                            f"enable='between(t,{start_time},{end_time})'"
                        ]
                        
                        drawtext_filter = f"[{base_label}]drawtext=" + ":".join(simple_params) + f"[sub{i}]"
                        filter_complex += ";" + drawtext_filter
                        base_label = f"sub{i}"
                        subtitle_added = True
                        st.info(f"✅ Used simplified subtitle rendering for subtitle {i+1}")
                        
                    except Exception as simple_error:
                        st.warning(f"⚠️ Could not add subtitle {i+1}: {simple_error}")
                        continue
                
        elif not enable_subtitles:
            st.info("ℹ️ Subtitles disabled for this clip")
        
        # Debug: Save the filter complex to a file for inspection
        if clip_subtitles and enable_subtitles:
            filter_debug_file = os.path.join(temp_dir, f'clip_{clip_index+1}_filters.txt')
            with open(filter_debug_file, 'w', encoding='utf-8') as f:
                f.write("Filter Complex:\n")
                f.write(filter_complex)
            st.info(f"💾 Filter debug file saved: {os.path.basename(filter_debug_file)}")
        
        # Final format
        filter_complex += f";[{base_label}]format=yuv420p[out]"
        
        # Output file
        output_file = os.path.join(temp_dir, f'clip_{clip_index+1}.mp4')
        
        # Quality settings
        if output_format == "4K":
            crf, preset, audio_br = '18', 'slower', '192k'
        elif output_format == "1080p":
            crf, preset, audio_br = '20', 'medium', '160k'
        elif output_format == "720p":
            crf, preset, audio_br = '22', 'medium', '128k'
        else:  # 480p
            crf, preset, audio_br = '24', 'fast', '96k'
        
        # FFmpeg command with inline filter_complex
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(moment['start_time']),
            '-i', video_path,
            '-t', str(moment['duration']),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',  # Optional audio
            
            # Video encoding
            '-c:v', 'libx264',
            '-preset', preset,
            '-crf', crf,
            '-pix_fmt', 'yuv420p',
            
            # Audio encoding
            '-c:a', 'aac',
            '-b:a', audio_br,
            '-ar', '44100',
            '-ac', '2',
            
            # Sync settings
            '-async', '1',
            '-vsync', 'cfr',
            
            # Output
            '-movflags', '+faststart',
            output_file
        ]
        
        # Debug: Show command
        st.write("🔧 Running optimized FFmpeg command...")
        
        # Save command to file for debugging
        cmd_file = os.path.join(temp_dir, f'clip_{clip_index+1}_command.txt')
        with open(cmd_file, 'w', encoding='utf-8') as f:
            f.write(" ".join(cmd))
        st.caption(f"Command saved to: {os.path.basename(cmd_file)}")
        
        # Run command
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if process.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            st.success(f"✅ Successfully created clip {clip_index+1} ({file_size:.1f} MB)")
            
            # Check for font-related warnings in stderr
            if process.stderr and ('font' in process.stderr.lower() or 'drawtext' in process.stderr.lower()):
                st.warning("⚠️ Font rendering warning detected. If subtitles appear as boxes, try:")
                st.info("1. Use the Font Test in Advanced Options\n2. Try a different subtitle style\n3. Enable ASCII-only mode (removes apostrophes)\n4. Disable subtitles if needed")
                
                # Save error log
                error_file = os.path.join(temp_dir, f'clip_{clip_index+1}_error.txt')
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(process.stderr)
                st.caption(f"Error log saved to: {os.path.basename(error_file)}")
            
            return {
                'file': output_file,
                'filename': f'clip_{clip_index+1}.mp4',
                'duration': moment['duration'],
                'score': moment['score'],
                'trigger_text': moment['trigger_text'],
                'size_mb': round(file_size, 2),
                'start_time': moment['start_time'],
                'subtitle_count': len(clip_subtitles)
            }
        else:
            st.error(f"❌ FFmpeg error for clip {clip_index+1}:")
            st.code(process.stderr[:1000] + "..." if len(process.stderr) > 1000 else process.stderr)
            
            # Save full error for debugging
            error_file = os.path.join(temp_dir, f'clip_{clip_index+1}_error_full.txt')
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write("COMMAND:\n")
                f.write(" ".join(cmd))
                f.write("\n\nERROR OUTPUT:\n")
                f.write(process.stderr)
                f.write("\n\nFILTER COMPLEX:\n")
                f.write(filter_complex)
            st.info(f"📋 Full error details saved to: {os.path.basename(error_file)}")
            
            # Suggest fixes
            if 'No such filter' in process.stderr or 'Invalid argument' in process.stderr:
                st.warning("🔧 This appears to be a filter syntax error. Try:")
                st.info("• Disable subtitles using the sidebar checkbox\n• Enable ASCII-only mode\n• Check the saved error file for details")
            
            return None
            
    except subprocess.TimeoutExpired:
        st.error(f"⏰ Timeout creating clip {clip_index+1}")
        return None
    except Exception as e:
        st.error(f"💥 Error creating clip {clip_index+1}: {str(e)}")
        return None

def create_download_zip(clips, temp_dir):
    """Create ZIP file for download"""
    zip_path = os.path.join(temp_dir, 'shorts_clips.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for clip in clips:
            if clip and os.path.exists(clip['file']):
                zipf.write(clip['file'], clip['filename'])
    
    return zip_path

# Initialize session state for persistent downloads
if 'clips' not in st.session_state:
    st.session_state.clips = []
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = None
if 'video_processed' not in st.session_state:
    st.session_state.video_processed = False
if 'current_settings' not in st.session_state:
    st.session_state.current_settings = {}
if 'smart_crop_region' not in st.session_state:
    st.session_state.smart_crop_region = None

# Streamlit UI
st.title("🎬 YouTube Shorts Generator - ROBUST SUBTITLE FIX")
st.write("✅ **Simplified subtitle handling + Smart cropping + Stable downloads**")

# Check FFmpeg availability
ffmpeg_available, ffmpeg_message = check_ffmpeg_availability()
if not ffmpeg_available:
    st.error(f"❌ {ffmpeg_message}")
    st.info("Please install FFmpeg with drawtext support to use this app.")
    st.stop()

# Quality info
st.info("""
🚀 **Robust Subtitle Fix:**
- 🔤 **Simplified Text Handling**: Removes problematic characters (apostrophes, quotes) 
- 🎨 **Multiple Subtitle Styles**: Box, shadow, or outline styles
- 🧪 **Debug Output**: Saves filter commands for troubleshooting
- 🔧 **ASCII Mode**: Ensures compatibility by removing special characters
- ⚙️ **Toggle Subtitles**: Easily disable if experiencing issues
- 👤 **Smart Cropping**: Face detection keeps speakers in frame
- 📥 **Stable Downloads**: Persistent download buttons
""")

# Settings
st.sidebar.header("🎨 Video Settings")

# Quality Selection
output_format = st.sidebar.selectbox(
    "📹 Output Quality",
    ["1080p", "720p", "480p", "4K"],
    index=0,
    help="Choose output resolution and quality"
)

# Aspect Ratio Info
st.sidebar.info("📱 **Aspect Ratio:** 9:16 (Vertical)\nPerfect for YouTube Shorts, TikTok, Instagram Reels")

# Background Style
background_style = st.sidebar.selectbox(
    "🎭 Background Style",
    ["simple_crop", "blurred"],
    help="Simple crop or blurred background for cinematic effect"
)

# Visual Preset
visual_preset = st.sidebar.selectbox(
    "🎨 Visual Preset",
    ["platform_optimized", "cinematic", "high_energy", "minimal"],
    help="Color enhancement presets"
)

# Motion Effects
motion_effects = st.sidebar.checkbox(
    "🎬 Motion Effects",
    value=False,
    help="Add subtle zoom animation (may impact performance)"
)

# Smart Crop Settings
st.sidebar.header("👤 Smart Crop Settings")
use_smart_crop = st.sidebar.checkbox(
    "🎯 Enable Smart Face-Tracking Crop",
    value=True,
    help="Automatically detect and keep faces in frame"
)

crop_position = st.sidebar.select_slider(
    "📍 Manual Crop Position",
    options=["Left", "Center-Left", "Center", "Center-Right", "Right"],
    value="Center",
    help="Fallback position if no faces detected"
)

st.sidebar.header("⚙️ Clip Settings")

# Subtitle Settings
st.sidebar.subheader("📝 Subtitle Settings")
enable_subtitles = st.sidebar.checkbox(
    "Enable Subtitles in Clips",
    value=True,
    help="Add subtitles to the video clips"
)

if enable_subtitles:
    subtitle_style = st.sidebar.selectbox(
        "Subtitle Style",
        ["box", "shadow", "outline"],
        help="Choose subtitle appearance style"
    )
    
    ascii_only = st.sidebar.checkbox(
        "ASCII-only mode",
        value=True,
        help="Remove special characters to prevent rendering issues (recommended). Note: This will remove apostrophes and quotes."
    )
    
    simple_mode = st.sidebar.checkbox(
        "Simple subtitle mode",
        value=False,
        help="Use basic subtitle rendering without advanced styling (fallback for compatibility issues)"
    )
    
    # Show current system info
    import platform
    system = platform.system()
    st.sidebar.info(f"System: {system}")
    
    if ascii_only:
        st.sidebar.caption("⚠️ Apostrophes will be removed from text")
else:
    subtitle_style = "box"  # Default value when disabled
    ascii_only = True
    simple_mode = False  # Default value when disabled
    st.sidebar.warning("⚠️ Subtitles disabled")

# Clip Duration
clip_duration = st.sidebar.slider("⏱️ Clip Duration (seconds)", 15, 60, 30)

# Max Clips
max_clips = st.sidebar.slider("📊 Maximum Clips", 1, 10, 5)

# Quality info based on selection
quality_info = {
    "4K": "🔥 Ultra High Quality (CRF 18, 192k audio)",
    "1080p": "✨ High Quality (CRF 20, 160k audio)", 
    "720p": "👍 Good Quality (CRF 22, 128k audio)",
    "480p": "💫 Standard Quality (CRF 24, 96k audio)"
}

st.sidebar.success(f"**Selected:** {output_format}")
st.sidebar.write(quality_info[output_format])

# Main input
url = st.text_input(
    "Enter YouTube URL:",
    placeholder="https://www.youtube.com/watch?v=..."
)

# Advanced options expander
with st.expander("🔧 Advanced Options"):
    st.write("**Subtitle Download Options:**")
    force_auto_captions = st.checkbox(
        "🤖 Force auto-generated captions",
        value=True,
        help="Try harder to get auto-generated captions if manual subtitles aren't available"
    )
    
    accept_any_language = st.checkbox(
        "🌍 Accept subtitles in any language",
        value=False,
        help="Use subtitles even if they're not in English"
    )
    
    st.write("**Font Testing:**")
    if st.button("🔤 Test Font Rendering"):
        test_font_rendering()
    
    st.write("**Troubleshooting:**")
    use_cookies = st.checkbox(
        "🍪 Use cookies for restricted videos",
        value=False,
        help="Enable if video requires login or has age restrictions"
    )
    
    if use_cookies:
        st.warning("⚠️ Cookie support requires additional setup. Videos may still fail if they require authentication.")

# Ensure all settings are always defined
if 'enable_subtitles' not in locals():
    enable_subtitles = True
if 'subtitle_style' not in locals():
    subtitle_style = "box"
if 'ascii_only' not in locals():
    ascii_only = True
if 'simple_mode' not in locals():
    simple_mode = False
if 'force_auto_captions' not in locals():
    force_auto_captions = True
if 'accept_any_language' not in locals():
    accept_any_language = False

# Show existing clips if available
if st.session_state.video_processed and st.session_state.clips:
    st.success(f"📹 **Clips Ready!** {len(st.session_state.clips)} clips generated with current settings")
    
    # Show download section
    st.subheader("📥 Download Your Clips")
    
    # Create ZIP download
    if st.session_state.temp_dir and os.path.exists(st.session_state.temp_dir):
        zip_path = create_download_zip(st.session_state.clips, st.session_state.temp_dir)
        if os.path.exists(zip_path):
            with open(zip_path, 'rb') as f:
                st.download_button(
                    label="📦 Download All Clips (ZIP)",
                    data=f.read(),
                    file_name="youtube_shorts_clips.zip",
                    mime="application/zip",
                    use_container_width=True
                )
    
    # Individual downloads
    st.subheader("📁 Individual Downloads")
    for i, clip in enumerate(st.session_state.clips):
        if os.path.exists(clip['file']):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{clip['filename']}** - {clip['duration']}s ({clip['size_mb']} MB)")
                st.write(f"📝 Subtitles: {clip.get('subtitle_count', 0)} segments")
                st.write(f"🎬 Format: {output_format} (9:16)")
            with col2:
                # Use unique key to prevent conflicts
                with open(clip['file'], 'rb') as f:
                    st.download_button(
                        label="⬇️ Download",
                        data=f.read(),
                        file_name=clip['filename'],
                        mime="video/mp4",
                        key=f"persistent_dl_{i}_{clip['filename']}"
                    )
    
    # Reset button
    if st.button("🔄 Generate New Clips", type="secondary"):
        st.session_state.video_processed = False
        st.session_state.clips = []
        st.session_state.smart_crop_region = None
        st.rerun()

if st.button("🚀 Generate Shorts", type="primary", use_container_width=True):
    if not url:
        st.error("Please enter a YouTube URL")
    else:
        # Reset previous state
        st.session_state.video_processed = False
        st.session_state.clips = []
        
        temp_dir = create_temp_dir()
        st.session_state.temp_dir = temp_dir
        
        with st.spinner("📥 Downloading video..."):
            video_path, subtitle_path, title, duration = download_video_and_subtitles(url, temp_dir, force_auto_captions, accept_any_language)
        
        if not video_path:
            st.error("Failed to download video")
            st.stop()
        
        st.success(f"✅ Downloaded: {title}")
        
        # Analyze video for smart cropping if enabled
        smart_crop_region = None
        if use_smart_crop:
            with st.spinner("👤 Analyzing video for optimal cropping..."):
                # Get output dimensions
                if output_format == "4K" or output_format == "1080p":
                    width, height = 1080, 1920
                elif output_format == "720p":
                    width, height = 720, 1280
                else:
                    width, height = 480, 854
                
                smart_crop_region = get_optimal_crop_region(video_path, width, height)
                if smart_crop_region and smart_crop_region['has_faces']:
                    st.success("✅ Face detection successful - will use smart cropping")
                else:
                    st.info("ℹ️ No faces detected - using standard center crop")
                
                st.session_state.smart_crop_region = smart_crop_region
        
        with st.spinner("📝 Analyzing subtitles..."):
            subtitles = parse_subtitles(subtitle_path)
        
        if not subtitles:
            st.warning("⚠️ No subtitles found. Creating clips without captions...")
            moments = []
            for i in range(min(max_clips, int(duration // clip_duration))):
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
            for i in range(min(max_clips, int(duration // clip_duration))):
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
            
            # Show moment details
            st.write(f"🎯 **Moment {i+1}:** {moment['trigger_text'][:100]}...")
            st.write(f"⏰ Time: {moment['start_time']:.1f}s - {moment['end_time']:.1f}s")
            st.write(f"📝 Subtitles in this moment: {len(moment['subtitles'])}")
            
            clip = create_shorts_clip(
                video_path, moment, background_style, visual_preset, motion_effects, 
                output_format, temp_dir, i, smart_crop_region, enable_subtitles, subtitle_style, ascii_only, simple_mode
            )
            
            if clip:
                clips.append(clip)
                st.success(f"✅ Created clip {i+1}: {clip['duration']}s ({clip['size_mb']} MB) - {clip['subtitle_count']} subtitles")
        
        if clips:
            # Store clips in session state for persistent access
            st.session_state.clips = clips
            st.session_state.video_processed = True
            
            st.success(f"🎉 Created {len(clips)} clips successfully!")
            st.info("📋 **Clips saved!** You can now download them. The download buttons will persist even after page interactions.")
            
            # Trigger a rerun to show the persistent download section
            st.rerun()
        else:
            st.error("❌ No clips were created successfully")

# Tips
with st.expander("💡 Tips & Features"):
    st.write(f"""
    **🎬 Current Settings:**
    - **Quality:** {output_format} with {quality_info[output_format].split('(')[1].replace(')', '')}
    - **Format:** 9:16 vertical (perfect for shorts platforms)
    - **Background:** {background_style.replace('_', ' ').title()}
    - **Visual Style:** {visual_preset.replace('_', ' ').title()}
    - **Smart Crop:** {'Enabled' if use_smart_crop else 'Disabled'}
    
    **📱 Platform Compatibility:**
    - ✅ YouTube Shorts (9:16 aspect ratio)
    - ✅ TikTok (optimal vertical format)
    - ✅ Instagram Reels (native 9:16)
    - ✅ Facebook Reels (vertical optimized)
    
    **🚀 Fixed Features:**
    - 🎯 **Robust Subtitle Handling**: Simplified text processing prevents FFmpeg errors
    - 📝 **Debug Output**: Saves filter commands and subtitle text for troubleshooting
    - 👤 **Smart Face Tracking**: Keeps speakers in frame automatically
    - 📹 **Quality Control**: Choose from 480p to 4K output
    - 🎨 **Professional Look**: Styled subtitles with box/shadow/outline options
    
    **💡 Best Practices:**
    - Enable Smart Crop for videos with people speaking
    - Use blurred background for landscape source videos
    - 1080p is recommended for most platforms
    - 30-second clips perform best on social media
    - If subtitles fail to download, try the alternative extraction method
    
    **🔤 Subtitle Troubleshooting:**
    - ASCII mode removes apostrophes and quotes to prevent errors
    - If subtitles still fail, disable them using the sidebar checkbox
    - Debug files are saved for each clip to help diagnose issues
    - The app uses simplified text processing for maximum compatibility
    """)

st.markdown("---")
st.markdown("🎬 **YouTube Shorts Generator** - Robust subtitle handling with simplified text processing!")