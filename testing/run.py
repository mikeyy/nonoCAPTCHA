import asyncio
import os

from speech import Amazon, Azure, Sphinx, DeepSpeech, play_audio, settings


speech_service = settings["service"]
audio_dir = "recap-audio"
post_play_audio = True


async def solve(service, audio_file):
    answer = None
    service = service.lower()
    if service in ["azure", "pocketsphinx", "deepspeech"]:
        if service == "azure":
            speech = Azure()
        elif service == "pocketsphinx":
            speech = Sphinx()
        else:
            speech = DeepSpeech()
        answer = await speech.get_text(audio_file)
    else:
        speech = Amazon()
        answer = await speech.get_text(audio_file)
    if answer:
        print(f"audio file: {audio_file}")
        print(f"{service}'s best guess: {answer}")
    else:
        print(f"{service}'s failed to decipher: {audio_file}")
    if post_play_audio:
        await play_audio(audio_file)
    print("--------"*15)


async def main():
    for dirs, subdirs, files in os.walk(audio_dir):
        for fname in files:
            ext = os.path.splitext(fname)[-1].lower()
            if ext == ".mp3":
                fpath = os.path.join(audio_dir, fname)
                await solve(speech_service, fpath)

asyncio.get_event_loop().run_until_complete(main())
