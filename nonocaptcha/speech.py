#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Bing(Azure) text-to-speech functions"""

import asyncio
import json
import re
import struct
import time
import websockets
from io import StringIO, BytesIO
from datetime import datetime
from uuid import uuid4
from pydub import AudioSegment
from config import settings
from functools import partial, wraps


SUB_KEY = settings["api_subkey"]


def threaded(func):
    @wraps(func)
    async def wrap(*args, **kwargs):
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(
            None, partial(func, *args, **kwargs)
        )

    return wrap

@threaded
def bytes_from_file(filename, chunksize=8192):
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(chunksize)
            if chunk:
                yield chunk
            else:
                break

@threaded
def mp3_to_wav(mp3_filename):
    wav_filename = mp3_filename.replace(".mp3", ".wav")
    sound = AudioSegment.from_mp3(mp3_filename)
    wav = sound.export(wav_filename, format="wav")
    return wav_filename

@threaded
def extract_json_body(response):
    pattern = "^\r\n"  # header separator is an empty line
    m = re.search(pattern, response, re.M)
    return json.loads(
        response[m.end() :]
    )  # assuming that content type is json

@threaded
def build_message(req_id, payload):
    message = b""
    timestamp = datetime.utcnow().isoformat()
    header = (
        f"X-RequestId: {req_id}\r\nX-Timestamp: {timestamp}Z\r\n"
        f"Path: audio\r\nContent-Type: audio/x-wav\r\n\r\n"
    )
    message += struct.pack(">H", len(header))
    message += header.encode()
    message += payload
    return message


async def send_file(websocket, filename):
    req_id = uuid4().hex
    for payload in await bytes_from_file(filename):
        message = await build_message(req_id, payload)
        await websocket.send(message)


async def get_text(mp3_filename):
    wav_filename = await mp3_to_wav(mp3_filename)
    conn_id = uuid4().hex
    url = (
        f"wss://speech.platform.bing.com/speech/recognition/dictation/cogn"
        f"itiveservices/v1?language=en-US&Ocp-Apim-Subscription-Key={SUB_KEY}&"
        f"X-ConnectionId={conn_id}&format=detailed"
    )

    async with websockets.connect(url) as websocket:
        await send_file(websocket, wav_filename)
        timeout = time.time() + 15
        while time.time() < timeout:
            response = await websocket.recv()
            content = await extract_json_body(response)
            if (
                "RecognitionStatus" in content
                and content["RecognitionStatus"] == "Success"
            ):
                answer = content["NBest"][0]["Display"]
                return answer[:-1].lower()
            if (
                "RecognitionStatus" in content
                and content["RecognitionStatus"] == "EndOfDictation"
            ):
                return
