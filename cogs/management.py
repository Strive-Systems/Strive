import discord
import uuid
import time
import re
import asyncio
from typing import List, Literal
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from utils.utils import get_next_case_id, get_next_reminder_id, StriveContext
from utils.constants import StriveConstants, reminders, afks, notes, socials
from utils.embeds import (
    UserInformationEmbed,
    ReminderEmbed,
    RoleSuccessEmbed,
    RolesInformationEmbed,
    SuccessEmbed,
    ErrorEmbed,
    NicknameSuccessEmbed,
    ReminderListEmbed,
)
from utils.pagination import ReminderPaginationView


constants = StriveConstants()


class SocialLinksButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Social Links",
            style=discord.ButtonStyle.gray,
            custom_id=f"social_links_{user_id}",
            emoji="<:striveLink:1338900764474609757>",
        )
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        try:
            social_links = await socials.find_one({"user_id": self.user_id})
            if not social_links or not social_links.get("platforms"):
                await interaction.response.send_message(
                    "This user has no social links.", ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Social Links",
                description="",
                color=interaction.client.base_color,
            )

            if social_links and "platforms" in social_links:
                for platform, username in social_links["platforms"].items():
                    if platform == "instagram":
                        link = f"https://instagram.com/{username}"
                    elif platform == "snapchat":
                        link = f"https://snapchat.com/add/{username}"
                    elif platform == "twitter":
                        link = f"https://x.com/{username}"
                    embed.add_field(name=platform.title(), value=link, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", ephemeral=True
            )
            print(f"Error in social links callback: {str(e)}")


SocialPlatformType = Literal["twitter", "instagram", "snapchat"]


class ManagementCommandCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.constants = StriveConstants()
        self.mongo_db = None
        self.check_for_reminders.start()
        self.cooldown = 2
        self.bot = strive

    @tasks.loop(minutes=1)
    async def check_for_reminders(self):
        current_time = int(datetime.utcnow().timestamp())

        async for reminder in reminders.find({"time": {"$lte": current_time}}):
            user = self.strive.get_user(reminder["user_id"])
            guild = self.strive.get_guild(reminder["guild_id"])

            if user:
                guild_name = guild.name if guild else "Unknown Server"
                reminder_time = f"<t:{reminder['time']}:F>"

                message = (
                    f"<:clock:1338811480451055719> On {reminder_time}, you told me to remind you:\n"
                    f"> **Message:** {reminder['message']}\n"
                    f"> **Guild:** {guild_name}"
                )

                await user.send(content=message)

            await reminders.delete_one({"_id": reminder["_id"]})

    @commands.hybrid_group(
        description="Manage reminders.",
        with_app_command=True,
        extras={"category": "General"},
    )
    async def reminder(self, ctx: StriveContext):

        if ctx.invoked_subcommand is None:
            await ctx.send("Available subcommands: `add`, `list`, `remove`")

    @reminder.command(
        name="add", description="Create a reminder.", with_app_command=True
    )
    async def add(self, ctx: StriveContext, name: str, time: str, message: str):
        try:
            minutes = self.time_converter(time)
            newtime = int((datetime.utcnow() + timedelta(minutes=minutes)).timestamp())
        except ValueError as e:
            return await ctx.send(
                embed=discord.Embed(
                    title="Invalid time", description=str(e), color=discord.Color.red()
                )
            )

        case_id = await get_next_reminder_id(ctx.guild.id)

        data = {
            "id": str(case_id),
            "user_id": ctx.author.id,
            "guild_id": ctx.guild.id,
            "name": name,
            "message": message,
            "time": newtime,
        }

        await reminders.insert_one(data)

        reminder_embed = ReminderListEmbed([data], current_page=0)
        await ctx.send(embed=reminder_embed.create_embed())

    @reminder.command(
        name="list", description="List your reminders.", with_app_command=True
    )
    async def list(self, ctx: StriveContext):
        user_reminders = reminders.find({"user_id": ctx.author.id})
        reminders_list = await user_reminders.to_list(None)

        if len(reminders_list) == 0:

            await ctx.send_warning("You have no reminders.")

        view = ReminderPaginationView(ctx.bot, reminders_list)
        embed = ReminderListEmbed(reminders_list[:5], 1).create_embed()

        await ctx.send(embed=embed, view=view)

    @reminder.command(
        name="remove", description="Remove a reminder by ID.", with_app_command=True
    )
    async def remove(self, ctx: StriveContext, reminder_id: str):

        result = reminders.delete_one({"id": reminder_id, "user_id": ctx.author.id})
        if result.deleted_count == 0:

            await ctx.send_warning("Reminder not found.")

        await ctx.send_success(f"Reminder with ID `{reminder_id}` has been removed.")

    @staticmethod
    def time_converter(parameter: str) -> int:

        time_units = {"s": 1 / 60, "m": 1, "h": 60, "d": 1440, "w": 10080}
        match = re.fullmatch(r"(\d+)([smhdw])", parameter.lower())

        if not match:
            raise ValueError("Invalid time format. Use '1m', '2h', '1d', etc.")

        value, unit = match.groups()
        return int(value) * time_units[unit]

    @commands.hybrid_command(
        description="Show all information about a certain user.",
        aliases=["w", "ui"],
        with_app_command=True,
        extras={"category": "General"},
    )
    async def whois(self, ctx, member: discord.User = None):
        if member is None:
            member = ctx.author

        try:
            fetched_member: discord.Member = await ctx.guild.fetch_member(member.id)
        except discord.NotFound:
            fetched_member = member

        embed = await UserInformationEmbed(
            fetched_member, self.constants, self.strive
        ).create_embed()

        social_links = await socials.find_one({"user_id": fetched_member.id})
        view = None
        if social_links and social_links.get("platforms"):
            view = discord.ui.View()
            view.add_item(SocialLinksButton(fetched_member.id))

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_group(
        name="social",
        description="Manage your social media links",
        extras={"category": "General"},
    )
    async def social(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_error("Please specify a subcommand: add, remove, list")

    @social.command(
        name="add",
        description="Add a social media link",
        extras={"category": "General"},
    )
    async def social_add(
        self, ctx: StriveContext, platform: SocialPlatformType, username: str
    ):
        result = await socials.update_one(
            {"user_id": ctx.author.id},
            {"$set": {f"platforms.{platform}": username}},
            upsert=True,
        )

        if platform == "instagram":
            link = f"https://instagram.com/{username}"
        elif platform == "snapchat":
            link = f"https://snapchat.com/add/{username}"
        elif platform == "twitter":
            link = f"https://x.com/{username}"

        await ctx.send_success(
            f"Added your [**{platform}**]({link}) link successfully!"
        )

    @social.command(
        name="remove",
        description="Remove a social media link",
        extras={"category": "General"},
    )
    async def social_remove(self, ctx: StriveContext, platform: SocialPlatformType):
        result = await socials.update_one(
            {"user_id": ctx.author.id}, {"$unset": {f"platforms.{platform}": ""}}
        )

        if result.modified_count > 0:
            await ctx.send_success(f"Removed your {platform} link successfully!")
        else:
            await ctx.send_error(f"You don't have a {platform} link saved.")

    @social.command(
        name="list",
        description="List your social media links",
        extras={"category": "General"},
    )
    async def social_list(self, ctx: StriveContext):
        social_links = await socials.find_one({"user_id": ctx.author.id})

        if not social_links or not social_links.get("platforms"):
            await ctx.send_warning("You have no social links saved.")
            return

        embed = discord.Embed(title="Your Social Links", color=ctx.strive.base_color)

        for platform, username in social_links["platforms"].items():
            if platform == "instagram":
                link = f"https://instagram.com/{username}"
            elif platform == "snapchat":
                link = f"https://snapchat.com/add/{username}"
            elif platform == "twitter":
                link = f"https://x.com/{username}"
            embed.add_field(name=platform.title(), value=link, inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_group(
        description="Allows you to change user roles with Strive.",
        with_app_command=True,
    )
    async def role(self, ctx: StriveContext):
        return

    @role.command(
        description="Allows server administrators to delete a role.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def delete(self, ctx: StriveContext, role: discord.Role):
        await role.delete(reason=f"Deleted by {ctx.author}")
        await ctx.send_success(f"Deleted {role.mention}")

    @role.command(
        description="Allows server administrators to add a role.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def create(self, ctx: StriveContext, *, role_name: str):
        new_role = await ctx.guild.create_role(
            name=role_name, reason=f"Created by {ctx.author}"
        )
        await ctx.send_success(f"Created {new_role.mention}")

    @role.command(
        description="Allows server administrators to assign a role.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def add(self, ctx: StriveContext, member: discord.Member, role: discord.Role):
        await member.add_roles(role, reason=f"Assigned by {ctx.author}")
        await ctx.send_success(f"Added {role.mention} to {member.mention}")

    @role.command(
        description="Allows server administrators to unassign a role.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def remove(
        self, ctx: StriveContext, member: discord.Member, role: discord.Role
    ):
        await member.remove_roles(role, reason=f"Unassigned by {ctx.author}")
        await ctx.send_success(f"Removed {role.mention} from {member.mention}")

    @role.command(
        description="Shows information about a specific role.",
        with_app_command=True,
        extras={"category": "Setup"},
    )
    async def info(self, ctx: commands.Context, role: discord.Role):
        embed = RolesInformationEmbed(role, constants).create()
        await ctx.send(embed=embed)

    @role.command(
        description="Add a role to all human members in the server.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def humans_add(self, ctx: StriveContext, role: discord.Role):
        dangerous_perms = [
            "administrator",
            "manage_guild",
            "manage_roles",
            "manage_channels",
            "manage_webhooks",
            "manage_nicknames",
            "manage_emojis",
            "ban_members",
            "kick_members",
        ]

        has_dangerous_perms = any(
            getattr(role.permissions, perm) for perm in dangerous_perms
        )
        if has_dangerous_perms and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "Only the server owner can add roles with dangerous permissions!"
            )

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "You cannot add a role that is higher than or equal to your highest role!"
            )
        if role >= ctx.guild.me.top_role:
            return await ctx.send_error(
                "I cannot add a role that is higher than my highest role!"
            )

        await ctx.guild.chunk()
        humans = [m for m in ctx.guild.members if not m.bot]

        estimated_time = (len(humans) // 10 + 1) * 2
        msg = await ctx.send_loading(
            f"Adding {role.mention} to `{len(humans)}` humans, this will roughly take **{estimated_time}** seconds"
        )

        for i in range(0, len(humans), 10):
            for member in humans[i : i + 10]:
                await member.add_roles(role, reason=f"Mass role add by {ctx.author}")
            await asyncio.sleep(2)

        await msg.delete()
        await ctx.send_success(f"Added {role.mention} to `{len(humans)}` humans.")

    @role.command(
        description="Remove a role to all human members in the server.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def humans_remove(self, ctx: StriveContext, role: discord.Role):
        dangerous_perms = [
            "administrator",
            "manage_guild",
            "manage_roles",
            "manage_channels",
            "manage_webhooks",
            "manage_nicknames",
            "manage_emojis",
            "ban_members",
            "kick_members",
        ]

        has_dangerous_perms = any(
            getattr(role.permissions, perm) for perm in dangerous_perms
        )
        if has_dangerous_perms and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "Only the server owner can remove roles with dangerous permissions!"
            )

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "You cannot remove a role that is higher than or equal to your highest role!"
            )
        if role >= ctx.guild.me.top_role:
            return await ctx.send_error(
                "I cannot remove a role that is higher than my highest role!"
            )

        await ctx.guild.chunk()
        humans = [m for m in ctx.guild.members if not m.bot]

        estimated_time = (len(humans) // 10 + 1) * 2
        msg = await ctx.send_loading(
            f"Removing {role.mention} to `{len(humans)}` humans, this will roughly take **{estimated_time}** seconds"
        )

        for i in range(0, len(humans), 10):
            for member in humans[i : i + 10]:
                await member.remove_roles(
                    role, reason=f"Mass role remove by {ctx.author}"
                )
            await asyncio.sleep(2)

        await msg.delete()
        await ctx.send_success(f"Removed {role.mention} from `{len(humans)}` humans.")

    @role.command(
        description="Add a role to all bot members in the server.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def bots(self, ctx: StriveContext, role: discord.Role):
        dangerous_perms = [
            "administrator",
            "manage_guild",
            "manage_roles",
            "manage_channels",
            "manage_webhooks",
            "manage_nicknames",
            "manage_emojis",
            "ban_members",
            "kick_members",
        ]

        has_dangerous_perms = any(
            getattr(role.permissions, perm) for perm in dangerous_perms
        )
        if has_dangerous_perms and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "Only the server owner can add roles with dangerous permissions!"
            )

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "You cannot add a role that is higher than or equal to your highest role!"
            )
        if role >= ctx.guild.me.top_role:
            return await ctx.send_error(
                "I cannot add a role that is higher than my highest role!"
            )

        await ctx.guild.chunk()
        bots = [m for m in ctx.guild.members if m.bot]

        estimated_time = (len(bots) // 10 + 1) * 2
        msg = await ctx.send_loading(
            f"Adding {role.mention} to `{len(bots)}` bots, this will roughly take **{estimated_time}** seconds"
        )

        for i in range(0, len(bots), 10):
            for member in bots[i : i + 10]:
                await member.add_roles(role, reason=f"Mass role add by {ctx.author}")
            await asyncio.sleep(2)

        await msg.delete()
        await ctx.send_success(f"Added {role.mention} to `{len(bots)}` bots.")

    @role.command(
        description="Add a role to all members in the server.",
        with_app_command=True,
        extras={"category": "Administration"},
    )
    @commands.has_permissions(manage_roles=True)
    async def all(self, ctx: StriveContext, role: discord.Role):
        dangerous_perms = [
            "administrator",
            "manage_guild",
            "manage_roles",
            "manage_channels",
            "manage_webhooks",
            "manage_nicknames",
            "manage_emojis",
            "ban_members",
            "kick_members",
        ]

        has_dangerous_perms = any(
            getattr(role.permissions, perm) for perm in dangerous_perms
        )
        if has_dangerous_perms and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "Only the server owner can add roles with dangerous permissions!"
            )

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send_error(
                "You cannot add a role that is higher than or equal to your highest role!"
            )
        if role >= ctx.guild.me.top_role:
            return await ctx.send_error(
                "I cannot add a role that is higher than my highest role!"
            )

        await ctx.guild.chunk()
        members = ctx.guild.members

        estimated_time = (len(members) // 10 + 1) * 2
        msg = await ctx.send_loading(
            f"Adding {role.mention} to `{len(members)}` members, this will roughly take **{estimated_time}** seconds"
        )

        for i in range(0, len(members), 10):
            for member in members[i : i + 10]:
                await member.add_roles(role, reason=f"Mass role add by {ctx.author}")
            await asyncio.sleep(2)

        await msg.delete()
        await ctx.send_success(f"Added {role.mention} to `{len(members)}` members.")

    # Purge command to purge user messages from discord channels.

    @commands.hybrid_command(
        name="purge",
        description="Clear a large number of messages from the current channel.",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def purge(
        self, ctx, option: str = None, limit: int = None, *, user: discord.User = None
    ):
        if hasattr(ctx, "interaction") and ctx.interaction is not None:
            await ctx.interaction.response.defer()

        if option is not None and option.isdigit():
            limit = int(option)
            option = "any"

        if option is None and limit is not None:
            option = "any"

        if limit is None or limit < 1:
            await ctx.send_error(
                "Please specify a valid number of messages to delete (greater than 0)."
            )
            return

        option = option.lower()

        if option == "any":
            deleted = await ctx.channel.purge(limit=limit)
            embed = SuccessEmbed(
                title="Messages Cleared",
                description=f"{self.strive.success} Cleared {len(deleted)} messages from this channel.",
            )

        elif option == "bots":
            deleted = await ctx.channel.purge(limit=limit, check=lambda m: m.author.bot)
            embed = SuccessEmbed(
                title="Bot Messages Cleared",
                description=f"{self.strive.success} Cleared {len(deleted)} bot messages from this channel.",
            )

        elif option == "user":
            if user is None:
                await ctx.send_error("Please specify a user to purge messages from.")
                return
            deleted = await ctx.channel.purge(
                limit=limit, check=lambda m: m.author.id == user.id
            )
            embed = SuccessEmbed(
                title="User Messages Cleared",
                description=f"{self.strive.success} Cleared {len(deleted)} messages from {user.mention}.",
            )

        elif option == "strive":
            deleted = await ctx.channel.purge(
                limit=limit, check=lambda m: m.author.id == self.strive.user.id
            )
            embed = SuccessEmbed(
                title="Strive Messages Cleared",
                description=f"{self.strive.success} Cleared {len(deleted)} messages from Strive.",
            )

        else:
            await ctx.send_error(
                "Please specify a valid option: any, bots, user, or strive."
            )
            return

        await ctx.send(embed=embed, delete_after=5)

    # These are the cog error handlers they determine how the error is sent.

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send_error(
                f"This command is on cooldown; please try again <t:{int(discord.utils.utcnow().timestamp() + error.retry_after)}:R>"
            )

    @commands.hybrid_group(
        name="members",
        description="Lists the amount of members a role is assigned to. You can pass specific_role to run the command.",
        with_app_command=True,
        extras={"category": "General"},
    )
    async def members(self, ctx):
        pass

    @members.command(
        name="specific_role",
        description="Lists the amount of members a role is assigned to.",
        with_app_command=True,
    )
    async def specific_role(self, ctx, *, role: discord.Role):

        if not role:
            await ctx.send_error("Please specify a role to check.")

        await ctx.guild.chunk()
        members_with_role = [
            member for member in ctx.guild.members if role in member.roles
        ]

        if not members_with_role:
            await ctx.send_error(f"No members have the role `{role.name}`.")

        embed = discord.Embed(
            title=f"Members with the role `{role.name}`",
            description=f"{len(members_with_role)} members have this role",
            color=constants.strive_embed_color_setup(),
        )

        member_list = "\n".join(
            [
                f"**{member.display_name}** (`{member.id}`)"
                for member in members_with_role
            ]
        )

        embed.add_field(name="", value=member_list, inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        description="This lists the servers members",
        with_app_command=True,
        extras={"category": "General"},
    )
    async def membercount(self, ctx: StriveContext):
        guild = ctx.guild

        if not guild.chunked:
            await guild.chunk()

        member_count = guild.member_count
        server_boosts = guild.premium_subscription_count

        # online_members = []
        # for member in guild.members:
        #     print(member.status)
        # return

        # online_members = len([member for member in guild.members if member.status != discord.Status.offline])
        server_icon_url = guild.icon.url if guild.icon else None
        server_name = guild.name

        embed = discord.Embed(
            description="", color=constants.strive_embed_color_setup()
        )

        if server_icon_url:
            embed.set_author(name=server_name, icon_url=server_icon_url)

        embed.add_field(name="Member Count", value=member_count, inline=True)

        # embed.add_field(
        #     name="Online Members",
        #     value=online_members,
        #     inline=True
        # )

        embed.add_field(name="Server Boosts", value=server_boosts, inline=True)

        await ctx.send(embed=embed)

    @commands.hybrid_group(description="Set your AFK status with an optional reason.")
    async def afk(self, ctx: StriveContext, *, message: str = "none"):
        afk_data = await afks.find_one({"user_id": ctx.author.id})

        if not afk_data:
            afk_doc = {
                "user_id": ctx.author.id,
                "guild_id": ctx.guild.id,
                "message": message,
                "timestamp": int(time.time()),
            }

            await afks.insert_one(afk_doc)

            afk_doc_2 = {"user_id": ctx.author.id, "guild_id": ctx.guild.id}

            self.strive.afk_users.append(afk_doc_2)

            await ctx.send_success(f"You are now AFK: {message}")

        elif afk_data:
            await ctx.send_error(f"You are already AFK!")

    @afk.group(name="mod", description="Group of a group")
    async def afk_mod(self, ctx: StriveContext):
        return

    @afk_mod.command(
        name="list", description="List all AFK's in this server", with_app_command=True
    )
    async def afk_list(self, ctx: StriveContext):
        all_afks = afks.find({"guild_id": ctx.guild.id})
        number = 0
        embed = discord.Embed(
            title="Current AFK's",
            description="",
            color=self.constants.strive_embed_color_setup(),
        )

        async for afk in all_afks:
            number += 1
            embed.add_field(
                name=f"AFK Number: {number}",
                value=f"User: <@{afk.get('user_id')}>\nMessage: {afk.get('message')}",
                inline=False,
            )

        if number == 0:
            embed = discord.Embed(
                description=f"{self.strive.error} No AFK logs could be found for this server!",
                color=self.constants.strive_embed_color_setup(),
            )
        else:
            embed.set_footer(
                text=f"Moderator ID: {ctx.author.id} • Total AFK's: {number}"
            )

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        afk_data = self.strive.afk_users

        afk_key = {"user_id": message.author.id, "guild_id": message.guild.id}
        if afk_key in afk_data:
            result = await afks.find_one(
                {"user_id": message.author.id, "guild_id": message.guild.id}
            )
            afk_timestamp = result.get("timestamp", int(time.time()))
            duration = int(time.time()) - afk_timestamp

            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60

            duration_str = (
                f"{hours}h {minutes}m {seconds}s"
                if hours > 0
                else f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            )

            await afks.delete_one(
                {"user_id": message.author.id, "guild_id": message.guild.id}
            )

            embed = discord.Embed(
                title="",
                description=f"{self.strive.success} Your AFK has ended as you sent a message indicating your return.\n> You were AFK for: {duration_str}",
                color=self.strive.base_color,
            )

            await message.reply(embed=embed)

            self.strive.afk_users.remove(afk_key)
            return

        if message.mentions:
            for user in message.mentions:
                afk_key = {"user_id": user.id, "guild_id": message.guild.id}
                if afk_key in afk_data:
                    result = await afks.find_one(
                        {"user_id": user.id, "guild_id": message.guild.id}
                    )

                    afk_timestamp = result.get("timestamp", int(time.time()))
                    formatted_time = f"<t:{afk_timestamp}:F>"

                    duration = int(time.time()) - afk_timestamp
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60

                    duration_str = (
                        f"{hours}h {minutes}m {seconds}s"
                        if hours > 0
                        else f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
                    )

                    await message.channel.send(
                        f"**<:clock:1338811480451055719> {user} is currently AFK because:** {result.get('message')}.\n"
                        f"-# They have been AFK for {duration_str} (since {formatted_time})."
                    )

    @commands.hybrid_group(
        description="Allows users to manage threads", with_app_command=True
    )
    async def thread(self, ctx: StriveContext):
        return

    @thread.command(
        name="close",
        description="Close a thread channel",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(manage_threads=True)
    async def close(self, ctx: StriveContext, thread: discord.TextChannel = None):
        thread = thread or ctx.channel

        if not isinstance(thread, discord.Thread):
            return await ctx.send_error(
                "This command can only be used in thread channels!"
            )
        await ctx.send_loading(f"This thread will be closed in 5 seconds.")
        await asyncio.sleep(5)
        await thread.delete()

    @thread.command(
        name="lock",
        description="Lock a thread channel",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(manage_threads=True)
    async def lock(self, ctx: StriveContext, thread: discord.TextChannel = None):
        thread = thread or ctx.channel

        if not isinstance(thread, discord.Thread):
            return await ctx.send_error(
                "This command can only be used in thread channels!"
            )

        await thread.edit(locked=True)
        await ctx.send_success(f"Thread {thread.mention} has been locked.")

    @thread.command(
        name="unlock",
        description="Unlock a thread channel",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(manage_threads=True)
    async def unlock(self, ctx: StriveContext, thread: discord.TextChannel = None):
        thread = thread or ctx.channel

        if not isinstance(thread, discord.Thread):
            return await ctx.send_error(
                "This command can only be used in thread channels!"
            )

        await thread.edit(locked=False)
        await ctx.send_success(f"Thread {thread.mention} has been unlocked.")

    @thread.command(
        name="rename",
        description="Rename a thread channel",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(manage_threads=True)
    async def rename(
        self, ctx: StriveContext, new_name: str, thread: discord.TextChannel = None
    ):
        thread = thread or ctx.channel

        if not isinstance(thread, discord.Thread):
            return await ctx.send_error(
                "This command can only be used in thread channels!"
            )

        old_name = thread.name
        await thread.edit(name=new_name)
        await ctx.send_success(f"Thread renamed from `{old_name}` to `{new_name}`")

    @thread.command(
        name="remove",
        description="Remove a member from the thread",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(manage_threads=True)
    async def remove(self, ctx: StriveContext, member: discord.User):
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send_error(
                "This command can only be used in thread channels!"
            )

        if member not in ctx.channel.members:
            return await ctx.send_error(f"{member.mention} is not in this thread!")

        await ctx.channel.remove_user(member)
        await ctx.send_success(f"Removed {member.mention} from {ctx.channel.mention}")

    @thread.command(
        name="add",
        description="Add a member to the thread",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(manage_threads=True)
    async def add(self, ctx: StriveContext, member: discord.User):
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.send_error(
                "This command can only be used in thread channels!"
            )

        if member in ctx.channel.members:
            return await ctx.send_error(f"{member.mention} is already in this thread!")

        try:
            await ctx.channel.add_user(member)
            await ctx.send_success(f"Added {member.mention} to {ctx.channel.mention}")
        except discord.Forbidden:
            await ctx.send_error(
                "I don't have permission to add members to this thread!"
            )
        except discord.HTTPException:
            await ctx.send_error(
                "Failed to add member to the thread; please try again later."
            )

    @commands.hybrid_group(
        description="Allows modification of user notes.", with_app_command=True
    )
    async def note(self, ctx: StriveContext):
        return

    @note.command(
        description="Adds a moderator note to a user.",
        with_app_command=True,
        extras={"category": "Moderation"},
    )
    @commands.has_guild_permissions(ban_members=True)
    async def add(self, ctx: StriveContext, member: discord.Member, reason):
        note_id = await get_next_case_id(ctx.guild.id)

        note_entry = {
            "note_id": note_id,
            "guild_id": ctx.guild.id,
            "guild_name": ctx.guild.name,
            "noted_user_id": member.id,
            "noted_user_name": str(member),
            "noted_by_id": ctx.author.id,
            "noted_by_name": str(ctx.author),
            "note": reason,
            "timestamp": ctx.message.created_at.isoformat(),
        }

        await notes.insert_one(note_entry)

        await ctx.send_success(f"**{note_id}** has been logged for {member}.")

    @note.command(
        description="Delete a note on a user",
        with_app_command=True,
        extras={"category": "Moderation"},
    )
    @commands.has_guild_permissions(ban_members=True)
    async def remove(self, ctx: StriveContext, id):
        await notes.delete_one({"note_id": f"Note #{id}"})

        await ctx.send_success(f"**Note #{id}** has been removed.")

    @note.command(
        description="Search for a note on a user",
        with_app_command=True,
        extras={"category": "Moderation"},
    )
    @commands.has_guild_permissions(ban_members=True)
    async def search(self, ctx: StriveContext, id):
        result = await notes.find_one({"note_id": f"{id}"})

        if result:
            user_id = result.get("noted_user_id", "N/A")
            user_name = result.get("noted_user_name", "N/A")
            mod_id = result.get("noted_by_id", "N/A")
            mod_name = result.get("noted_by_name", "N/A")

            note = result.get("note", "No note provided")

            embed = discord.Embed(
                title=f"Notes | Note #{id}", color=constants.strive_embed_color_setup()
            )

            embed.add_field(
                name="Member", value=f"<@{user_id}> ({user_id})", inline=True
            )
            embed.add_field(
                name="Moderator", value=f"<@{mod_id}> ({mod_id})", inline=True
            )
            embed.add_field(name="Note", value=note, inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send_error(f"No note found with the ID {id}.")

    # This is the command that you can use to nickname users. You can enter the user you want to nickname
    # followed by the new name. To clear a nickname you can do m-nick @User followed by no new name.
    # You can also use User IDs instead of pinging the user.

    @commands.hybrid_command(
        description="Allows you to nickname a user in a server to whatever you want.",
        with_app_command=True,
        extras={"category": "General"},
    )
    @commands.has_permissions(administrator=True)
    async def nick(self, ctx, member: discord.Member, *, nickname: str = None):

        previous_nickname = member.display_name

        await member.edit(nick=nickname if nickname else None)

        embed = NicknameSuccessEmbed(
            user=member,
            previous_name=previous_nickname,
            new_name=nickname if nickname else "Cleared",
        )

        await ctx.send(embed=embed)


async def setup(strive):
    await strive.add_cog(ManagementCommandCog(strive))
