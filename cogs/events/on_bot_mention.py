import discord
from discord.ext import commands
from utils.utils import StriveContext


class OnstriveMention(commands.Cog):
    def __init__(self, strive):
        self.strive = strive



    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        content = message.content.strip()

        # Ignore messages sent by Strive itself
        
        if message.author.id == self.strive.user.id or message.reference:
            return

        # If the bot is mentioned followed by a command
        
        if content.startswith(f"<@{self.strive.user.id}> ") or content.startswith(f"<@!{self.strive.user.id}> "):
            
            
            command_content = content.split(maxsplit=1)[1] if len(content.split()) > 1 else None


            if command_content:
                fake_message = message
                fake_message.content = command_content
                await self.strive.process_commands(fake_message)
                return


        if self.strive.user in message.mentions:
            
            
            embed = discord.Embed(
                title="",
                description=(f"Hi {message.author.mention}, \n\nThanks for using **{self.strive.user.name}**! \n\nYou can run commands like `/about` or `/setup` to get started. The bots prefix is `!` by default and to change it you can run `/prefix newprefix`.\n"),
                color=discord.Color.from_str('#2a2c30')
            )
            
            
            await message.channel.send(embed=embed)



async def setup(strive):
    await strive.add_cog(OnstriveMention(strive))
