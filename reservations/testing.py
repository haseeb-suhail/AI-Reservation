from django.test import TestCase

# Create your tests here.
import assemblyai as aai

aai.settings.api_key = "6ccf1f75fb9e45a6b914a2a43d03cf2d"
transcriber = aai.Transcriber()

transcript = transcriber.transcribe("media/Tasty_Bites.mp3")
# transcript = transcriber.transcribe("./my-local-audio-file.wav")

print(transcript.text)