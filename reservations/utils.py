import os
import uuid
import shutil  # To handle file moving
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from django.conf import settings

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def text_to_speech_file(text: str) -> str:
    # Convert text to speech
    response = client.text_to_speech.convert(
        voice_id="pNInz6obpgDQGcFmaJgB",  # Adam pre-made voice
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
        ),
    )

    # Save the speech file
    speech_file_name = f"{uuid.uuid4()}.mp3"
    speech_file_path = os.path.join(settings.MEDIA_ROOT, speech_file_name)
    with open(speech_file_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    print(f"{speech_file_path}: A new audio file was saved successfully!")

    return speech_file_path


def add_beep_to_speech(speech_file_path: str) -> str:
    # Load beep sound
    beep_sound = AudioSegment.from_mp3("mixkit-censorship-beep-1082.wav")

    # Load speech sound
    speech_sound = AudioSegment.from_mp3(speech_file_path)

    # Concatenate speech and beep (beep will be added at the end)
    combined = speech_sound + beep_sound

    # Save the combined file
    combined_file_path = f"combined_{uuid.uuid4()}.mp3"
    combined.export(combined_file_path, format="mp3")

    print(f"{combined_file_path}: Combined speech and beep file saved successfully!")

    return combined_file_path


def generate_restaurant_speech_file(restaurant):
    """
    Generate a text-to-speech file for the given restaurant and save it.
    """
    text = (
        f"Hello, I am speaking from {restaurant.restaurant_name}. "
        f"We are located at {restaurant.restaurant_address}. "
        f"I hope you're doing well. "
        f"We currently have {restaurant.available_tables} tables available for reservations, "
        f"with a seating capacity of {restaurant.seating_capacity} people. "
        f"Our opening hours are from {restaurant.opening_hours}, "
        f"and we close at {restaurant.closing_hours}. "
        f"We specialize in {restaurant.cuisines}. "
        f"Would you like to make a reservation? Please speak after the beep."
    )

    # Generate the TTS file (assuming text_to_speech_file and add_beep_to_speech are defined)
    file_path = text_to_speech_file(text)
    file_path_with_beep = add_beep_to_speech(file_path)

    # Rename the file according to the restaurant name
    new_file_name = f"{restaurant.restaurant_name.replace(' ', '_').replace('/', '_')}.mp3"
    new_file_path = os.path.join(settings.MEDIA_ROOT, new_file_name)

    # Move the combined file to the new path
    shutil.move(file_path_with_beep, new_file_path)

    return new_file_path

# `pip3 install assemblyai` (macOS)
# `pip install assemblyai` (Windows)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        speech_file = text_to_speech_file(text)
        add_beep_to_speech(speech_file)
    else:
        print("No text provided.")
