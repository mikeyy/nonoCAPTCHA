#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Audio solving module. """
import os
import random
import shutil
import tempfile
from asyncio import TimeoutError, CancelledError

from aiohttp.client_exceptions import ClientError

from goodbyecaptcha import util
from goodbyecaptcha.base import Base
from goodbyecaptcha.exceptions import DownloadError, ReloadError, TryAgain
from goodbyecaptcha.speech import AzureSpeech, Amazon, Azure, DeepSpeech, Sphinx, Google, WitAI


class SolveAudio(Base):
    def __init__(self, page, loop, proxy, proxy_auth, proc_id):
        self.page = page
        self.loop = loop
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.proc_id = proc_id
        self.service = self.speech_service.lower()
        self.method = 'audio'

    async def solve_by_audio(self):
        """Go through procedures to solve audio"""
        await self.get_frames()
        answer = None
        for _ in range(2):
            try:
                answer = await self.loop.create_task(self.get_audio_response())
                # Secondary Recognition
                self.service = self.speech_secondary_service.lower()
            except DownloadError:
                self.log('Download Error!')
                # raise
            except ReloadError:
                self.log('Reload Error!')
                # raise
            else:
                if not answer:
                    continue
                else:
                    if len(answer) < 4:
                        continue
            await self.type_audio_response(answer)
            await self.click_verify()
            try:
                result = await self.check_detection(self.animation_timeout)
            except TryAgain:
                continue
            except Exception:
                raise Exception('You must solve more captchas.')
            else:
                return result
        else:
            return {"status": "retries_exceeded"}

    async def get_audio_response(self):
        """Download audio data then send to speech-to-text API for answer"""
        try:
            audio_url = await self.image_frame.evaluate(
                'jQuery("#audio-source").attr("src")')
            if not isinstance(audio_url, str):
                raise DownloadError(f"Audio url is not valid, expected `str`"
                                    "instead received {type(audio_url)}")
        except CancelledError:
            raise DownloadError("Audio url not found, aborting")

        self.log("Downloading audio file")
        try:
            self.log("audio file: {0}".format(str(audio_url)))
            # Get the challenge audio to send to Google
            audio_data = await self.loop.create_task(
                util.get_page(
                    audio_url,
                    proxy=self.proxy,
                    proxy_auth=self.proxy_auth,
                    binary=True,
                    timeout=self.page_load_timeout))
            self.log("Downloaded audio file")
        except ClientError as e:
            self.log(f"Error `{e}` occured during audio download, retrying")
        else:
            answer = await self.get_answer(audio_data, self.service)
            if answer is not None:
                self.log(f'Received answer "{answer}"')
                answer = await self.add_error_humans_to_text(answer)
                self.log(f'Received human answer "{answer}"')
                return answer
            elif self.service is self.speech_service.lower():
                # Secondary Recognition
                return None

            self.log("No answer, reloading")
            await self.click_reload_button()
            func = (
                f'"{audio_url}" !== '
                f'jQuery(".rc-audiochallenge-tdownload-link").attr("href")')
            try:
                await self.image_frame.waitForFunction(
                    func, timeout=self.animation_timeout)
            except TimeoutError:
                raise ReloadError("Download link never updated")

    async def type_audio_response(self, answer):
        self.log("Typing audio response")
        response_input = await self.image_frame.J("#audio-response")
        length = random.uniform(70, 130)
        try:
            await self.loop.create_task(
                response_input.type(text=answer, delay=length))
        except Exception:
            raise Exception('Try again later')

    async def click_verify(self):
        self.log("Clicking verify")
        verify_button = await self.image_frame.J("#recaptcha-verify-button")
        await self.click_button(verify_button)

    async def get_answer(self, audio_data, service):
        answer = None
        if service in [
            "azure",
            "pocketsphinx",
            "deepspeech",
            "azurespeech",
            "google",
            "wit.ai"
        ]:
            self.log('Initialize a new recognizer')
            if service == "azurespeech":
                self.log('Using Azure Speech Recognition')
                speech = AzureSpeech()
            elif service == "azure":
                self.log('Using Azure Recognition')
                speech = Azure()
            elif service == "pocketsphinx":
                self.log('Using Sphinx Recognition')
                speech = Sphinx()
            elif service == "google":
                self.log('Using Google Speech Recognition')
                speech = Google()
            elif service == "wit.ai":
                self.log('Using Wit.AI Recognition')
                speech = WitAI()
            else:
                speech = DeepSpeech()
            tmpd = tempfile.mkdtemp()
            tmpf = os.path.join(tmpd, "audio.mp3")
            await util.save_file(tmpf, data=audio_data, binary=True)
            answer = await self.loop.create_task(speech.get_text(tmpf))
            shutil.rmtree(tmpd)
        else:
            speech = Amazon()
            answer = await self.loop.create_task(
                speech.get_text(audio_data))
        return answer

    async def add_error_humans_to_text(self, answer):
        # Create Imperfections in text_output (The Humans is inperfect)
        answer = answer[:-1] if 6 < len(answer) < 20 else answer
        answer = answer.split(' ')[0] + ' ' + answer.split(' ')[1] \
            if 30 > len(answer) > 20 and len(answer.split(' ')) > 2 else answer
        answer = answer if answer[-1:] != ' ' else answer[:-1]
        return answer
