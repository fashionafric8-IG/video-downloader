import os
import logging
import re

import yt_dlp

def _is_valid_netscape(path):
    """Check if a cookies file follows the Netscape cookie file format required by yt-dlp.
    Returns True if the first non‑empty line starts with '# Netscape HTTP Cookie File'.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    return line.startswith('# Netscape HTTP Cookie File')
        return False
    except Exception:
        return False

# Use the same logger as app.py
logger = logging.getLogger(__name__)

def clean_filename(filename):
    """Removes special characters from filename to avoid filesystem issues."""
    # Keep alphanumeric, spaces, and common symbols like . [ ] - _
    # Replace everything else with nothing or underscore
    return re.sub(r'[^\w\s\.\-\[\]\(\)_]', '', filename).strip()

def get_video_info(url):
    """
    Extracts metadata and available formats for a given video URL.
    Does not download the video.
    """
    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'geo_bypass': True,
            'socket_timeout': 15,
            'source_address': '0.0.0.0', # Force IPv4
            'extractor_args': {'youtube': ['player_client=ios,android,web']},
        }

        # Include cookiefile if a valid cookies.txt exists
        if os.path.isfile('cookies.txt') and _is_valid_netscape('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {'error': 'Failed to fetch video information. The IP might be blocked or cookies expired.'}

        # Parse formats
        formats = []
        if isinstance(info, dict) and 'formats' in info:
            for f in info['formats']:
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                
                # Filter out AV1 codecs because they cause playback issues on many devices (especially for FB Reels)
                if vcodec:
                    vc = vcodec.lower()
                    if vc.startswith('av01') or vc.startswith('av1'):
                        continue
                
                # Filter for meaningful formats
                if vcodec != 'none' or acodec != 'none':
                    # Check if combined (contains both)
                    is_combined = vcodec != 'none' and acodec != 'none'
                    
                    # Format label
                    res = f.get('format_note') or f.get('resolution') or 'Audio'
                    size = f.get('filesize') or f.get('filesize_approx')
                    size_str = f"{round(size / (1024 * 1024), 1)} MB" if size else "Unknown Size"
                    
                    # We prioritize combined formats for the user because ffmpeg is missing
                    formats.append({
                        'id': f['format_id'],
                        'ext': f.get('ext', 'mp4'),
                        'res': res,
                        'size': size_str,
                        'combined': is_combined,
                        'type': 'Video' if vcodec != 'none' else 'Audio'
                    })

        # Apply cleaning to the filename derived from info
        raw_title = info.get('title', 'Unknown Title')
        cleaned_title = clean_filename(raw_title)
        
        return {
            'title': cleaned_title,
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration_string', ''),
            'formats': sorted(formats, key=lambda x: (x['combined'], x['res']), reverse=True)
        }
    except Exception as e:
        logger.error(f"ANALYZE ERROR: {str(e)}")
        return {"error": str(e)}

def download_video(url, format_id, output_dir):
    """Downloads a video using yt_dlp's Python API."""
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'format': format_id if format_id else 'bv*[ext=mp4][vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(output_dir, '%(title).100s [%(id)s].%(ext)s'),
        'restrict_filenames': True,
        'noplaylist': True,
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'socket_timeout': 30,
        'source_address': '0.0.0.0', # Force IPv4
        'max_filesize': 100 * 1024 * 1024,  # Limit to 100MB for VPS safety
        'extractor_args': {'youtube': ['player_client=ios,android,web']},
    }
    
    # Cookie Logic
    if os.path.isfile('cookies.txt') and _is_valid_netscape('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # yt_dlp returns the filename in info['requested_downloads'][0]['filepath'] if available
            if 'requested_downloads' in info and info['requested_downloads']:
                path = info['requested_downloads'][0].get('filepath')
                if path and os.path.exists(path):
                    return os.path.abspath(path)
            
            # Fallback: check info['_filename']
            path = info.get('_filename') or info.get('filename')
            if path and os.path.exists(path):
                return os.path.abspath(path)
                
            raise RuntimeError("yt-dlp finished but the output file could not be located.")
            
    except Exception as e:
        logger.exception("Download error")
        raise e
