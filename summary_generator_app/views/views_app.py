from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json

from yt_dlp import YoutubeDL
import os
import assemblyai as aai
from ..models import summaryPost
import environ
import openai
from openai import OpenAI

# Load environment variables from .env
env = environ.Env()
environ.Env.read_env()

# Access the API key from environment variables
AAI_API_KEY = env('AAI_API_KEY')

# Access the API key from environment variables
OPENAI_API_KEY = env('OPENAI_API_KEY')

@login_required
@csrf_protect
@never_cache
# @user_passes_test(lambda user: user.groups.filter(name="App"), login_url='/error_page/')
def index(request):
  username = request.user
  return render(request, 'index.html', {'username': username})

def error_page(request):
  return render(request, 'error_page.html')

def delete_audio_file(filepath):
    """ Delete the audio file if it exists. """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"File deleted: {filepath}")
        else:
            print(f"File not found: {filepath}")
    except Exception as e:
        print(f"Error when deleting file: {e}")

def download_video_and_audio(link, title):
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
    video_path = settings.MEDIA_ROOT / f"{safe_title}_video"
    audio_path = settings.MEDIA_ROOT / f"{safe_title}_audio"

    # Descargar video .mp4
    video_opts = {
        'format': 'mp4',
        'outtmpl': str(video_path) + '.mp4',
    }
    with YoutubeDL(video_opts) as ydl:
        ydl.download([link])
    video_file = str(video_path) + '.mp4'

    # Descargar audio .mp3
    audio_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(audio_path),  # sin extensión, yt-dlp la añade
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with YoutubeDL(audio_opts) as ydl:
        ydl.download([link])
    audio_file = str(audio_path) + '.mp3'

    return video_file, audio_file

def get_transcription(audio_file, title):
    aai.settings.api_key = AAI_API_KEY
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    if transcript and hasattr(transcript, 'text') and transcript.text:
        original_text = transcript.text
        # Guardar la transcripción original en un archivo .txt
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        transcript_file = settings.MEDIA_ROOT / f"{safe_title}.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(original_text)

        # (Opcional) Si quieres seguir devolviendo la traducción, puedes traducir aquí:
        messages = [
            {"role": "system", "content": "You are a concise summary writer."},
            {"role": "user", "content": f"Translate and summarize the following text in Spanish in a natural way:\n\n{original_text}"}
        ]
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                stream=False
            )
            translated_text = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error al traducir la transcripción: {e}")
            return None

        # Devuelve la traducción (o el original si prefieres)
        return translated_text
    else:
        return None

@csrf_exempt
def generate_summary(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        title = yt_title(yt_link)
        video_file, audio_file = download_video_and_audio(yt_link, title)
        transcription = get_transcription(audio_file, title)

        if not transcription:
            return JsonResponse({'error': " Failed to get transcript"}, status=500)

        # Aquí puedes generar el resumen si lo deseas, usando la transcripción traducida
        # summary_content = generate_summary_from_transcription(transcription)
        # ...

        return JsonResponse({'content': transcription})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    ydl_opts = {}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)  # Only extracts information without downloading
        title = info.get('title', None)
    return title

def download_audio(link):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=True)
        file_path = ydl.prepare_filename(info)
        base, ext = os.path.splitext(file_path)
        new_file = f"{base}.mp3"
    
    return new_file

# DeepSeek client configuration
# client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.openai.com/v1")

# OpenAI client configuration
client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"), 
    base_url="https://api.openai.com/v1", 
)

