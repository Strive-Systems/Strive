import discord
import time
from discord.ext import commands
from collections import defaultdict
from utils.embeds import AutoModListWordsEmbed
from utils.constants import StriveConstants, blacklistedwords, blacklist_bypass

constants = StriveConstants()

class AutoModCommandCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive


    async def cog_load(self):

        await self.fetch_banned_words()
        await self.fetch_blacklist_bypass()



    async def fetch_banned_words(self):
        
        
        self.strive.blacklistedwords = defaultdict(list)
        
        
        async for doc in blacklistedwords.find({}):
            guild_id = doc.get('guild_id')
            if guild_id and 'word' in doc:
                self.strive.blacklistedwords[guild_id].append(doc['word'])



    async def fetch_blacklist_bypass(self):
        
        
        self.strive.blacklist_bypass = set()
        
        
        async for doc in blacklist_bypass.find({}):
            self.strive.blacklist_bypass.add(doc.get('discord_id'))



    async def check_for_banned_words(self, message):
        guild_id = message.guild.id
        content = message.content.lower()

        for word in self.strive.blacklistedwords.get(guild_id, []):
            if word in content:
                await message.delete()
                try:
                    await message.author.send(f"Your message in **{message.guild.name}** contained inappropriate content and was removed.")
                except discord.Forbidden:
                    await message.channel.send(f"{message.author.mention}, your message contained inappropriate content and was removed.")



    @commands.hybrid_command(name="addword", description="Adds a word to the banned words list (Admin only)")
    @commands.has_permissions(administrator=True)
    async def addword(self, ctx: commands.Context, word: str):
        guild_id = ctx.guild.id
        await blacklistedwords.insert_one({'guild_id': guild_id, 'word': word})
        await self.fetch_banned_words()
        await ctx.send_success(f"The word `{word}` has been added to the banned words list.")



    @commands.hybrid_command(name="removeword", description="Removes a word from the banned words list (Admin only)")
    @commands.has_permissions(administrator=True)
    async def removeword(self, ctx: commands.Context, word: str):
        guild_id = ctx.guild.id
        await blacklistedwords.delete_one({'guild_id': guild_id, 'word': word})
        await self.fetch_banned_words()
        await ctx.send_success(f"The word `{word}` has been removed from the banned words list.")



    @commands.hybrid_command(name="listwords", description="Lists the banned words for this guild")
    async def listwords(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        banned_words_list = self.strive.blacklistedwords.get(guild_id, [])

        if not banned_words_list:
            await ctx.send_error(f"No banned words found for this server.", ephemeral=True)
            return

        banned_words_str = ', '.join(banned_words_list)
        embed_color = constants.strive_embed_color_setup()
        embed = AutoModListWordsEmbed(guild_name=ctx.guild.name, banned_words=banned_words_str, color=embed_color)

        await ctx.send(embed=embed, ephemeral=True)



async def setup(strive):
    await strive.add_cog(AutoModCommandCog(strive))