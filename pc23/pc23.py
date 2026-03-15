import argparse
from pathlib import Path

import speech_recognition as sr


def transcribe_from_file(recognizer: sr.Recognizer, audio_path: Path) -> str:
    """Transcribe speech from an audio file (.wav, .aiff, .flac)."""
    with sr.AudioFile(str(audio_path)) as source:
        audio = recognizer.record(source)

    return recognizer.recognize_google(audio, language="en-US")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PC.23 - English speech recognition from audio files for NLP pipeline inputs."
    )
    parser.add_argument(
        "--audio",
        type=Path,
        required=True,
        help="Path to the audio file to transcribe.",
    )

    args = parser.parse_args()
    recognizer = sr.Recognizer()

    try:
        if not args.audio.exists():
            raise FileNotFoundError(f"Audio file not found: {args.audio}")
        text = transcribe_from_file(recognizer, args.audio)

        print("\n--- TRANSCRIPTION (en-US) ---")
        print(text)

    except sr.UnknownValueError:
        print("Could not understand the audio (speech not recognized).")
    except sr.RequestError as exc:
        print(f"Recognition service unavailable/request failed: {exc}")
    except Exception as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
