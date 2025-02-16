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
# from pytube import YouTube
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

# Create your views here.
@login_required
@csrf_protect
@never_cache
# @user_passes_test(lambda user: user.groups.filter(name="App"), login_url='/error_page/')
def index(request):
  username = request.user
  return render(request, 'index.html', {'username': username})


def error_page(request):
  return render(request, 'error_page.html')


@csrf_exempt
def generate_summary(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        # get yt title
        title = yt_title(yt_link)

        # get transcript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': " Failed to get transcript"}, status=500)

        # use OpenAI to generate the summary
        summary_content = generate_summary_from_transcription(transcription)
        if not summary_content:
            return JsonResponse({'error': " Failed to generate summary article"}, status=500)

        # save summary article to database
        new_summary_article = summaryPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=summary_content,
        )
        new_summary_article.save()

        # return summary article as a response
        return JsonResponse({'content': summary_content})
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
        'format': 'bestaudio/best',  # Download only the best available audio
        'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s'),  # Customized exit route
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extract audio only
            'preferredcodec': 'mp3',  # Convert to MP3
            'preferredquality': '192',  # Audio quality
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=True)  # Extract and download
        file_path = ydl.prepare_filename(info)  # Gets the name of the downloaded file
        # Change the extension
        base, ext = os.path.splitext(file_path)
        new_file = f"{base}.mp3"
    
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = AAI_API_KEY

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text

# DeepSeek client configuration
# client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.openai.com/v1")

# OpenAI client configuration
client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"), 
    base_url="https://api.openai.com/v1", 
)

def generate_summary_from_transcription(transcription):
    messages = [
        {"role": "system", "content": "You are a concise summary writer."},
        {"role": "user", "content": f"From the content of the generated transcript, make a summary in Spanish.\n\nTranscripción:\n{transcription}"}
    ]

    
    try:
        # Make a request to the model
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=messages,
            max_tokens=256,
            temperature=0.7,
            stream=False
        )        

        # Access content generated using dot notation
        generated_content = response.choices[0].message.content.strip()
        return generated_content
    except Exception as e:
        print(f"Error al generar el summary: {e}")
        return None
