import discord
from discord.ext import tasks, commands
from utils.utils import StriveContext

class Tasks(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.change_status.start()

    @tasks.loop(seconds=30)
    async def change_status(self):
        guild_count = len(self.strive.guilds)
        user_count = sum(guild.member_count for guild in self.strive.guilds)


        await self.strive.change_presence(activity=discord.Activity(
            name=f"{guild_count} Guilds • {user_count:,} Users • /help",
            type=discord.ActivityType.watching
        ))      
                

async def setup(strive):
  await strive.add_cog(Tasks(strive))