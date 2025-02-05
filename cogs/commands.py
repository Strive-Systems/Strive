import os
import discord
import time
import datetime
import subprocess
import shortuuid
import pytz
from dotenv import load_dotenv
from datetime import datetime
from discord import Interaction, Embed
from discord.ext import commands
from utils.constants import StriveConstants, db, prefixes, timezones
from utils.embeds import AboutEmbed, AboutWithButtons, PingCommandEmbed, ServerInformationEmbed, EmojiFindEmbed, PrefixEmbed, PrefixSuccessEmbed, PrefixSuccessEmbedNoneChanged


constants = StriveConstants()


# The main commands Cog.

class CommandsCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        


    # This is the info Command for strive. Place every other command before this one, this should be the last command in
    # this file for readability purposes.

    @commands.hybrid_command(description="Provides important information about Strive.", with_app_command=True, extras={"category": "Other"})
    async def about(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        
        
        # Collect information for the embed such as the bots uptime, hosting information, database information
        # user information and server information so that users can see the growth of the bot.
        
        uptime_seconds = getattr(self.strive, 'uptime', 0)
        uptime_formatted = f"<t:{int((self.strive.start_time.timestamp()))}:R>"
        guilds = len(self.strive.guilds)
        users = sum(guild.member_count for guild in self.strive.guilds)
        version_info = await db.command('buildInfo')
        version = version_info.get('version', 'Unknown')
        shards = self.strive.shard_count or 1
        cluster = 0
        environment = constants.strive_environment_type()
        
        
        # Formats the date and time
        
        command_run_time = datetime.now()
        formatted_time = command_run_time.strftime("Today at %I:%M %p UTC")


        # This builds the emebed.

        embed = AboutEmbed.create_info_embed(
            uptime=self.strive.start_time,
            guilds=guilds,
            users=users,
            latency=self.strive.latency,
            version=version,
            bot_name=ctx.guild.name,
            bot_icon=ctx.guild.icon,
            shards=shards,
            cluster=cluster,
            environment=environment,
            command_run_time=formatted_time,
            thumbnail_url="https://cdn.discordapp.com/attachments/1326735526740496444/1333643206226739312/StriveLogoGrey.png"
        )


        # Send the emebed to view.

        view = AboutWithButtons.create_view()

        await ctx.send(embed=embed, view=view)
        
        
        
    # This is a server information command that will show information about a server
    # in an easy to read emebed similar to circle bot.
    
    @commands.hybrid_command(description="Displays information about the current server.", with_app_command=True, extras={"category": "General"})
    async def serverinfo(self, ctx):


        embed = ServerInformationEmbed(ctx.guild, constants).create_embed()

        if isinstance(ctx, Interaction):
            
            await ctx.response.send_message(embed=embed)
            
        elif isinstance(ctx, commands.Context):
            
            await ctx.send(embed=embed)
            
            
            
    # This gets the MongoDB latency using a lightweight command like ping and then mesuring its response time.        
            
    async def get_mongo_latency(self):
        try:
            start_time = time.time()
            
            
            await db.command('ping')


            mongo_latency = round((time.time() - start_time) * 1000)
            return mongo_latency


        except Exception as e:
            print(f"Error measuring MongoDB latency: {e}")
            return -1
    
            
    
    # This is the space for the ping command which will allow users to ping.
    
    @commands.hybrid_command(name="ping", description="Check the bot's latency and uptime.", with_app_command=True, extras={"category": "Other"})
    async def ping(self, ctx: commands.Context):
        
        
        latency = self.strive.latency
        
        database_latency = await self.get_mongo_latency()


        # Calculate uptime
        
        uptime_seconds = getattr(self.strive, 'uptime', 0)
        uptime_formatted = f"<t:{int((self.strive.start_time.timestamp()))}:R>"
        

        # Use the embed creation function from embeds.py
        
        embed = PingCommandEmbed.create_ping_embed(
            latency=latency,
            database_latency=database_latency,
            uptime=self.strive.start_time
        )
        

        await ctx.send(embed=embed)



    @commands.hybrid_command(description="Finds and shows info about a emoji", with_app_command=True, extras={"category": "General"})
    async def emoji_find(self, ctx, emoji: discord.Emoji):


        if emoji.name == None:
            await ctx.send("{self.bot.error} I couldn't find that emoji.")
            return
        

        await ctx.send(embed=EmojiFindEmbed(emoji).create_embed())
    


    @commands.hybrid_command(description="Shows all the emojis in the server.", with_app_command=True, extras={"category": "General"})
    async def emojis(self, ctx: commands.Context):
        emojis = "".join(f"{emoji}" for emoji in ctx.guild.emojis)


        embed = discord.Embed(
            description=emojis,
            color=constants.strive_embed_color_setup()
        )


        embed.set_author(name=f"{ctx.guild.name} emojis", icon_url=ctx.guild.icon.url)


        await ctx.send(embed=embed)



    @commands.hybrid_command(description="Enlarges a provided emoji.", with_app_command=True, extras={"category": "General"})
    async def enlarge(self, ctx, emoji: discord.Emoji):


        if emoji == None:
            embed = Embed(
                title="",
                description=f"{self.bot.error} I could not find that emoji."
            )
            await ctx.reply(embed=embed)
            return
        

        emoji_url = emoji.url


        embed = Embed(color=constants.strive_embed_color_setup()).set_thumbnail(url=emoji_url)

        
        await ctx.send(embed=embed)
        
        
        
    # This is the avatar command that will allow users to run /av or prefix!av to see their own
    # or another users avatar in an embed state.

    @commands.hybrid_command(name="av", description="Displays the avatar of a user. If no user is mentioned, shows your avatar.", with_app_command=True, extras={"category": "General"})
    async def av(self, ctx, user: discord.User = None):

            
        if user is None:
            user = ctx.author
        
        
        embed = discord.Embed(
            title=f"{user}'s Avatar",
            color=constants.strive_embed_color_setup()
        )
        
        
        embed.set_image(url=user.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author}")


        await ctx.send(embed=embed)
        
        
        
    @commands.hybrid_command(description="Change the prefix of Strive in your server.", with_app_command=True, extras={"category": "General"})
    @commands.has_guild_permissions(manage_guild=True)
    async def prefix(self, ctx, prefix: str = None):
        if prefix is None:
            guild_data = await prefixes.find_one({"guild_id": str(ctx.guild.id)})
        
            if guild_data:
                prefix = guild_data.get("prefix")
                
            else:
                load_dotenv()
                prefix = os.getenv('PREFIX')
            
            embed = PrefixSuccessEmbedNoneChanged(prefix)
            
        else:
            # Update the prefix if the user provides a new one
                
            result = await prefixes.update_one(
                {"guild_id": str(ctx.guild.id)},
                {"$set": {"prefix": prefix}},
                upsert=True
            )

            self.strive.prefixes[ctx.guild.id] = prefix
            embed = PrefixSuccessEmbed(prefix)
        
        
        await ctx.send(embed=embed)



    # This is a say command that allows users to say things using the bot.

    @commands.hybrid_command(description="Use this command to say things to people using the bot.", with_app_command=True, extras={"category": "General"})
    @commands.has_permissions(administrator=True)
    async def say(self, ctx, *, message: str):
 
        if ctx.interaction:
            await ctx.send("sent", allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)
            await ctx.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.channel.send(message, allowed_mentions=discord.AllowedMentions.none())
            await ctx.message.delete()
            


    @commands.hybrid_command(description="Use this command to generate a donation link to donate to Strive.", with_app_command=True, extras={"category": "General"})
    async def donate(self, ctx):
        
        embed = discord.Embed(
            title="Donate to Strive Systems",
            description=f"Thank you for wanting to donate! It goes a long way in terms of supporting this project as its completely free, here is your donation link. \n\n https://buy.stripe.com/bIY7uncmy3rW1kk144",
            color=constants.strive_embed_color_setup()
        )
            
            
        await ctx.send(embed=embed)

    @commands.hybrid_group(description="Allows you to set your timezone or view another users", aliases=["tz"], extras={"category": "General"}, with_app_command=True)
    async def timezone(self, ctx, user: discord.Member = None):
        try:
            if user is None:
                user = ctx.author

            timezone_data = await timezones.find_one({"user_id": str(user.id)})
            
            if not timezone_data:
                embed = discord.Embed(
                    title="",
                    description=f"{self.bot.error} {'You have' if user == ctx.author else f'{user.name} has'} not set a timezone yet.",
                    color=constants.strive_embed_color_setup()
                )
                await ctx.send(embed=embed)
                return

            timezone = pytz.timezone(timezone_data["timezone"])
            current_time = datetime.now(timezone)

            embed = discord.Embed(
                title=f"Timezone - {user.name}",
                description=f"> **Timezone:** {timezone_data['timezone']}\n> **Local Time:** {current_time.strftime('%I:%M %p %Z')}",
                color=constants.strive_embed_color_setup()
            )
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error viewing timezone: {e}")
            embed = discord.Embed(
                title="",
                description=f"{self.bot.error} An error occurred while viewing the timezone.",
                color=constants.strive_embed_color_setup()
            )
            await ctx.send(embed=embed)

    @timezone.command(name="set", description="Set your timezone", extras={"category": "General"}, with_app_command=True)
    async def timezone_set(self, ctx, timezone: str):
        try:
            timezone = timezone.lower()
            matching_timezones = [tz for tz in pytz.all_timezones if timezone in tz.lower()]
            
            if not matching_timezones:
                embed = discord.Embed(
                    description=f"{self.bot.error} Invalid timezone. Please use a city name like 'london' or 'tokyo'.",
                    color=constants.strive_embed_color_setup()
                )
                await ctx.send(embed=embed)
                return

            selected_timezone = matching_timezones[0]
            await timezones.update_one(
                {"user_id": str(ctx.author.id)},
                {"$set": {"timezone": selected_timezone}},
                upsert=True
            )

            embed = discord.Embed(
                description=f"{self.bot.success} Your timezone has been set to `{selected_timezone}`",
                color=constants.strive_embed_color_setup()
            )

            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="",
                description=f"{self.bot.error} An error occurred while setting your timezone.",
                color=constants.strive_embed_color_setup()
            )
            await ctx.send(embed=embed)

async def setup(strive):
    await strive.add_cog(CommandsCog(strive))