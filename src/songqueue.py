from random import shuffle
import asyncio

import discord

from song import Song


class InnerQueue(asyncio.Queue):
    def __getitem__(self, item):
        return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class SongQueue():
    def __init__(self):
        self.queue   = InnerQueue()
        self.next    = asyncio.Event()
        self.current = None  # currently playing song
        self.voice   = None  # voice client
        self.text    = None  # text chat where the songs are announced, etc.
        self.player  = asyncio.get_running_loop().create_task(self.player_task())

    async def player_task(self):
        while True:
            self.next.clear()
            self.current = await self.queue.get()

            # FFMPEG options to prevent stream closing on lost connections
            before_options  = "-reconnect 1 -reconnect_streamed 1"
            before_options += " -reconnect_delay_max 5"

            source = discord.FFmpegPCMAudio(self.current.stream,
                                            before_options=before_options)
            self.voice.play(source, after=self.next_song)

            msg = discord.Embed(title="Now playing",
                    description=f"[{self.current.title}]({self.current.url})")
            msg.add_field(name="Duration",
                    value=self.current.duration_formatted)
            msg.add_field(name="Uploader",
                    value=f"[{self.current.uploader}]({self.current.uploader_url})")
            msg.set_thumbnail(url=self.current.thumbnail)

            await self.text.send(embed=msg)
            await self.next.wait()


    def next_song(self, error=None):
        if error:
            raise VoiceError(str(error))
        self.next.set()