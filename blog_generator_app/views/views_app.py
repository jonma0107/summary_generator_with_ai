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
from ..models import BlogPost
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
# @csrf_protect
# @never_cache
# @user_passes_test(lambda user: user.groups.filter(name="App"), login_url='/error_page/')
def index(request):
  username = request.user
  return render(request, 'index.html', {'username': username})


def error_page(request):
  return render(request, 'error_page.html')


@csrf_exempt
def generate_blog(request):
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


        # use OpenAI to generate the blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': " Failed to generate blog article"}, status=500)

        # save blog article to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()

        # return blog article as a response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    ydl_opts = {}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)  # Solo extrae información sin descargar
        title = info.get('title', None)
    return title

def download_audio(link):
    ydl_opts = {
        'format': 'bestaudio/best',  # Descargar solo el mejor audio disponible
        'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s'),  # Ruta de salida personalizada
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extrae solo el audio
            'preferredcodec': 'mp3',  # Convierte a MP3
            'preferredquality': '192',  # Calidad del audio
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=True)  # Extraer y descargar
        file_path = ydl.prepare_filename(info)  # Obtiene el nombre del archivo descargado
        # Cambia la extensión si el post-procesador la modifica
        base, ext = os.path.splitext(file_path)
        new_file = f"{base}.mp3"
    
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = AAI_API_KEY

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text

# Configuración del cliente de DeepSeek
client = openai.OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")

def generate_blog_from_transcription(transcription):
    messages = [
        {"role": "system", "content": "You are a professional blog writer. Write clear and attractive articles."},
        {"role": "user", "content": f"Based on the following transcript of a YouTube video, write a complete blog article. The article should be informative and should not sound like a straight transcript, but rather a well-structured and engaging piece of text.\n\nTranscripción:\n{transcription}"}
    ]

    
    try:
        # Realizar la solicitud al modelo de DeepSeek
        response = client.chat.completions.create(
            model="deepseek-r1:latest",  # Asegúrate de que coincida con el nombre del modelo
            messages=messages,
            stream=False
        )
        print(response)  # Depuración: Imprime la respuesta completa

        # Accede al contenido generado usando la notación de puntos
        generated_content = response.choices[0].message.content.strip()
        return generated_content
    except Exception as e:
        print(f"Error al generar el blog: {e}")
        return None
