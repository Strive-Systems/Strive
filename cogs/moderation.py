import discord
import asyncio
import uuid
import re
import time
from discord.ext import commands
from utils.constants import StriveConstants, cases, blacklist_bypass
from utils.utils import get_next_case_id, StriveContext
from datetime import timedelta
from datetime import datetime


constants = StriveConstants()


class ModerationCommandCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.constants = StriveConstants()
        
        
    
    @staticmethod
    async def is_blacklisted_or_admin(ctx, member: discord.Member):
        
        
        if isinstance(member, discord.User):
            member = ctx.guild.get_member(member.id)


        if member is None:
            return False


        if member.guild_permissions.administrator:
            return True
        
        
        if member.top_role >= ctx.author.top_role:
            return True


        blacklist_entry = await blacklist_bypass.find_one({"discord_id": member.id})
        if blacklist_entry:
            return True


        return False



    @commands.hybrid_command(description="You can run this command to warn a user in your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(administrator=True)
    async def warn(self, ctx: StriveContext, member: discord.Member, *, reason: str = "No reason provided"):
        
        if await ModerationCommandCog.is_blacklisted_or_admin(ctx, member):
            
            
            await ctx.send_error(f"You cannot warn {member.mention} because they are an admin or bypassed from moderation.")
            
            
        else:
    
        
            case_id = await get_next_case_id(ctx.guild.id)


            try:
                dm_message = f"**Case #{case_id} - You have been warned in {ctx.guild.name}** for {reason}."
                await member.send(dm_message)
            except discord.Forbidden:
                await ctx.send_error(f"Unable to send a DM to {member.mention}; warning the user in the server.")
            
            
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


            await ctx.send_success(f"**Case #{case_id} - {member}** has been warned for {reason}.")        
        
        
    @commands.hybrid_command(name="ban", description="Ban command to ban members from your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: StriveContext, member: discord.User, *, reason: str = "Nothing was provided"):
        
        if await ModerationCommandCog.is_blacklisted_or_admin(ctx, member):
            
            
            await ctx.send_error(f"You cannot ban {member.mention} because they are an admin or bypassed from moderation.")
            
            
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
                return await ctx.send_error(f"{fetched_member} is already banned.")
            
            
            elif fetched_member == ctx.author:
                return await ctx.send_error(f"You cannot ban yourself!")
        
        
            elif fetched_member == ctx.guild.me:
                return await ctx.send_error(f"I cannot ban myself!")
            
            
            try:
                if fetched_member.top_role >= ctx.author.top_role:
                    return await ctx.send_error(f"You cannot ban a member with an equal or higher role!")
                
                
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
            
            await ctx.send_success(f"**Case #{case_id} - {fetched_member}** has been banned for {reason}.")
                
            
            
    @commands.hybrid_command(name="unban", description="Unban command to unban members from your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx: StriveContext, user: discord.User, *, reason: str = "No reason provided"):
        
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
                await ctx.send_error(f"{user.mention} is not banned.")
                return


            await ctx.guild.unban(user_to_unban, reason=reason)
            case_id = await get_next_case_id(ctx.guild.id)
            await ctx.send_success(f"**Case #{case_id} - {user_to_unban}** has been unbanned for {reason}.")


        except discord.Forbidden:
            await ctx.send_error(f"I do not have permission to unban {user.mention}.")
            
        
        
    # Softban command that bans and unbans a user, effectively deleting their messages.
    
    @commands.hybrid_command(description="Softban a user, deleting their messages from the server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        
        if await ModerationCommandCog.is_blacklisted_or_admin(ctx, member):
            await ctx.send_error(f"You cannot softban {member.mention} because they are an admin or bypassed from moderation.")
            
        else:
            await ctx.guild.ban(member, reason=reason, delete_message_days=1)
            case_number = f"Case #{str(uuid.uuid4().int)[:4]}"  # Generate a short unique case number
            await ctx.send_success(f"**Case #{case_number} - Successfully softbanned {member.mention}** for: {reason}")
            await asyncio.sleep(2)
            await ctx.guild.unban(member)        
    
    
    @commands.hybrid_command(description="Mute/Timeout a certain user", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: StriveContext, member: discord.Member, time: str, *, reason: str = "No reason provided"):
        
        if await ModerationCommandCog.is_blacklisted_or_admin(ctx, member):
            await ctx.send_error(f"You cannot mute {member.mention} because they are an admin or bypassed from moderation.")

        else:
            if member == ctx.author:
                return await ctx.send_error("You cannot mute yourself!")
            
            elif member == ctx.guild.me:
                return await ctx.send_error("I cannot mute myself!")
            
            try:
                if member.top_role >= ctx.author.top_role:
                    return await ctx.send_error("You cannot mute a member with an equal or higher role!")
            except AttributeError:
                pass

            time_match = re.match(r"(\d+)([mshd])", time)
            if not time_match:
                return await ctx.send_error("Invalid time format. Use `1m`, `1h`, etc.")

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
                return await ctx.send_error("Invalid time unit. Use `m`, `h`, `s`, or `d`.")

            until = discord.utils.utcnow() + delta
            await member.timeout(until, reason=reason)
            formatted_time = discord.utils.format_dt(until, style="f")
            
            await ctx.send_success(f"**{member.name}** has been muted until {formatted_time}!")

    @commands.hybrid_command(description="Remove timeout from a certain user", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: StriveContext, member: discord.Member, *, reason: str = "No reason provided"):
        if member == ctx.author:
            return await ctx.send_error("You cannot unmute yourself!")
    
        elif member == ctx.guild.me:
            return await ctx.send_error("I cannot unmute myself!")
        
        try:
            if member.top_role >= ctx.author.top_role:
                return await ctx.send_error("You cannot unmute a member with an equal or higher role!")
        except AttributeError:
            pass

        await member.timeout(None, reason=reason)
        await ctx.send_success(f"**{member.name}** has been unmuted!")
        
    @commands.hybrid_command(description="You can run this command to kick a user in your server.", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: StriveContext, member: discord.Member, *, reason: str = "No reason provided"):
        
        if await ModerationCommandCog.is_blacklisted_or_admin(ctx, member):
            await ctx.send_error(f"You cannot kick {member.mention} because they are an admin or bypassed from moderation.")
            
        else:
            if not ctx.guild.me.guild_permissions.manage_messages:
                await ctx.send_error("I do not have permission to manage messages.")
                return
            
            if not ctx.guild.me.guild_permissions.kick_members:
                await ctx.send_error("I do not have permission to kick members.")
                return

            try:
                await member.kick(reason=reason)
            except discord.Forbidden:
                await ctx.send_error("I do not have permission to kick that user.")
                return
            except discord.HTTPException:
                await ctx.send_error("I couldn't kick this user.")
                return

            case_id = await get_next_case_id(ctx.guild.id)

            try:
                dm_message = f"{self.strive.success} **Case #{case_id} - You have been kicked from **{ctx.guild.name}** for {reason}"
                await member.send(dm_message)
            except discord.Forbidden:
                await ctx.send_error(f"Unable to send a DM to {member.mention}; kicking the user in the server.")

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
            
            await ctx.send_success(f"**Case #{case_id} - {member}** has been kicked for {reason}.")
        
    @commands.hybrid_group(description="This is the command for case management.")
    async def case(self, ctx):
        return
    
    @case.command(description="Searches cases by an Case ID.", with_app_command=True)
    @commands.has_guild_permissions(ban_members=True)
    async def view(self, ctx: StriveContext, caseid: int):
        case_info = await cases.find_one({'case_id': caseid, 'guild_id': ctx.guild.id})
        
        if case_info:
            embed = discord.Embed(
                title=f"{case_info.get('type').title()} | Case #{case_info.get('case_id')}",
                description=f"Action took place on <t:{case_info.get('timestamp')}:F>.",
                color=self.constants.strive_embed_color_setup(),
            )

            member_value = f"<@{case_info.get('user_id')}> (`{case_info.get('user_id')}`)"
            moderator_value = f"<@{case_info.get('moderator_id')}> (`{case_info.get('moderator_id')}`)"
            reason_value = case_info.get('reason') or "No reason provided."

            if case_info.get('status') == "cleared":
                member_value = f"~~{member_value}~~"
                moderator_value = f"~~{moderator_value}~~"
                reason_value = f"~~{reason_value}~~"

            embed.add_field(
                name="Member",
                value=member_value,
                inline=True
            )
            
            embed.add_field(
                name="Moderator",
                value=moderator_value,
                inline=True
            )

            embed.add_field(
                name="Reason",
                value=reason_value,
                inline=False
            )

            try:
                member: discord.Member = await self.strive.fetch_user(case_info.get('user_id'))
                embed.set_author(name=f"@{member.name}", icon_url=member.avatar.url)
                
            except:
                embed.set_author(name="Unknown User")

            await ctx.send(embed=embed)
            
        else:
            await ctx.send_error(f"Case #{caseid} could not be found!")    
    
    
    @case.command(description="Void a case by ID", with_app_command=True)
    @commands.has_guild_permissions(ban_members=True)
    async def void(self, ctx: StriveContext, *, caseid: int):
        case_info = await cases.find_one_and_update({'case_id': caseid, 'guild_id': ctx.guild.id}, {'$set': {'status': 'cleared'}})
        
        if case_info:
            await ctx.send_success(f"**Case #{caseid}** has been voided!")
        elif not case_info:
            await ctx.send_error(f"**Case #{caseid}** could not be found!")
            
    @commands.hybrid_group(description="Allows the lookup, transferring and modification of modlogs.")
    async def modlogs(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a valid subcommand (view, transfer, clear).")

    @modlogs.command(description="View all modlogs for a certain user")
    @commands.has_guild_permissions(ban_members=True)
    async def view(self, ctx: StriveContext, member: discord.Member):
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
            await ctx.send_error("This user has no active modlogs.")
            
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
    @commands.has_guild_permissions(ban_members=True)
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
            await ctx.send_error(f"The following cases could not be updated: {', '.join(map(str, failed_cases))}")

        await ctx.send_success(f"All moderation logs for **{olduser.name}** have been transferred to **{newuser.name}**.")

    @modlogs.command(description="Clear all modlogs for a certain user")
    @commands.has_guild_permissions(ban_members=True)
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
            await ctx.send_error(f"The following cases could not be cleared: {', '.join(map(str, failed_cases))}")

        await ctx.send_success(f"All moderation logs have been cleared for **{member.name}**.")

    @commands.hybrid_command(description="View a list of banned users", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx):
        bans = [entry async for entry in ctx.guild.bans()]
        
        if not bans:
            await ctx.send_error("There are no banned users in this server.")
            return

        embed = discord.Embed(
            title="Server Ban List", 
            description=f"There are currently **{len(bans)}** banned users.\nSelect a user from the dropdown menu below to view more information.",
            color=self.constants.strive_embed_color_setup()
        )

        embed.set_footer(text="This dropdown will disable in 60 seconds")

        class BanDropdown(discord.ui.Select):
            def __init__(self, bans, msg):
                self.msg = msg
                options = [
                    discord.SelectOption(
                        label=str(ban.user),
                        value=str(ban.user.id),
                        description=f"ID: {ban.user.id}"
                    ) for ban in bans[:25]  # Discord limit of 25 options
                ]
                
                super().__init__(
                    placeholder="Select a banned user...",
                    min_values=1,
                    max_values=1,
                    options=options
                )

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("You cannot use this menu.", ephemeral=True)
                    return

                ban_list = [ban async for ban in interaction.guild.bans()]
                ban = next((ban for ban in ban_list if str(ban.user.id) == self.values[0]), None)

                if ban:
                    case = await cases.find_one({
                        'user_id': int(self.values[0]),
                        'guild_id': interaction.guild.id,
                        'type': 'ban',
                        'status': 'active'
                    })

                    embed = discord.Embed(
                        title=f"Ban Information for {ban.user}",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )

                    embed.set_footer(text="This dropdown will disable in 1 minute")
                    embed.add_field(name="User", value=f"{ban.user} (`{ban.user.id}`)", inline=False)
                    embed.add_field(name="Reason", value=ban.reason or "No reason provided", inline=False)

                    if case:
                        embed.add_field(
                            name="Additional Information",
                            value=f"**Case ID:** {case.get('case_id')}\n"
                                  f"**Moderator:** <@{case.get('moderator_id')}>\n"
                                  f"**Banned on:** <t:{case.get('timestamp')}:F>",
                            inline=False
                        )

                    try:
                        embed.set_thumbnail(url=ban.user.avatar.url)
                    except:
                        pass

                    self.placeholder = str(ban.user)
                    await interaction.response.edit_message(embed=embed, view=self.view)

        class BanView(discord.ui.View):
            def __init__(self, bans, message):
                super().__init__(timeout=60.0)
                self.add_item(BanDropdown(bans, message))

            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)

        message = await ctx.send(embed=embed)
        view = BanView(bans, message)
        view.message = message
        await message.edit(view=view)         

    @commands.hybrid_command(description="Add slowmode to a channel", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: StriveContext, duration: str = None, channel: discord.TextChannel = None):
        channel = channel or ctx.channel

        if duration is None or duration.lower() == "on":
            duration = "5s"
        elif duration.lower() == "off" or duration == "0":
            duration = "0s"

        if duration == "0s":
            try:
                await channel.edit(slowmode_delay=0)
                await ctx.send_success(f"Slowmode has been disabled in {channel.mention}.")
                return
            except discord.Forbidden:
                await ctx.send_error(f"I don't have permission to modify slowmode in {channel.mention}.")
                return

        time_mapping = {'s': 1, 'm': 60, 'h': 3600}
        try:
            amount = int(duration[:-1])
            unit = duration[-1].lower()
            
            if unit not in time_mapping:
                raise ValueError
                
            seconds = amount * time_mapping[unit]
        except (ValueError, IndexError):
            await ctx.send_error("Invalid duration format; use format like: 10s, 5m, 1h")
            return

        if seconds > 21600:  # discord's max slowmode is 6 hours
            await ctx.send_error("Slowmode cannot be longer than 6 hours (21600 seconds).")
            return

        try:
            await channel.edit(slowmode_delay=seconds)
            await ctx.send_success(f"Slowmode set to **{duration.lower()}** in {channel.mention}.")

        except discord.Forbidden:
            await ctx.send_error(f"I don't have permission to modify slowmode in {channel.mention}.")

    @commands.hybrid_command(description="Remove member's attach files & embed links permission", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def imute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        overwrite = discord.PermissionOverwrite(attach_files=False, embed_links=False)
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        await ctx.send_success(f"Removed file/embed permissions from {member.mention}")

    @commands.hybrid_command(description="Restore member's attach files & embed links permission", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def iunmute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        overwrite = discord.PermissionOverwrite(attach_files=None, embed_links=None)
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        await ctx.send_success(f"Restored file/embed permissions for {member.mention}")

    @commands.hybrid_command(description="Remove member's reaction & external emotes permission", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def rmute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        overwrite = discord.PermissionOverwrite(add_reactions=False, use_external_emojis=False)
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        await ctx.send_success(f"Removed reaction/emoji permissions from {member.mention}")

    @commands.hybrid_command(description="Restore member's reaction & external emotes permission", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(moderate_members=True)
    async def runmute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        overwrite = discord.PermissionOverwrite(add_reactions=None, use_external_emojis=None)
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        await ctx.send_success(f"Restored reaction/emoji permissions for {member.mention}")    

    @commands.hybrid_command(description="Remove dangerous roles from a user", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(administrator=True)
    async def strip(self, ctx, member: discord.Member):

        if member.top_role >= ctx.author.top_role:
            await ctx.send_error("You cannot strip roles from someone with an equal or higher role than you.")
            return

        dangerous_perms = {
            "administrator", "manage_guild", "manage_roles", "manage_channels",
            "manage_webhooks", "manage_nicknames", "manage_emojis",
            "kick_members", "ban_members", "mention_everyone"
        }

        dangerous_roles = [
            role for role in member.roles[1:]
            if any(getattr(role.permissions, perm) for perm in dangerous_perms)
        ]

        if not dangerous_roles:
            await ctx.send_error(f"No dangerous roles found on {member.mention}.")
            return

        removed_roles = []
        failed_roles = []

        for role in dangerous_roles:
            if role >= ctx.guild.me.top_role:
                failed_roles.append(role.name)
                continue
            try:
                await member.remove_roles(role, reason=f"Role strip command used by {ctx.author}")
                removed_roles.append(role.name)
            except discord.Forbidden:
                failed_roles.append(role.name)

        if removed_roles:
            await ctx.send_success(f"Removed **{len(removed_roles)}** dangerous roles from {member.mention}\n-# <:right:1332554985153626113>  {', '.join(removed_roles)}")
        else:
            await ctx.send_error(f"Failed to remove any roles from {member.mention}")

    @commands.hybrid_command(description="Lock a channel", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: StriveContext, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        
        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send_error("I don't have permission to manage channels!")
            
        current_perms = channel.overwrites_for(ctx.guild.default_role)
        if current_perms.send_messages is False:
            return await ctx.send_error(f"{channel.mention} is already locked!")
            
        current_perms.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=current_perms)
        await ctx.send_success(f"{channel.mention} has been locked!")



    @commands.hybrid_command(description="Unlock a channel", with_app_command=True, extras={"category": "Moderation"})
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: StriveContext, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        
        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send_error("I don't have permission to manage channels!")
            
        current_perms = channel.overwrites_for(ctx.guild.default_role)
        if current_perms.send_messages is not False:
            return await ctx.send_error(f"{channel.mention} is already unlocked!")
            
        current_perms.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=current_perms)
        await ctx.send_success(f"{channel.mention} has been unlocked!")
        
async def setup(strive):
    await strive.add_cog(ModerationCommandCog(strive))