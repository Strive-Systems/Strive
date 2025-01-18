import discord
import uuid
from discord.ext import commands
from utils.embeds import DebugEmbed, CheckGuildEmbed
from utils.constants import StriveConstants
from utils.utils import get_next_case_id
from utils.constants import blacklists, blacklist_bypass
 

constants = StriveConstants()


# This is the admins cog for the bots admin commands that only server admins may run.
# This includes a debug command to debug the bot.

class AdminCommandsCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
    
    
    
    @commands.command()
    @commands.is_owner()
    async def checkguild(self, ctx: commands.Context, id: str):
        return
        
        
        
    # This command will add users into blacklist_bypass collection so they can run commands like JSK
    # and blacklist_guild or blacklist_user.
        
    @commands.command()
    async def addowner(self, ctx: commands.Context, user: discord.User):
        role = discord.utils.get(ctx.guild.roles, id = 1326485348326314054)
        if ctx.guild.id == 1326476818894557217 and role in ctx.author.roles:
            if user.id in constants.bypassed_users:
                return await ctx.send(f"<:error:1326752911870660704> {user.mention} is already in the bypass list.")

            # Add the user to the MongoDB collection
            
            await blacklist_bypass.insert_one({"discord_id": user.id})
            
            await ctx.send(f"<:success:1326752811219947571> {user.mention} has been added to the bypass list.")



    # This command will remove owners from the bypassed users and prevent them from using blacklist commands
    # or JSK commands. This is incase the developer or owner leaves or steps down.
    
    @commands.command()
    async def removeowner(self, ctx: commands.Context, user: discord.User):
        role = discord.utils.get(ctx.guild.roles, id = 1326485348326314054)
        if ctx.guild.id == 1326476818894557217 and role in ctx.author.roles:
            if user.id not in constants.bypassed_users:
                return await ctx.send(f"<:error:1326752911870660704> {user.mention} is not in the bypass list.")
            
            await blacklist_bypass.delete_one({"discord_id": user.id})
            
            await ctx.send(f"<:success:1326752811219947571> {user.mention} has been removed from the bypass list.")
            


    # This is a custom sync command cause JSK sync is broken, this will sync the commands with Discord
    # guilds accross the platform that uses the bot.


    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guild_id: int = None):
        if guild_id:
            guild = discord.Object(id=guild_id)
            synced = await self.strive.tree.sync(guild=guild)
        else:
            synced = await self.strive.tree.sync()
        await ctx.send(f"<:success:1326752811219947571> Synced {len(synced)} commands.")        



    # This is the set of commands to unblacklist a user from the bot. This follows the same set of logic as
    # blacklisting the user but in the opposit order.

    @commands.command()
    @commands.is_owner()
    async def unblacklist(self, ctx: commands.Context, entity: int):
        
        
        entity_type = ""


        # Check to see if its a user or guild
        
        try:
            entity_fetched: discord.User = await self.strive.fetch_user(entity)
            entity_type = 'user'
        except Exception:
            entity_fetched = entity
            entity_type = 'guild'


        # Assign what to call it in confirm message
        
        if entity_type == 'user':
            entity = entity_fetched.mention
            entity_id = entity_fetched.id
        elif entity_type == 'guild':
            entity_id = entity


        # Checks to see if its in the db
        
        if not await blacklists.find_one({"discord_id": entity_id, "type": entity_type}):
            return await ctx.send(f"<:error:1326752911870660704> {entity} is not blacklisted.")


        case_id = await get_next_case_id(ctx.guild.id)
        
        
        await blacklists.delete_one({"discord_id": entity_id, "type": entity_type})
        await ctx.send(ctx, f"<:success:1326752811219947571> **Case #{case_id} - {entity}** has been unblacklisted.")
        
        
        
        
    # This set of commands allows server administrators to blacklist the bot and prevent users
    # from runing commands.

    @commands.command()
    @commands.is_owner()
    async def blacklist(self, ctx: commands.Context, entity: int):
        
        entity_type = ""

        # Checks to see if its a user or guild
        
        try:
            entity_fetched: discord.User = await self.strive.fetch_user(entity)
            entity_type = 'user'
        except Exception:
            entity_fetched = entity
            entity_type = 'guild'


        # Assign what to call it in confirm message
        
        if entity_type == 'user':
            entity = entity_fetched.mention
            entity_id = entity_fetched.id
        elif entity_type == 'guild':
            entity_id = entity
            

        # Checks to see if its in the db
        
        if await blacklists.find_one({"discord_id": entity_id, "type": entity_type}):
            return await ctx.send(f"<:error:1326752911870660704> {entity} is already blacklisted.")
        
        
        # Creates, enters, and sends confirm message
        
        blacklist_entry = {
            "discord_id": entity_id,
            "type": entity_type
        }
        
        
        case_id = await get_next_case_id(ctx.guild.id)
        

        await blacklists.insert_one(blacklist_entry)
        await ctx.send(ctx, f"<:success:1326752811219947571> **Case #{case_id} - {entity}** has been blacklisted.")
        

async def setup(strive):
    await strive.add_cog(AdminCommandsCog(strive))