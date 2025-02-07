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

    @commands.hybrid_group(name="lastfm", aliases=['lf'], description="Last.fm commands", fallback="help")
    async def lastfm(self, ctx: StriveContext):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @lastfm.command(name="set", description="Connect your Last.fm account")
    async def lastfm_set(self, ctx: StriveContext, username: str):
        check = await lastfm.find_one({"discord_id": ctx.author.id})
        if check:
            return await ctx.send_error("You already have a Last.fm account connected.")

        try:
            user_info = await self.lastfmhandler.get_user_info(username)
            if not user_info:
                return await ctx.send_error("That Last.fm account doesn't exist.")

            total_scrobbles = user_info['user']['playcount']
            registered_timestamp = int(user_info['user']['registered']['unixtime'])

            await lastfm.insert_one({
                "discord_id": ctx.author.id,
                "username": username,
                "connected_at": int(time.time()),
                "total_scrobbles": total_scrobbles,
                "registered_at": registered_timestamp
            })

            embed = discord.Embed(
                title="Last.fm Account Connected",
                description=f"Successfully connected your Last.fm account: **{username}**",
                color=constants.strive_embed_color_setup()
            )
            embed.add_field(name="Total Scrobbles", value=str(total_scrobbles), inline=True)
            embed.add_field(name="Account Created", value=f"<t:{registered_timestamp}:R>", inline=True)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send_error(f"An error occurred: {str(e)}")

    @lastfm.command(name="unset", description="Disconnect your Last.fm account")
    async def lastfm_unset(self, ctx: StriveContext):
        check = await lastfm.find_one({"discord_id": ctx.author.id})
        if not check:
            return await ctx.send_error("You don't have a Last.fm account connected.")

        await lastfm.delete_one({"discord_id": ctx.author.id})
        await ctx.send_success("Successfully disconnected your Last.fm account.")

    @lastfm.command(name="topartists", description="View your top artists")
    async def lastfm_topartists(self, ctx: StriveContext):
        check = await lastfm.find_one({"discord_id": ctx.author.id})
        if not check:
            return await ctx.send_error("You don't have a Last.fm account connected.")

        try:
            top_artists = await self.lastfmhandler.get_top_artists(check["username"])
            description = "\n".join(f"`{i+1}` **{artist['name']}** - {str(artist['playcount'])} plays" 
                                  for i, artist in enumerate(top_artists[:10]))

            embed = discord.Embed(
                title=f"{check['username']}'s Top Artists",
                description=description,
                color=constants.strive_embed_color_setup()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send_error(f"An error occurred: {str(e)}")

    @lastfm.command(name="topsongs", description="View your top songs")
    async def lastfm_topsongs(self, ctx: StriveContext):
        check = await lastfm.find_one({"discord_id": ctx.author.id})
        if not check:
            return await ctx.send_error("You don't have a Last.fm account connected.")

        try:
            top_tracks = await self.lastfmhandler.get_top_tracks(check["username"])
            description = "\n".join(f"`{i+1}` **{track['name']}** by {track['artist']['name']} - {str(track['playcount'])} plays" 
                                  for i, track in enumerate(top_tracks[:10]))

            embed = discord.Embed(
                title=f"{check['username']}'s Top Songs",
                description=description,
                color=constants.strive_embed_color_setup()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send_error(f"An error occurred: {str(e)}")

    @lastfm.command(name="topalbums", description="View your top albums")
    async def lastfm_topalbums(self, ctx: StriveContext):
        check = await lastfm.find_one({"discord_id": ctx.author.id})
        if not check:
            return await ctx.send_error("You don't have a Last.fm account connected.")

        try:
            top_albums = await self.lastfmhandler.get_top_albums(check["username"])
            description = "\n".join(f"`{i+1}` **{album['name']}** by {album['artist']['name']} - {str(album['playcount'])} plays" 
                                  for i, track in enumerate(top_albums[:10]))

            embed = discord.Embed(
                title=f"{check['username']}'s Top Albums",
                description=description,
                color=constants.strive_embed_color_setup()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send_error(f"An error occurred: {str(e)}")

    @lastfm.command(name="whoknows", aliases=['wk'], description="View who knows an artist")
    async def lastfm_whoknows(self, ctx: StriveContext, *, artist: str = None):
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
        description = "\n".join(f"{'🎵' if i == 0 else f'`{i+1}`'} {member.mention} - **{str(plays)}** plays" 
                              for i, (member, plays) in enumerate(listeners[:10]))

        embed = discord.Embed(
            title=f"Who knows {artist}?",
            description=description,
            color=constants.strive_embed_color_setup()
        )
        embed.set_footer(text=f"Total Listeners: {len(listeners)}")

        await ctx.send(embed=embed)

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

async def setup(strive):
    await strive.add_cog(LastFMCommandCog(strive))