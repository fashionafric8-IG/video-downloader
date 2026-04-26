import os
import logging
import subprocess
import re
import yt_dlp

# Use the same logger as app.py
logger = logging.getLogger(__name__)

def get_video_info(url):
    """
    Extracts metadata and available formats for a given video URL.
    Does not download the video.
    """
    # Use simple options for analysis
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Failed to extract info for {url}: {e}")
            return {'error': str(e)}

    # Parse formats
    formats = []
    if 'formats' in info:
        for f in info['formats']:
            vcodec = f.get('vcodec')
            acodec = f.get('acodec')
            
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

    return {
        'title': info.get('title', 'Unknown Title'),
        'thumbnail': info.get('thumbnail', ''),
        'duration': info.get('duration_string', ''),
        'formats': sorted(formats, key=lambda x: (x['combined'], x['res']), reverse=True)
    }

def download_video(url, format_id, output_dir):
    """
    Downloads a video using yt-dlp via subprocess for maximum reliability.
    Returns the absolute path to the downloaded file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Path to the yt-dlp executable
    ytdlp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'Scripts', 'yt-dlp.exe')
    if not os.path.exists(ytdlp_path):
        ytdlp_path = 'yt-dlp'

    # Safe filename template
    # We use %(title).100s to limit title length and %(id)s to ensure uniqueness
    outtmpl = os.path.join(output_dir, '%(title).100s [%(id)s].%(ext)s')
    
    # Selection logic:
    # If a specific format_id is provided, use it.
    # Otherwise, use 'best' (which defaults to best combined without ffmpeg)
    select_format = format_id if format_id else 'best[ext=mp4]/best'
    
    cmd = [
        ytdlp_path,
        '-f', select_format,
        '-o', outtmpl,
        '--no-warnings',
        '--restrict-filenames', # Ensures safe filenames for Windows
        '--print', 'after_move:filepath', # Prints the final path to stdout
        url
    ]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # The last non-empty line of stdout should be our path
        output_lines = [l.strip() for l in process.stdout.split('\n') if l.strip()]
        if output_lines:
            final_path = output_lines[-1]
            if os.path.exists(final_path):
                logger.info(f"Successfully downloaded: {final_path}")
                return os.path.abspath(final_path)
        
        # Fallback: check the output directory for the most recent file
        files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if not f.endswith('.part')]
        if files:
            return os.path.abspath(max(files, key=os.path.getmtime))
            
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed: {e.stderr}")
    except Exception as e:
        logger.exception(f"Unexpected error in downloader: {e}")
        
    return None
