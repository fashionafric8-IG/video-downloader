import os
import time
import threading
import logging
import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
# existing imports remain

from werkzeug.exceptions import HTTPException

# existing imports and logger setup remain unchanged
from downloader import get_video_info, download_video

# Setup logging
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8', errors='replace'),
        logging.StreamHandler(sys.stdout)
    ]
)
# Fixed the logging handler name error below in implementation

from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://toolsflash.org",
            "https://www.toolsflash.org"
        ]
    }
})


# Allow routes with or without trailing slashes to avoid HTML redirects
app.url_map.strict_slashes = False

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_task():
    """Background task to delete files older than 1 hour."""
    while True:
        try:
            now = time.time()
            for f in os.listdir(DOWNLOAD_DIR):
                path = os.path.join(DOWNLOAD_DIR, f)
                if os.path.isfile(path) and os.stat(path).st_mtime < now - 3600:
                    os.remove(path)
                    logging.info(f"Cleaned up old file: {f}")
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
        time.sleep(600) # Run every 10 minutes

# Start cleanup thread
threading.Thread(target=cleanup_task, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    info = get_video_info(url)
    if 'error' in info:
        return jsonify({'error': info['error']}), 500
    
    return jsonify(info)

# Global error handlers to always return JSON
@app.errorhandler(404)
def handle_404(e):
    response = jsonify({'error': 'Resource not found'})
    response.status_code = 404
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the exception
    logging.exception('Unhandled exception')
    response = jsonify({'error': str(e)})
    response.status_code = 500
    return response

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    try:
        path = download_video(url, format_id, DOWNLOAD_DIR)
        return jsonify({
            'filename': os.path.basename(path),
            'title': os.path.basename(path)
        })
    except Exception as e:
        # Log full traceback
        logging.exception('Download error')
        return jsonify({'error': str(e)}), 500

@app.route('/serve/<filename>')
def serve_file(filename):
    """Safely serves the file for download with forced attachment headers."""
    import mimetypes
    mimetype, _ = mimetypes.guess_type(filename)
    return send_from_directory(
        DOWNLOAD_DIR, 
        filename, 
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype or 'application/octet-stream'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
