#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Audio solving module. """

import os
import random
import shutil
import tempfile

from asyncio import TimeoutError, CancelledError
from aiohttp.client_exceptions import ClientError

from nonocaptcha import util
from nonocaptcha.speech import Amazon, Azure, Sphinx, DeepSpeech, AzureSpeech
from nonocaptcha.base import Base
from nonocaptcha.exceptions import DownloadError, ReloadError, TryAgain


class SolveAudio(Base):
    def __init__(self, page, loop, proxy, proxy_auth, proc_id):
        self.page = page
        self.loop = loop
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.proc_id = proc_id

    async def solve_by_audio(self):
        """Go through procedures to solve audio"""
        await self.get_frames()
        for _ in range(10):
            try:
                answer = await self.loop.create_task(self.get_audio_response())
            except DownloadError:
                raise
            except ReloadError:
                raise
            else:
                if not answer:
                    continue
            await self.type_audio_response(answer)
            await self.click_verify()
            try:
                result = await self.check_detection(self.animation_timeout)
            except TryAgain:
                continue
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
            audio_data = await self.loop.create_task(
                util.get_page(
                    audio_url,
                    proxy=self.proxy,
                    proxy_auth=self.proxy_auth,
                    binary=True,
                    timeout=self.page_load_timeout))
        except ClientError as e:
            self.log(f"Error `{e}` occured during audio download, retrying")
        else:
            answer = None
            service = self.speech_service.lower()
            if service in [
                "azure",
                "pocketsphinx",
                "deepspeech",
                "azurespeech"
            ]:
                if service == "azurespeech":
                    speech = AzureSpeech()
                elif service == "azure":
                    speech = Azure()
                elif service == "pocketsphinx":
                    speech = Sphinx()
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
            if answer:
                self.log(f'Received answer "{answer}"')
                return answer

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
        await self.loop.create_task(
            response_input.type(text=answer, delay=length))

    async def click_verify(self):
        self.log("Clicking verify")
        verify_button = await self.image_frame.J("#recaptcha-verify-button"
                                                 )
        await self.click_button(verify_button)
