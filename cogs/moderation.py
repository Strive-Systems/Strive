import discord
import asyncio
import uuid
import re
import time
from discord.ext import commands
from utils.constants import StriveConstants, cases, blacklist_bypass
from utils.utils import get_next_case_id
from datetime import timedelta
from datetime import datetime


constants = StriveConstants()


class ModerationCommandCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.constants = StriveConstants()


    @commands.hybrid_command(description="You can run this command to warn a user in your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(administrator=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        
        if await is_blacklisted_or_admin(ctx, member):
            
            
            embed = discord.Embed(
                title="",
                description=f"<:error:1326752911870660704> You cannot warn {member.mention} because they are an admin or bypassed from moderation.",
                color=discord.Color.green()
            )
            
            
            await ctx.send(embed=embed)
            
            
        else:
    
        
            case_id = await get_next_case_id(ctx.guild.id)


            try:
                dm_message = f"<:success:1326752811219947571> **Case #{case_id} - You have been warned in {ctx.guild.name}** for {reason}."
                await member.send(dm_message)
            except discord.Forbidden:
                await ctx.send(f"<:error:1326752911870660704> Unable to send a DM to {member.mention}; warning the user in the server.")
            
            
            warn_entry = {
                "case_id": case_id,
                "guild_id": ctx.guild.id,
                "user_id": member.id,
                "moderator_id": ctx.author.id,
                "reason": reason,
                "timestamp": int(time.time()),
                "type": "warn",
                "status": "active"
            }
            await cases.insert_one(warn_entry)


            embed = discord.Embed(
                title="",
                description=f"<:success:1326752811219947571> **Case #{case_id} - {member}** has been warned for {reason}.",
                color=discord.Color.green()
            )
            
            
            await ctx.send(embed=embed)
        
        
        
    @commands.hybrid_command(name="ban", description="Ban command to ban members from your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.User, *, reason: str = "Nothing was provided"):
        
        if await is_blacklisted_or_admin(ctx, member):
            
            
            embed = discord.Embed(
                title="",
                description=f"<:error:1326752911870660704> You cannot ban {member.mention} because they are an admin or bypassed from moderation.",
                color=discord.Color.green()
            )
            
            
            await ctx.send(embed=embed)
            
            
        else:
        
        
            try:
                fetched_member: discord.Member = await self.strive.fetch_user(member.id)
            except Exception as e:
                raise commands.CommandInvokeError(e)
            
            
            banned_users = ctx.guild.bans()
            user_to_unban = None
            
            
            async for ban_entry in banned_users:
                if ban_entry.user.id == fetched_member.id:
                    user_to_unban = ban_entry.user
                    break


            # Moved the error checking to the top to prevent as many nested if statements.

            if user_to_unban:
                return await ctx.send(f"<:error:1326752911870660704> User {fetched_member} is already banned.", ephemeral=True)
            
            
            elif fetched_member == ctx.author:
                return await ctx.send("<:error:1326752911870660704> You cannot ban yourself!")
        
        
            elif fetched_member == ctx.guild.me:
                return await ctx.send("<:error:1326752911870660704> I cannot ban myself!")
            
            
            try:
                if fetched_member.top_role >= ctx.author.top_role:
                    return await ctx.send("You cannot ban a member with an equal or higher role!")
                
                
            except AttributeError:
                pass
            
            # Sends a DM to the user
            
            case_id = await get_next_case_id(ctx.guild.id)


            # Perform the ban operation
            try:
                await ctx.guild.ban(fetched_member, reason=reason)
            except Exception as e:
                raise commands.CommandInvokeError(e)
            
            # Log to MongoDB
            
            ban_entry = {
                "case_id": case_id,
                "guild_id": ctx.guild.id,
                "user_id": member.id,
                "moderator_id": ctx.author.id,
                "reason": reason,
                "timestamp": int(time.time()),
                "type": "ban",
                "status": "active"
            }
            await cases.insert_one(ban_entry)

            # Send the success message
            
            await ctx.send(f"<:success:1326752811219947571> **Case #{case_id} - {member}** has been banned for {reason}.")
                
            
            
    @commands.hybrid_command(name="unban", description="Unban command to unban members from your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided"):
        
        # Defer the response to avoid delay issues.
        
        await ctx.defer()

        try:
            
            # This command was hell to write.
            # Use async for to iterate over the banned users (since it's an async generator).
            
            banned_users = ctx.guild.bans()  # Don't await here, just call it.

            user_to_unban = None


            # Iterate asynchronously through the banned users list.
            
            async for ban_entry in banned_users:
                if ban_entry.user.id == user.id:
                    user_to_unban = ban_entry.user
                    break


            if user_to_unban is None:
                await ctx.send(f"<:error:1326752911870660704> User {user} is not banned.", ephemeral=True)
                return


            await ctx.guild.unban(user_to_unban, reason=reason)
            case_id = await get_next_case_id(ctx.guild.id)
            await ctx.send(f"<:success:1326752811219947571> **Case #{case_id} - Successfully unbanned {user_to_unban.mention}** for {reason}.", ephemeral=True)


        except discord.Forbidden:
            await ctx.send("<:error:1326752911870660704> I do not have permissions to unban this user.", ephemeral=True)
            
        
        
    # Softban command that bans and unbans a user, effectively deleting their messages.
    
    @commands.hybrid_command(description="Softban a user, deleting their messages from the server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        
        if await is_blacklisted_or_admin(ctx, member):
            
            
            embed = discord.Embed(
                title="",
                description=f"<:error:1326752911870660704> You cannot softban {member.mention} because they are an admin or bypassed from moderation.",
                color=discord.Color.green()
            )
            
            
            await ctx.send(embed=embed)
            
        else:

            await ctx.guild.ban(member, reason=reason, delete_message_days=1)
            case_number = f"Case #{str(uuid.uuid4().int)[:4]}"  # Generate a short unique case number
            await ctx.send(f"<:success:1326752811219947571> **Case #{case_number} - Successfully softbanned {member.mention}** for: {reason}")
            await asyncio.sleep(2)
            await ctx.guild.unban(member)
        
    
    
    @commands.hybrid_command(description="Mute/Timeout a certain user", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, time: str, *, reason: str = "No reason provided"):
        
        if await is_blacklisted_or_admin(ctx, member):
            
            
            embed = discord.Embed(
                title="",
                description=f"<:error:1326752911870660704> You cannot mute {member.mention} because they are an admin or bypassed from moderation.",
                color=discord.Color.green()
            )
            
            
            await ctx.send(embed=embed)
            

        else:
    
    
            if member == ctx.author:
                return await ctx.send("<:error:1326752911870660704> You cannot mute yourself!")
            
            
            elif member == ctx.guild.me:
                return await ctx.send("<:error:1326752911870660704> I cannot mute myself!")
            
            
            try:
                if member.top_role >= ctx.author.top_role:
                    return await ctx.send("You cannot mute a member with an equal or higher role!")
            except AttributeError:
                pass


            time_match = re.match(r"(\d+)([mshd])", time)
            if not time_match:
                return await ctx.send("Invalid time format. Use `1m`, `1h`, etc.")


            amount, unit = time_match.groups()
            amount = int(amount)


            if unit == "m":
                delta = timedelta(minutes=amount)
            elif unit == "h":
                delta = timedelta(hours=amount)
            elif unit == "s":
                delta = timedelta(seconds=amount)
            elif unit == "d":
                delta = timedelta(days=amount)
            else:
                return await ctx.send("Invalid time unit. Use `m`, `h`, `s`, or `d`.")


            until = discord.utils.utcnow() + delta
            await member.timeout(until, reason=reason)
            formatted_time = discord.utils.format_dt(until, style="f")
            
            
            embed = discord.Embed(
                title="",
                description=f"<:success:1326752811219947571> **{member.name}** has been muted until {formatted_time}!",
                color=discord.Color.green()
            )
            
            
            await ctx.send(embed=embed)



    @commands.hybrid_command(description="Remove timeout from a certain user", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member == ctx.author:
            return await ctx.send("<:error:1326752911870660704> You cannot unmute yourself!")
    
        elif member == ctx.guild.me:
            return await ctx.send("<:error:1326752911870660704> I cannot unmute myself!")
        
        try:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send("You cannot unmute a member with an equal or higher role!")
        except AttributeError:
            pass


        await member.timeout(None, reason=reason)
        
        
        embed = discord.Embed(
            title="",
            description=f"<:success:1326752811219947571> **{member.name}** has been unmuted!",
            color=discord.Color.green()
        )
        
        
        await ctx.send(embed=embed)
        
        
        
    @commands.hybrid_command(description="You can run this command to kick a user in your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        
        
        if await is_blacklisted_or_admin(ctx, member):
            
            
            embed = discord.Embed(
                title="",
                description=f"<:error:1326752911870660704> You cannot kick {member.mention} because they are an admin or bypassed from moderation.",
                color=discord.Color.green()
            )
            
            
            await ctx.send(embed=embed)
            
            
        else:
        
        
            if not ctx.guild.me.guild_permissions.manage_messages:
                await ctx.send("<:error:1326752911870660704> I do not have permission to manage messages.")
                return
            
            
            if not ctx.guild.me.guild_permissions.kick_members:
                await ctx.send("<:error:1326752911870660704> I do not have permission to kick members.")
                return


            try:
                await member.kick(reason=reason)
            except discord.Forbidden:
                await ctx.send("<:error:1326752911870660704> I do not have permission to kick that user.")
                return
            except discord.HTTPException:
                await ctx.send("<:error:1326752911870660704> I couldn't kick this user.")
                return


            case_id = await get_next_case_id(ctx.guild.id)


            try:
                dm_message = f"<:success:1326752811219947571> **Case #{case_id} - You have been kicked from **{ctx.guild.name}** for {reason}"
                await member.send(dm_message)
            except discord.Forbidden:
                await ctx.send(f"<:error:1326752911870660704> Unable to send a DM to {member.mention}; kicking the user in the server.")


            kick_entry = {
                "case_id": case_id,
                "guild_id": ctx.guild.id,
                "user_id": member.id,
                "moderator_id": ctx.author.id,
                "reason": reason,
                "timestamp": int(time.time()),
                "type": "kick",
                "status": "active"
            }
            await cases.insert_one(kick_entry)
            

            await ctx.send(f"<:success:1326752811219947571> **Case #{case_id} - {member}** has been kicked for {reason}.")
            
        
        
    @commands.hybrid_group(description="Group command")
    async def case(self, ctx):
        return
    
    
    
    @case.command(description="Searches cases by an Case ID.", with_app_command=True)
    async def view(self, ctx: commands.Context, caseid: int):
        case_info = await cases.find_one({'case_id': caseid, 'guild_id': ctx.guild.id})
        
        
        if case_info:
            
            embed = discord.Embed(
                title=f"{case_info.get('type').title()} | Case #{case_info.get('case_id')}",
                description=f"Action took place on <t:{case_info.get('timestamp')}:F>.",
                color=self.constants.strive_embed_color_setup(),
            )

            embed.add_field(
                name="Member",
                value=f"<@{case_info.get('user_id')}> (`{case_info.get('user_id')}`)",
                inline=True
            )
            
            embed.add_field(
                name="Moderator",
                value=f"<@{case_info.get('moderator_id')}> (`{case_info.get('moderator_id')}`)",
                inline=True
            )

            embed.add_field(
                name="Reason",
                value=case_info.get('reason') or "No reason provided.",
                inline=False
            )


            try:
                member: discord.Member = await self.strive.fetch_user(case_info.get('user_id'))
                embed.set_author(name=f"@{member.name}", icon_url=member.avatar.url)
                
                
            except:
                embed.set_author(name="Unknown User")


            await ctx.send(embed=embed)
            
            
        else:
            
            embed = discord.Embed(
                title="",
                description=f"<:error:1326752911870660704> Case #{caseid} could not be found!",
                color=discord.Color.red()
            )
            
            
            await ctx.send(embed=embed)
    
    
    
    @case.command(description="Void a case by ID", with_app_command=True)
    async def void(self, ctx: commands.Context, *, caseid: int):
        
        
        case_info = await cases.find_one_and_update({'case_id': caseid, 'guild_id': ctx.guild.id}, {'$set': {'status': 'cleared'}})
        
        
        if case_info:
            await ctx.send(f"<:success:1326752811219947571> Case #{caseid} has been voided!")
        
        
        elif not case_info:
            await ctx.send(f"<:error:1326752911870660704> Case #{caseid} could not be found!")
            
           
            
    @commands.hybrid_group(description="Group command")
    async def modlogs(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a valid subcommand (view, transfer, clear).")



    @modlogs.command(description="View all modlogs for a certain user")
    async def view(self, ctx, member: discord.Member):
        number = 0
        embed = discord.Embed(
            title="",
            description="",
            color=self.constants.strive_embed_color_setup(),
            timestamp=datetime.utcnow()
        )

        results = cases.find({'user_id': member.id, "guild_id": ctx.guild.id})
        
        
        async for result in results:
            if result.get('status') == "active":
                number += 1
                embed.add_field(
                    name=f"Case ID: {result.get('case_id')} | {result.get('type').title()}",
                    value=(
                        f"Reason: {result.get('reason')}\n"
                        f"Moderator: <@{result.get('moderator_id')}> ({result.get('moderator_id')})\n"
                        f"Date: <t:{result.get('timestamp')}:F>"
                    ),
                    inline=False
                )


        if number == 0:
            embed = discord.Embed(
                title="",
                description="<:error:1326752911870660704> No mod logs could be found for this user!",
                color=self.constants.strive_embed_color_setup()
            )
            
            
        else:
            try:
                embed.set_author(
                    name=f"{member.name}'s Modlogs",
                    icon_url=member.avatar.url
                )
                
            except AttributeError:
                embed.set_author(
                    name=f"{member.name}'s Modlogs",
                    icon_url=member.default_avatar.url
                )
                
                
            embed.set_footer(text=f"ID: {member.id} • Total Modlogs: {number}")


        await ctx.send(embed=embed)



    @modlogs.command(description="Transfer all modlogs to a different user")
    async def transfer(self, ctx, olduser: discord.Member, newuser: discord.Member):
        results = cases.find({'user_id': olduser.id, "guild_id": ctx.guild.id})
        failed_cases = []


        async for result in results:
            updated_case = await cases.find_one_and_update(
                {'case_id': result.get('case_id'), 'user_id': olduser.id, 'guild_id': ctx.guild.id},
                {'$set': {'user_id': newuser.id}}
            )
            if not updated_case:
                failed_cases.append(result.get('case_id'))


        if failed_cases:
            await ctx.send(f"<:error:1326752911870660704> The following cases could not be updated: {', '.join(map(str, failed_cases))}")


        embed = discord.Embed(
            title="",
            description=(
                f"<:success:1326752811219947571> All moderation logs for **{olduser.name}** "
                f"have been transferred to **{newuser.name}**."
            ),
            color=discord.Color.green()
        )
        
        
        await ctx.send(embed=embed)



    @modlogs.command(description="Clear all modlogs for a certain user")
    async def clear(self, ctx, member: discord.Member):
        results = cases.find({'user_id': member.id, "guild_id": ctx.guild.id})
        failed_cases = []


        async for result in results:
            updated_case = await cases.find_one_and_update(
                {'case_id': result.get('case_id'), 'guild_id': ctx.guild.id},
                {'$set': {'status': 'cleared'}}
            )
            if not updated_case:
                failed_cases.append(result.get('case_id'))


        if failed_cases:
            await ctx.send(f"<:error:1326752911870660704> The following cases could not be cleared: {', '.join(map(str, failed_cases))}")


        embed = discord.Embed(
            title="",
            description=f"<:success:1326752811219947571> All moderation logs have been cleared for **{member.name}**.",
            color=discord.Color.green()
        )
        
        
        await ctx.send(embed=embed)



    async def is_blacklisted_or_admin(ctx, member: discord.Member):


        if member.guild_permissions.administrator:
            return True
        

        blacklist_entry = await blacklist_bypass.find_one({"user_id": member.id, "guild_id": ctx.guild.id})
        if blacklist_entry:
            return True


        return False



async def setup(strive):
    await strive.add_cog(ModerationCommandCog(strive))