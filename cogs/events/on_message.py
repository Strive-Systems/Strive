import discord
from discord.ext import commands
from utils.utils import StriveContext


class OnMessage(commands.Cog):
    def __init__(self, strive):
        self.strive = strive



    @commands.Cog.listener()
    async def on_command(self, ctx: StriveContext):


        log_channel_id = 1338806081605861386
        channel = self.strive.get_channel(log_channel_id)


        if channel is None:
            print(f"Channel with ID {log_channel_id} not found.")
            return
        

        embed = discord.Embed(title="Command Run", color=0x2f3136)
        
        embed.add_field(name="Server Name", value=ctx.guild.name, inline=True)
        
        embed.add_field(name="Server ID", value=str(ctx.guild.id), inline=True)
        
        embed.add_field(
            name="Owner Info",
            value=f"<@{ctx.guild.owner_id}> (``{ctx.guild.owner_id}``)",
            inline=False,
        )
        
        embed.add_field(name="User", value=f"<@{ctx.author.id}>", inline=False)
        
        embed.add_field(
            name="Command",
            value=ctx.command.name,
            inline=False,
        )

        await channel.send(embed=embed)



async def setup(strive):
    await strive.add_cog(OnMessage(strive))
