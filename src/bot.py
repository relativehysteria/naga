import discord
from discord.ext import commands
from log import globalLog as gLog
from songqueue import SongQueue
from song import Song
from settings import REACTION_OK, REACTION_ERR

class Naga(commands.Cog):
    def __init__(self, bot: commands.Bot):
        # The bot this cog belongs to
        self.bot = bot

        # Queues of all the servers this bot is in.
        # { guild.id: SongQueue }
        self.queues = {}


    @staticmethod
    def _valid_index(ctx: commands.Context, idx: int) -> bool:
        """Checks whether an index `idx` can be used to index into a queue."""
        idx >= 0 or idx < len(ctx.queue)

    async def cog_before_invoke(self, ctx: commands.Context):
        """Sets `ctx.queue` to the server's queue if it exists, otherwise it
        creates a new one
        """
        ctx.queue = self.queues.get(ctx.guild.id)


    @commands.command(name="join")
    async def _join_vc(self, ctx: commands.Context, *,
                       destination_vc: discord.VoiceChannel = None):
        """Joins a voice channel.

        If `destination_vc` is specified, joins the specified voice channel.
        If it isn't specified, joins the voice channel the author is in.
        """
        if not ctx.author.voice and not destination_vc:
            await ctx.send("No voice channel.")
            return

        # `ctx.queue` is initialized by `cog_before_invoke`.
        # If there's no queue (None), it means that this bot is not in
        # a voice channel
        if not ctx.queue:
            ctx.queue = SongQueue()
            self.queues[ctx.guild.id] = ctx.queue

        # Join the destination voice channel
        destination_vc = destination_vc or ctx.author.voice.channel
        if ctx.queue.voice:
            await ctx.queue.voice.disconnect()
        ctx.queue.voice = await destination_vc.connect()
        await ctx.message.add_reaction(REACTION_OK)


    @commands.command(name="leave")
    async def _leave_vc(self, ctx: commands.Context):
        """Leaves a voice channel"""
        if ctx.queue is not None and ctx.queue.voice:
            await ctx.queue.voice.disconnect()
            ctx.queue.destruct()
            del self.queues[ctx.guild.id]
            await ctx.message.add_reaction(REACTION_OK)


    @commands.command(name="play")
    async def _play(self, ctx: commands.Context, *args):
        """Plays something in a voicechat"""
        query = ' '.join(args)
        if query == "" or ctx.queue is None:
            gLog.debug(f"Query: {query}")
            gLog.debug(f"Queue is not None: {ctx.queue is not None}")
            await ctx.message.add_reaction(REACTION_ERR)
            return

        gLog.info(f"Query: {query}")

        # Get a list of urls to a playlist (if a playlist was given, otherwise
        # just get [single_url]).
        urls = Song.get_urls_from_query(query)
        if len(urls) == 0:
            await ctx.message.add_reaction(REACTION_ERR)
            return

        to_update_msg = await ctx.send(f"Queuing up...")
        counter = 0
        for url in urls:
            # Stop downloading when the bot disconnects
            if ctx.queue._stop_thread:
                break

            # Get the song and make sure that it is valid
            song = Song(url)
            if song.stream is None:
                continue

            # Create an embed and send it to the server if the song has a title,
            # otherwise don't even bother.
            # Don't create embeds for playlists.
            if len(urls) == 1 and song.title:
                msg = discord.Embed(title="Enqueued", description=
                                    f"[{song.title}]({song.url})")
                if song.duration:
                    msg.add_field(name="Duration", value=
                                  song.duration_formatted)
                if song.uploader:
                    msg.add_field(name="Uploader", value=
                                  f"[{song.uploader}]({song.uploader_url})")
                if song.thumbnail:
                    msg.set_thumbnail(url=song.thumbnail)
                await ctx.send(embed=msg)

            # Put the song into the queue
            ctx.queue.put(song)
            counter += 1

            # Notify the user that the song has been put into the queue.
            if len(urls) != 1:
                await to_update_msg.edit(content=
                    f"Queued up `{counter}` songs so far.."
                )
            else:
                await to_update_msg.delete()

        # Finish queuing and notify the user about the status.
        if len(urls) != 1:
            await to_update_msg.edit(content=f"Queued up `{counter}` songs.")

        if counter == len(urls):
            await ctx.message.add_reaction(REACTION_OK)
        else:
            await ctx.message.add_reaction(REACTION_ERR)


    @commands.command(name="skip")
    async def _skip(self, ctx: commands.Context):
        """Skips the currently playing song"""
        if ctx.queue is not None:
            ctx.queue.skip()
            await ctx.message.add_reaction(REACTION_OK)


    @commands.command(name="pause")
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song"""
        if ctx.queue is not None:
            ctx.queue.pause()
            await ctx.message.add_reaction(REACTION_OK)


    @commands.command(name="shuffle")
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue"""
        if ctx.queue is not None:
            ctx.queue.shuffle()
            await ctx.message.add_reaction(REACTION_OK)


    @commands.command(name="clear")
    async def _clear(self, ctx: commands.Context):
        """Clears the queue"""
        if ctx.queue is not None:
            ctx.queue.clear()
            await ctx.message.add_reaction(REACTION_OK)


    @commands.command(name="loop")
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song"""
        if ctx.queue is not None:
            ctx.queue.loop()
            await ctx.message.add_reaction(REACTION_OK)


    @commands.command(name="queue")
    async def _print_queue(self, ctx: commands.Context):
        """Shows the current queue"""
        qlen = len(ctx.queue)
        if ctx.queue is None or (qlen == 0 and ctx.queue.current_song is None):
            await ctx.send("Queue is empty.")
            return

        # If the current song is looping, it is prefixed with LOOP,
        # otherwise its index is 0.
        #
        # This doesn't count the currently playing song;
        # If there is a song playing but there is no song in the queue,
        # qlen is 0...
        embed = discord.Embed(title=f"Queue `[{qlen}]`", inline=False)

        # First line of the embed: current song
        status  = "LOOP:" if ctx.queue.loop_song else "00"
        embed.add_field(
            name="Current",
            value=f"`{status}` {str(ctx.queue.current_song)}\n\n",
            inline=False
        )

        # The rest of the embed: the queue
        msg = ""
        for (counter, song) in enumerate(ctx.queue, start=1):
            pre_msg  = f"`{counter:02}` "
            pre_msg += str(song)
            pre_msg += "\n"

            # Embed value limit is 1024 chars
            if len(msg + pre_msg) >= 1020:
                msg += "`...`"
                break
            msg += pre_msg

        if msg != "":
            embed.add_field(name="Next up...", value=msg, inline=False)

        await ctx.message.add_reaction(REACTION_OK)
        await ctx.send(embed=embed)


    @commands.command(name="remove")
    async def _remove(self, ctx: commands.Context, *, idx: int):
        """Removes a song from the queue"""
        if ctx.queue is None or not self._valid_index(len(ctx.queue), idx):
            await ctx.message.add_reaction(REACTION_ERR)
            return

        if idx == 0:
            ctx.queue.skip()
        else:
            del ctx.queue[idx-1]

        await ctx.message.add_reaction(REACTION_OK)
