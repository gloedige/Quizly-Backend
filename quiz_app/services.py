"""YouTube processing and Gemini quiz-generation services."""
# Standard library
import json
import os
import re
import tempfile
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlparse

import logging

logger = logging.getLogger(__name__)

QUIZ_PROMPT = """Based on the following transcript, generate a quiz in valid JSON format.
The quiz must follow this exact structure:
{
  \"title\": \"A concise topic-based quiz title.\",
  \"description\": \"A summary of at most 150 characters.\",
  \"questions\": [
    {
      \"question_title\": \"Question text.\",
      \"question_options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],
      \"answer\": \"One option exactly as written above\"
    }
  ]
}
Requirements: exactly 10 questions, exactly 4 distinct options per question, the answer must match one option, valid JSON only, no commentary.
Transcript:
{transcript}
"""
YOUTUBE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')

MAX_VIDEO_LENGTH = '600'  # in seconds, e.g., 600 seconds = 10 minutes
MAX_VIDEO_SIZE = '30M'

AI_MODEL_VERSION = 'gemini-3.8-flash'

_WHISPER_MODELS = {}
_MODEL_LOAD_LOCK = Lock()
_TRANSCRIPTION_LOCK = Lock()

def canonicalize_youtube_url(value):
    """Validate common YouTube URL forms and return the canonical watch URL."""
    parsed = urlparse(value.strip())
    host = (parsed.hostname or '').lower()
    if parsed.scheme not in {'http', 'https'}:
        raise ValueError('YouTube URL must use HTTP or HTTPS.')
    video_id = _extract_video_id(parsed, host)
    if not YOUTUBE_ID_PATTERN.fullmatch(video_id or ''):
        raise ValueError('Invalid YouTube video URL.')
    return f'https://www.youtube.com/watch?v={video_id}'


def _extract_video_id(parsed, host):
    """Extract a video ID only from supported YouTube host and path forms."""
    if host == 'youtu.be':
        return parsed.path.strip('/').split('/')[0]
    if host not in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'}:
        return None
    if parsed.path == '/watch':
        return parse_qs(parsed.query).get('v', [None])[0]
    match = re.match(r'^/(?:shorts|embed|live)/([^/]+)', parsed.path)
    return match.group(1) if match else None


def generate_quiz_content(youtube_url):
    """Download, transcribe and generate quiz data using temporary audio storage."""
    with tempfile.TemporaryDirectory(prefix='quizly-') as temp_directory:
        audio_path = _download_audio(youtube_url, temp_directory)
        transcript = _transcribe_audio(audio_path)
        return _generate_with_gemini(transcript)


def _download_audio(youtube_url, temp_directory):
    """Download the best available YouTube audio track to a temporary directory."""
    import yt_dlp

    template = str(Path(temp_directory) / 'source.%(ext)s')
    options = {
                'format': f'bestaudio[filesize<{MAX_VIDEO_SIZE}]/bestaudio[filesize_approx<{MAX_VIDEO_SIZE}]',
                'outtmpl': template,
                'quiet': True,
                'noplaylist': True,
                'match_filter': yt_dlp.utils.match_filter_func(f'duration <= {MAX_VIDEO_LENGTH}'),
                'logger': logger,
            }
    try:
        logger.info(f"Starting download for: {youtube_url}")
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([youtube_url])
        audio_path = str(_find_downloaded_audio(temp_directory))
        logger.info('YouTube audio download completed: %s', audio_path)
    except Exception as e:
        raise RuntimeError('YouTube audio download failed.') from e
    return audio_path

def _find_downloaded_audio(temp_directory):
    """Return the downloaded audio file or raise when no file was produced."""
    files = [path for path in Path(temp_directory).iterdir() if path.is_file() and not path.name.endswith('.part')]
    if not files:
        raise RuntimeError('YouTube audio download produced no file.')
    return files[0]

def _get_whisper_model(model_name):
    """Get a Whisper model instance, loading it if necessary."""
    import whisper
    with _MODEL_LOAD_LOCK:
        if model_name not in _WHISPER_MODELS:
            _WHISPER_MODELS[model_name] = whisper.load_model(model_name)

        return _WHISPER_MODELS[model_name]

def _transcribe_audio(audio_path):
    """Transcribe a local audio file with Whisper."""
    model_name = os.getenv('WHISPER_MODEL', 'base')
    model = _get_whisper_model(model_name)

    with _TRANSCRIPTION_LOCK:
        return model.transcribe(audio_path)['text']

def _generate_with_gemini(transcript):
    """Request quiz JSON from Gemini Flash and parse its response."""
    from google import genai
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not configured.')
    client = genai.Client(api_key=api_key)
    result = client.models.generate_content(
        model=os.getenv('GEMINI_MODEL', AI_MODEL_VERSION),
        contents=QUIZ_PROMPT.replace('{transcript}', transcript),
    )
    return _parse_gemini_json(result.text or '')


def _parse_gemini_json(response_text):
    """Remove optional Markdown fences and parse Gemini's JSON response."""
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_text.strip(), flags=re.IGNORECASE)
    return json.loads(cleaned)
