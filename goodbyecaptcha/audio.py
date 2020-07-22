#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Audio solving module. """
import asyncio
import os
import random
import shutil
import tempfile
from asyncio import TimeoutError, CancelledError

from aiohttp.client_exceptions import ClientError

from goodbyecaptcha import util
from goodbyecaptcha.base import Base
from goodbyecaptcha.exceptions import DownloadError, ReloadError, TryAgain, ButtonError, SafePassage, ResolveMoreLater
from goodbyecaptcha.speech import AzureSpeech, Amazon, Azure, DeepSpeech, Sphinx, Google, WitAI


class SolveAudio(Base):
    def __init__(self, page, image_frame, loop=None, proxy=None, proxy_auth=None, lang='en-US', options=None,
                 chromePath=None, **kwargs):
        self.page = page
        self.image_frame = image_frame
        self.service = self.speech_service.lower()

        super(SolveAudio, self).__init__(loop=loop, proxy=proxy, proxy_auth=proxy_auth, language=lang, options=options,
                                         chromePath=chromePath, **kwargs)

    async def solve_by_audio(self):
        """Go through procedures to solve audio"""
        self.log('Wait for Audio Buttom ...')
        await self.loop.create_task(self.wait_for_audio_button())
        self.log('Click random images ...')
        for _ in range(int(random.uniform(2, 5))):
            await asyncio.sleep(random.uniform(0.2, 0.5))  # Wait 2-5 ms
            await self.click_tile()  # Click random images
        await asyncio.sleep(random.uniform(1.5, 3.5))  # Wait 1-3 seg
        await self.click_verify()  # Click Verify button
        self.log('Clicking Audio Buttom ...')
        await asyncio.sleep(random.uniform(1, 3))  # Wait 1-3 sec
        result = await self.click_audio_button()  # Click audio button
        if isinstance(result, dict):
            if result["status"] == "detected":  # Verify if detected
                return result
        # Start process
        await self.get_frames()
        answer = None
        # Start url for ...
        start_url = self.page.url
        for _ in range(8):
            try:
                answer = await self.loop.create_task(self.get_audio_response())
                temp = self.service
                self.service = self.speech_secondary_service.lower()  # Secondary Recognition
                self.speech_secondary_service = temp
            except TryAgain:
                self.log('Try again Error!')
            except DownloadError:
                self.log('Download Error!')
            except ReloadError:
                self.log('Reload Error!')
            else:
                if not answer:
                    continue
                else:
                    if len(answer) < 4:
                        continue
            await self.type_audio_response(answer)
            await self.click_verify()
            await asyncio.sleep(2.0)  # Wait 2seg
            if start_url != self.page.url:
                return {'status': 'success'}
            try:
                result = await self.check_detection(self.animation_timeout)
            except TryAgain:
                continue
            except SafePassage:
                continue
            except Exception:
                raise ResolveMoreLater('You must solve more captchas.')
            else:
                return result
        else:
            return {"status": "retries_exceeded"}

    async def wait_for_audio_button(self):
        """Wait for audio button to appear."""
        try:
            await self.image_frame.waitForFunction(
                "jQuery('#recaptcha-audio-button').length",
                timeout=self.animation_timeout)
        except ButtonError:
            raise ButtonError("Audio button missing, aborting")
        except Exception as ex:
            self.log(ex)
            raise Exception(ex)

    async def click_tile(self):
        """Click random title for bypass detection"""
        self.log("Clicking random tile")
        tiles = await self.image_frame.JJ(".rc-imageselect-tile")
        await self.click_button(random.choice(tiles))

    async def click_audio_button(self):
        """Click audio button after it appears."""
        audio_button = await self.image_frame.J("#recaptcha-audio-button")
        await self.click_button(audio_button)
        try:
            result = await self.check_detection(self.animation_timeout)
        except SafePassage:
            pass
        else:
            return result

    async def get_audio_response(self):
        """Download audio data then send to speech-to-text API for answer"""
        try:
            audio_url = await self.image_frame.evaluate('jQuery("#audio-source").attr("src")')
            if not isinstance(audio_url, str):
                raise DownloadError(f"Audio url is not valid, expected `str` instead received {type(audio_url)}")
        except CancelledError:
            raise DownloadError("Audio url not found, aborting")

        self.log("Downloading audio file ...")
        try:
            if self.debug:
                self.log("audio file: {0}".format(str(audio_url)))
            # Get the challenge audio to send to Google
            audio_data = await self.loop.create_task(
                util.get_page(audio_url, proxy=self.proxy, proxy_auth=self.proxy_auth, binary=True,
                              timeout=self.page_load_timeout))
            self.log("Downloaded audio file!")
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
                return None  # Secondary Recognition

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
        """Enter answer text on input"""
        self.log("Waiting audio response")
        response_input = None
        for i in range(4):
            response_input = await self.image_frame.J("#audio-response")
            if response_input:
                break
            await asyncio.sleep(2.0)  # Wait 2seg
        self.log("Typing audio response")
        length = random.uniform(70, 130)
        try:
            await self.loop.create_task(response_input.type(text=answer, delay=length))
        except Exception:
            raise TryAgain('Try again later')

    async def get_answer(self, audio_data, service):
        """Get answer text from API selected (Primary and Secondary)"""
        if service in ["azure", "pocketsphinx", "deepspeech", "azurespeech", "google", "wit.ai"]:
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
            elif service == "amazon":
                self.log('Using Amazon Recognition')
                speech = Amazon()
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
            speech = Google()  # Set default Speech (Google is Free)
            answer = await self.loop.create_task(speech.get_text(audio_data))
        return answer

    async def add_error_humans_to_text(self, answer):
        """Create Imperfections in text_output (The Humans is not perfect)"""
        answer = answer[:-1] if 6 < len(answer) < 20 else answer
        answer = answer.split(' ')[0] + ' ' + answer.split(' ')[1] \
            if 30 > len(answer) > 20 and len(answer.split(' ')) > 2 else answer
        answer = answer if answer[-1:] != ' ' else answer[:-1]
        return answer
