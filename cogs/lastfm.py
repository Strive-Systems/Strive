import discord
import json
import time
from discord.ext import commands, tasks
from utils.constants import StriveConstants, lastfm
from utils.utils import StriveContext
from utils.lastfm import LastFMHandler
from datetime import datetime
from typing import Literal

constants = StriveConstants()

class LastFMCommandCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.lastfmhandler = LastFMHandler("b800358c32d9d0551f90492cf18fac9a")
        self.lastfm_crowns = {}
        self.globalwhoknows_cache = {}

    @commands.hybrid_command(description="Connect your Last.fm account", with_app_command=True, extras={"category": "LastFM"})
    async def lastfm(self, ctx: StriveContext, username: str):
        check = await lastfm.find_one({"discord_id": ctx.author.id})
        if check:
            return await ctx.send_error("You already have a Last.fm account connected.")

        try:
            user_info = await self.lastfmhandler.get_user_info(username)
            if not user_info:
                return await ctx.send_error("That Last.fm account doesn't exist.")

            await lastfm.insert_one({
                "discord_id": ctx.author.id,
                "username": username,
                "connected_at": int(time.time())
            })

            await ctx.send_success(f"Successfully connected your Last.fm account: **{username}**")
        except Exception as e:
            await ctx.send_error(f"An error occurred: {str(e)}")

    @commands.hybrid_command(aliases=['np', 'fm'], description="View your currently playing track", with_app_command=True, extras={"category": "LastFM"})
    async def nowplaying(self, ctx: StriveContext, member: discord.Member = None):
        member = member or ctx.author
        check = await lastfm.find_one({"discord_id": member.id})
        
        if not check:
            return await ctx.send_error(f"{'You don' if member == ctx.author else f'**{member}** doesn'}'t have a Last.fm account connected.")

        try:
            user = check['username']
            a = await self.lastfmhandler.get_tracks_recent(user, 1)
            artist = a['recenttracks']['track'][0]['artist']['#text'].replace(" ", "+")
            album = a['recenttracks']['track'][0]['album']['#text'] or "N/A"
            
            embed = discord.Embed(colour=constants.strive_embed_color_setup())
            embed.add_field(name="**Track:**", value = f"\n{a['recenttracks']['track'][0]['name']}", inline = True)
            embed.add_field(name="**Artist:**", value = f"\n{a['recenttracks']['track'][0]['artist']['#text']}", inline = True)
            embed.set_author(name = user, icon_url = member.display_avatar, url = f"https://last.fm/user/{user}")                               
            embed.set_thumbnail(url=(a['recenttracks']['track'][0])['image'][3]['#text'])
            embed.set_footer(text = f"Track Playcount: {await self.lastfmhandler.get_track_playcount(user, a['recenttracks']['track'][0])} ・Album: {album}", icon_url = (a['recenttracks']['track'][0])['image'][3]['#text'])
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Track Link", url=a['recenttracks']['track'][0]['url']))
            view.add_item(discord.ui.Button(label="Artist Link", url=f"https://last.fm/music/{artist}"))
            
            await ctx.send(embed=embed, view=view)

        except Exception as e:
            await ctx.send_error(f"An error occurred: {str(e)}")

    @commands.hybrid_command(description="View who knows an artist", with_app_command=True, extras={"category": "LastFM"})
    async def whoknows(self, ctx: StriveContext, *, artist: str = None):
        check = await lastfm.find_one({"discord_id": ctx.author.id})
        if not check:
            return await ctx.send_error("You don't have a Last.fm account connected.")

        if not artist:
            recent = await self.lastfmhandler.get_tracks_recent(check["username"], 1)
            artist = recent['recenttracks']['track'][0]['artist']['#text']

        listeners = []
        async for user in lastfm.find({"discord_id": {"$in": [m.id for m in ctx.guild.members]}}):
            member = ctx.guild.get_member(user["discord_id"])
            if member:
                plays = await self.lastfmhandler.get_artist_playcount(user["username"], artist)
                if plays > 0:
                    listeners.append((member, plays))

        if not listeners:
            return await ctx.send_error(f"Nobody in this server has listened to **{artist}**")

        listeners.sort(key=lambda x: x[1], reverse=True)
        description = "\n".join(f"{'🎵' if i == 0 else f'`{i+1}`'} {member.mention} - **{plays:,}** plays" 
                              for i, (member, plays) in enumerate(listeners[:10]))

        embed = discord.Embed(
            title=f"Who knows {artist}?",
            description=description,
            color=constants.strive_embed_color_setup()
        )
        embed.set_footer(text=f"Total Listeners: {len(listeners)}")

        await ctx.send(embed=embed)

async def setup(strive):
    await strive.add_cog(LastFMCommandCog(strive))