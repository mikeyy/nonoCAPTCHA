#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Audio solving module."""

import os
import random
import shutil
import tempfile

from asyncio import TimeoutError

from config import settings
from nonocaptcha import util
from nonocaptcha.speech import Amazon, Azure, Sphinx, DeepSpeech
from nonocaptcha.base import Base, Detected, Success, TryAgain


class ReloadError(Exception):
    pass


class DownloadError(Exception):
    pass


class SolveAudio(Base):
    def __init__(self, page, proxy, proc_id):
        self.page = page
        self.proxy = proxy
        self.proc_id = proc_id

    async def solve_by_audio(self):
        """Go through procedures to solve audio"""

        self.get_frames()

        for i in range(5):
            try:
                answer = await self.get_audio_response()
            except InvalidDownload:
                raise
            except ReloadError:
                raise
            else:
                if not answer:
                    continue

            await self.type_audio_response(answer)
            await self.click_verify()

            timeout = settings["wait_timeout"]["success_timeout"]
            try:
                await self.check_detection(self.image_frame, timeout)
            except TryAgain:
                continue
            except Detected:
                raise
            except Success:
                raise

    async def get_audio_response(self):
        """Download audio data then send to speech-to-text API for answer"""
        
        try:
            audio_url = await self.image_frame.evaluate(
                f'$(".rc-audiochallenge-tdownload-link").attr("href")'
            )
            if not isinstance(audio_url, str):
                raise DownloadError("Audio url is not valid, aborting")
        except asyncio.CancelledError:
            raise DownloadError("Audio url not found, aborting")

        self.log("Downloading audio file")
        timeout = settings["wait_timeout"]["load_timeout"]
        try:
            audio_data = await util.get_page(
                audio_url, self.proxy, binary=True, timeout=timeout
            )
        except TimeoutError:
            self.log("Download timed-out, trying again")
        else:
            answer = None
            service = settings["speech_api"]["service"].lower()
            if service in ["azure", "sphinx", "deepspeech"]:
                if service == "azure":
                    speech = Azure()
                elif service == "sphinx":
                    speech = Sphinx()
                else:
                    speech = DeepSpeech()
                tmpd = tempfile.mkdtemp()
                tmpf = os.path.join(tmpd, "audio.mp3")
                await util.save_file(tmpf, data=audio_data, binary=True)
                answer = await speech.get_text(tmpf)
                shutil.rmtree(tmpd)
            else:
                speech = Amazon()
                answer = await speech.get_text(audio_data)
            if answer:
                self.log(f'Received answer "{answer}"')
                return answer
        self.log("No answer, reloading")
        await self.click_reload_button()
        func = (
            f'"{audio_url}" !== '
            f'$(".rc-audiochallenge-tdownload-link").attr("href")'
        )
        timeout = settings["wait_timeout"]["reload_timeout"]
        try:
            await self.image_frame.waitForFunction(
                func, timeout=timeout * 1000
            )
        except TimeoutError:
            raise ReloadError("Download link never updated")
        else:
            return

    async def type_audio_response(self, answer):
        self.log("Typing audio response")
        response_input = await self.image_frame.J("#audio-response")
        length = random.uniform(70, 130)
        await response_input.type(text=answer, delay=length)

    async def click_verify(self):
        if settings["keyboard_traverse"]:
            response_input = await self.image_frame.J("#audio-response")
            self.log("Pressing Enter")
            await response_input.press("Enter")
        else:
            verify_button = await self.image_frame.J(
                "#recaptcha-verify-button"
            )

            self.log("Clicking verify")
            await self.click_button(verify_button)
