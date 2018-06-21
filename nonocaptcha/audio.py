#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Audio solving module."""

import random
import tempfile

from nonocaptcha import util
from nonocaptcha.speech import get_text
from nonocaptcha.helper import wait_between
from config import settings



class SolveAudio(object):
    def __init__(self, frames, check_detection, proxy, log):
        self.checkbox_frame, self.image_frame = frames
        self.check_detection = check_detection
        self.proxy = proxy
        self.log = log
        self.detected = False
    
    async def solve_by_audio(self):
        """Go through procedures to solve audio"""
        
        answer = await self.get_audio_response()
        if not answer:
            return
        await self.type_audio_response(answer)
        await self.click_verify()
        
        timeout = settings["wait_timeout"]["success_timeout"]
        try:
            await self.check_detection(self.checkbox_frame, timeout)
        finally:
            if self.detected:
                raise
            return 1

    async def get_audio_response(self):
        """Download audio data then send to speech-to-text API for answer"""

        download_link_element = (
            'document.getElementsByClassName("rc-audiochallenge-tdownload-link'
            '")[0]'
        )

        audio_url = await self.image_frame.evaluate(
            f'{download_link_element}.getAttribute("href")'
        )

        self.log("Downloading audio file")
        audio_data = await util.get_page(audio_url, self.proxy, binary=True)

        answer = None
        with tempfile.NamedTemporaryFile(suffix="mp3") as tmpfile:
            await util.save_file(tmpfile.name, audio_data, binary=True)
            answer = await get_text(tmpfile.name)

        if answer:
            self.log(f'Received answer "{answer}"')
            return answer

        self.log("No answer, reloading")
        await self.click_reload_button()

        func = (
            f'"{audio_url}" !== '
            f'{download_link_element}.getAttribute("href")'
        )
        timeout = settings["wait_timeout"]["reload_timeout"]
        try:
            await self.check_detection(
                self.image_frame, timeout, wants_true=func
            )
        except:
            raise
        else:
            if self.detected:
                raise

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

    async def click_reload_button(self):
        reload_button = await self.image_frame.J("#recaptcha-reload-button")
        await self.click_button(reload_button)

    async def click_button(self, button):
        click_delay = random.uniform(70, 130)
        await wait_between(2000, 4000)
        await button.click(delay=click_delay / 1000)