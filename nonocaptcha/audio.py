#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Audio solving module."""

import random
import tempfile

from config import settings
from nonocaptcha import util
from nonocaptcha.speech import get_text
from nonocaptcha.base import Base


class SolveAudio(Base):
    def __init__(self, page, proxy, proc_id):
        self.page = page
        self.proxy = proxy
        self.proc_id = proc_id

    async def solve_by_audio(self):
        """Go through procedures to solve audio"""

        self.get_frames()
        
        for i in range(5):
            answer = await self.get_audio_response()
            if not answer:
                continue

            await self.type_audio_response(answer)
            await self.click_verify()
            
            timeout = settings["wait_timeout"]["success_timeout"]
            try:
                await self.check_detection(self.image_frame, timeout)
            except:
                pass
            finally:
                if self.detected:
                    raise
                break

    async def get_audio_response(self):
        """Download audio data then send to speech-to-text API for answer"""

        audio_url = await self.image_frame.evaluate(
            f'$(".rc-audiochallenge-tdownload-link").attr("href")'
        )

        self.log("Downloading audio file")
        audio_data = await util.get_page(
            audio_url, self.proxy, binary=True, timeout=30
        )

        if audio_data is None:
            self.log("Download timed-out")
        else:
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
            f'$(".rc-audiochallenge-tdownload-link").attr("href")'
        )
        timeout = settings["wait_timeout"]["reload_timeout"]
        try:
            await self.image_frame.waitForFunction(
                func, timeout=timeout * 1000
            )
        except:
            raise
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
