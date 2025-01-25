import discord
from discord.ext import commands
from zuid import ZUID
from utils.embeds import MissingArgsEmbed, BadArgumentEmbed, ForbiddenEmbed, MissingPermissionsEmbed, UserErrorEmbed, DeveloperErrorEmbed


class OnCommandError(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        error_id = ZUID(prefix="error_", length=10)
        error_id = error_id()
        
        if isinstance(error, commands.MissingRequiredArgument):
            embed = MissingArgsEmbed(error.param.name)
            return await ctx.send(embed=embed)



        elif isinstance(error, commands.BadArgument):
            embed = BadArgumentEmbed()
            return await ctx.send(embed=embed)



        elif isinstance(error, discord.Forbidden):
            embed = ForbiddenEmbed()
            return await ctx.send(embed=embed)



        elif isinstance(error, commands.MissingPermissions):
            embed = MissingPermissionsEmbed()
            return await ctx.send(embed=embed)
        


async def setup(strive):
    await strive.add_cog(OnCommandError(strive))