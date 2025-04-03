import discord
import asyncio
import random
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from utils.utils import get_next_case_id, StriveContext
from utils.constants import StriveConstants, giveaways
import re
from typing import Optional, Literal
from discord.ui import Button, View

constants = StriveConstants()

class GiveawayButton(Button):
    def __init__(self, giveaway_data, strive):
        self.giveaway = giveaway_data
        self.strive = strive
        super().__init__(emoji="<:striveJoin:1338900763317112925>", style=discord.ButtonStyle.grey, 
                        disabled=(datetime.utcnow() > giveaway_data["ends"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id in self.giveaway["entries"]:
            return await interaction.followup.send(embed=discord.Embed(color=self.strive.base_color, description=f"{self.strive.error} Already entered."), ephemeral=True)
        if datetime.utcnow() > self.giveaway["ends"]:
            self.disabled = True
            await interaction.message.edit(view=self.view)
            return await interaction.followup.send(embed=discord.Embed(color=self.strive.base_color, description=f"{self.strive.error} Giveaway ended."), ephemeral=True)

        self.giveaway["entries"].append(interaction.user.id)
        await giveaways.update_one({"_id": self.giveaway["_id"]}, {"$push": {"entries": interaction.user.id}})
        embed = interaction.message.embeds[0]
        embed.description = embed.description.replace(f"Entries: **{len(self.giveaway['entries'])-1}**", f"Entries: **{len(self.giveaway['entries'])}**")
        await interaction.message.edit(embed=embed)
        await interaction.followup.send(embed=discord.Embed(color=self.strive.base_color, description=f"{self.strive.success} Entered!"), ephemeral=True)

class EntriesView(View):
    def __init__(self, entries, strive):
        super().__init__()
        self.entries = entries
        self.strive = strive
        self.current_page = 0
        self.entries_per_page = 10

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.grey)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_page(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.grey)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.current_page + 1) * self.entries_per_page < len(self.entries):
            self.current_page += 1
            await self.update_page(interaction)

    async def update_page(self, interaction: discord.Interaction):
        start = self.current_page * self.entries_per_page
        end = start + self.entries_per_page
        current_entries = self.entries[start:end]
        
        embed = discord.Embed(
            title="Giveaway Entries",
            description="\n".join([f"{idx+1}. <@{entry}>" for idx, entry in enumerate(current_entries, start=start)]),
            color=self.strive.base_color
        )
        embed.set_footer(text=f"Page {self.current_page + 1}/{-(-len(self.entries)//self.entries_per_page)} | Total Entries: {len(self.entries)}")
        await interaction.response.edit_message(embed=embed, view=self)

class ViewEntriesButton(Button):
    def __init__(self, giveaway_data, strive):
        self.giveaway = giveaway_data
        self.strive = strive
        super().__init__(label="View Entries", style=discord.ButtonStyle.grey, emoji="<:member:1338813549912395846>")

    async def callback(self, interaction: discord.Interaction):
        view = EntriesView(self.giveaway["entries"], self.strive)
        embed = discord.Embed(
            title="Giveaway Entries",
            description="\n".join([f"{idx+1}. <@{entry}>" for idx, entry in enumerate(self.giveaway["entries"][:10])]),
            color=self.strive.base_color
        )
        embed.set_footer(text=f"Page 1/{-(-len(self.giveaway['entries'])//10)} | Total Entries: {len(self.giveaway['entries'])}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class Giveaways(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @tasks.loop(seconds=1)
    async def check_giveaways(self):
        await self.strive.wait_until_ready()
        async for giveaway in giveaways.find({"ended": False}):
            if datetime.utcnow() > giveaway["ends"]:
                winners = random.sample(giveaway["entries"], min(len(giveaway["entries"]), giveaway["winner_count"])) if giveaway["entries"] else []
                channel = self.strive.get_channel(giveaway["channel_id"])
                if channel:
                    try:
                        message = await channel.fetch_message(giveaway["message_id"])
                        winners_text = ", ".join([f"<@{w}>" for w in winners]) if winners else "No winners"
                        embed = discord.Embed(title=giveaway["prize"], description=f"Ended: {discord.utils.format_dt(giveaway['ends'], style='R')}\nWinners: **{winners_text}**\nHosted by: {giveaway['host']}\nEntries: **{len(giveaway['entries'])}**", color=self.strive.base_color, timestamp=giveaway["ends"])
                        view = View()
                        view.add_item(ViewEntriesButton(giveaway, self.strive))
                        await message.edit(embed=embed, view=view)
                        if winners:
                            await message.reply(f"<:striveGift:1338900761702305812> **Congratulations** {winners_text}, you have won [**{giveaway['prize']}**]({message.jump_url})!")
                    except: pass
                await giveaways.update_one({"_id": giveaway["_id"]}, {"$set": {"ended": True, "winners": winners}})

    @commands.hybrid_group(name="giveaway")
    async def giveaway(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @giveaway.command(name="start")
    @app_commands.describe(channel="Channel", duration="Duration (1d, 12h, 30m)", winners="Number of winners", prize="Prize")
    @commands.has_permissions(administrator=True)
    async def start(self, ctx: StriveContext, channel: discord.TextChannel, duration: str, winners: int, *, prize: str):
        try:
            seconds = self.parse_time(duration)
            end_time = datetime.utcnow() + timedelta(seconds=seconds)
        except ValueError:
            return await ctx.send_error("Invalid duration format. Use: 1d, 12h, 30m")

        if winners < 1:
            return await ctx.send_error("Winner count must be at least 1")

        giveaway_data = {
            "guild_id": ctx.guild.id, "channel_id": channel.id, "host": ctx.author.mention,
            "prize": prize, "winner_count": winners, "ends": end_time,
            "entries": [], "ended": False, "winners": [], "message_id": None
        }

        embed = discord.Embed(title=prize, description=f"React with the button below to enter!\n\nEnds: {discord.utils.format_dt(end_time, style='R')}\nHosted by: {ctx.author.mention}\nWinners: **{winners}**\nEntries: **0**", color=self.strive.base_color, timestamp=end_time)
        message = await channel.send(embed=embed)
        giveaway_data["message_id"] = message.id
        await giveaways.insert_one(giveaway_data)
        
        view = View()
        view.add_item(GiveawayButton(giveaway_data, self.strive))
        view.add_item(ViewEntriesButton(giveaway_data, self.strive))
        await message.edit(view=view)
        await ctx.send_success(f"Giveaway started in {channel.mention}!")

    def parse_time(self, time_str: str) -> int:
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        match = re.match(r'(\d+)([smhdw])', time_str.lower())
        if not match: raise ValueError("Invalid time format")
        value, unit = match.groups()
        return int(value) * time_units[unit]

    @giveaway.command(name="end", description="End a giveaway early")
    @app_commands.describe(message_url="The message URL or ID of the giveaway")
    @commands.has_permissions(administrator=True)
    async def end(self, ctx: StriveContext, message_url: str):
        message_id = int(message_url) if message_url.isdigit() else int(message_url.split('/')[-1])
        giveaway = await giveaways.find_one({"guild_id": ctx.guild.id, "message_id": message_id, "ended": False})
        if not giveaway:
            return await ctx.send_error("Giveaway not found or already ended")
        await giveaways.update_one({"_id": giveaway["_id"]}, {"$set": {"ends": datetime.utcnow()}})
        await ctx.send_success("Giveaway will end shortly")

    @giveaway.command(name="reroll", description="Reroll a giveaway's winners")
    @app_commands.describe(message_url="The message URL or ID of the giveaway")
    @commands.has_permissions(administrator=True)
    async def reroll(self, ctx: StriveContext, message_url: str):
        message_id = int(message_url) if message_url.isdigit() else int(message_url.split('/')[-1])
        giveaway = await giveaways.find_one({"guild_id": ctx.guild.id, "message_id": message_id, "ended": True})
        if not giveaway or not giveaway["entries"]:
            return await ctx.send_error("Giveaway not found, hasn't ended, or has no entries")

        import random
        new_winners = random.sample(giveaway["entries"], min(len(giveaway["entries"]), giveaway["winner_count"]))
        if channel := ctx.guild.get_channel(giveaway["channel_id"]):
            try:
                original_message = await channel.fetch_message(message_id)
                winners_text = ", ".join([f"<@{w}>" for w in new_winners])
                embed = original_message.embeds[0]
                embed.description = f"Ended: {discord.utils.format_dt(giveaway['ends'], style='R')}\nWinners: **{winners_text}**\nHosted by: {giveaway['host']}\nEntries: **{len(giveaway['entries'])}**"
                view = View()
                view.add_item(ViewEntriesButton(giveaway, self.strive))
                await original_message.edit(embed=embed, view=view)
                await original_message.reply(f"<:striveRerolled:1338900765632106589> **Giveaway rerolled!** Congratulations {winners_text} you have won [**{giveaway['prize']}**]({original_message.jump_url})!")
            except: pass
        
        await giveaways.update_one({"_id": giveaway["_id"]}, {"$set": {"winners": new_winners}})
        await ctx.send_success("Giveaway rerolled!")

    def parse_time(self, time_str: str) -> int:
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        if match := re.match(r'(\d+)([smhdw])', time_str.lower()):
            value, unit = match.groups()
            return int(value) * time_units[unit]
        raise ValueError("Invalid time format")

async def setup(strive):
    await strive.add_cog(Giveaways(strive))