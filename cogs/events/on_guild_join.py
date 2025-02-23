import discord
from discord import Embed
from discord.ext import commands
from utils.constants import StriveConstants
from utils.utils import StriveContext

constants = StriveConstants()


class OnGuildJoin(commands.Cog):
    def __init__(self, strive):
        self.strive = strive

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):

        if constants.strive_environment_type() == "Development":

            id = guild.id
            owner = guild.get_member(guild.owner_id)
            is_dev_guild = id in self.strive.beta_guilds
            channel = self.strive.get_guild(self.strive.beta_guilds[0]).get_channel(
                1338806026094247968
            )

            # Check if owner is None
            if owner is None:
                owner_info = "Owner not found"
            else:
                owner_info = f"{owner}({owner.id})"

            embed = Embed(
                title="Beta bot added to a guild",
                description=f"**NAME:** `{guild.name}`\n**ID:** `{id}`\n**OWNER:** `{owner_info}`\n**IS_DEV_GUILD:** `{is_dev_guild}`",
            )

            if not is_dev_guild:
                await guild.leave()

            await channel.send(embed=embed)

        channel = self.strive.get_channel(1338806026094247968)

        embed = discord.Embed(title="New Server Joined", color=0x2F3136)
        embed.add_field(name="Server Name", value=guild.name, inline=True)
        embed.add_field(name="Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="Member Count", value=str(guild.member_count), inline=True)
        embed.add_field(
            name="Owner Info",
            value=f"<@{str(guild.owner_id)}>(``{str(guild.owner_id)}``)",
            inline=False,
        )
        embed.add_field(
            name="Current Server Count",
            value=str(len(self.strive.guilds)),
            inline=False,
        )

        await channel.send(embed=embed)


async def setup(strive):
    await strive.add_cog(OnGuildJoin(strive))
