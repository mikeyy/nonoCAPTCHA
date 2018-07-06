#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Audio solving module."""

import os
import random
import shutil
import tempfile

from asyncio import TimeoutError, CancelledError

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
        
        # Get checkbox and image frames
        self.get_frames()
        
        # Try five times to solve the audio before manual failing
        for i in range(5):
            try:
                # Get the audio response
                answer = await self.get_audio_response()
            except DownloadError:
                # There was an error downloading the audio
                raise
            except ReloadError:
                # A problem reloading the audio after incorrect answer occured
                raise
            else:
                # Start from the top again if no answer resulted
                if not answer:
                    continue
            
            # Type the response we received
            await self.type_audio_response(answer)
            # Click verify
            await self.click_verify()

            try:
                # Check if we were detected
                await self.check_detection(
                    self.image_frame, self.animation_timeout
                )
            except TryAgain:
                # Incorrect answer, start from the top
                continue
            except Detected:
                # We were detected
                raise
            except Success:
                # Audio response successful
                raise

    async def get_audio_response(self):
        """Download audio data then send to speech-to-text API for answer"""
        
        try:
            # Get the audio url with jQuery selector
            audio_url = await self.image_frame.evaluate(
                f'$(".rc-audiochallenge-tdownload-link").attr("href")'
            )
            if not isinstance(audio_url, str):
                # Audio url isn't a string, abort
                raise DownloadError("Audio url is not valid, aborting")
        except CancelledError:
            # Odd, no URL is here, abort
            raise DownloadError("Audio url not found, aborting")

        self.log("Downloading audio file")
        try:
            audio_data = await util.get_page(
                audio_url,
                self.proxy,
                binary=True,
                timeout=self.page_load_timeout
            )
        except TimeoutError:
            self.log("Download timed-out, trying again")
        else:
            answer = None
            service = self.speech_service.lower()
            # Which service was supplied in the configuration?
            if service in ["azure", "pocketsphinx", "deepspeech"]:
                if service == "azure":
                    speech = Azure()
                elif service == "pocketsphinx":
                    speech = Sphinx()
                else:
                    speech = DeepSpeech()
                # Make a temporary directory to store the audio file, mp3->wav
                tmpd = tempfile.mkdtemp()
                tmpf = os.path.join(tmpd, "audio.mp3")
                await util.save_file(tmpf, data=audio_data, binary=True)
                # Get the text from the earlier supplied service
                answer = await speech.get_text(tmpf)
                # Remove created directory
                shutil.rmtree(tmpd)
            else:
                # Use Amazon if no other services were supplied
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
        try:
            # Wait for the audio url to actually change before continuing
            await self.image_frame.waitForFunction(
                func, timeout=self.animation_timeout
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
        if self.keyboard_traverse:
            response_input = await self.image_frame.J("#audio-response")
            self.log("Pressing Enter")
            await response_input.press("Enter")
        else:
            verify_button = await self.image_frame.J(
                "#recaptcha-verify-button"
            )

            self.log("Clicking verify")
            await self.click_button(verify_button)
