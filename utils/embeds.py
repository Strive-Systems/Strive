import discord
import platform
from datetime import datetime
from discord import Interaction
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from utils.constants import StriveConstants
from typing import List


constants = StriveConstants()


# Success messages can use this embed by calling the class a passing correct prameters.

class SuccessEmbed(discord.Embed):
    def __init__(self, title: str, description: str, **kwargs):
        super().__init__(
            title=title, 
            description=description, 
            color=discord.Color.green(), 
            **kwargs
        )
         
         
class ErrorEmbed(discord.Embed):
    def __init__(self, title: str, description: str, **kwargs):
        super().__init__(
            title=title, 
            description=description, 
            color=discord.Color.red(), 
            **kwargs
        )
         
        
# This is the missing aguments embed, we create this embed when someone forgets a command parameter for example member or option.
# This makes it easier for users to correct their error in the command.
        
class MissingArgsEmbed(discord.Embed):
    def __init__(self, param_name):
        super().__init__(
            title="",
            description=f"<:error:1326752911870660704> Please specify a {param_name}",
            color=discord.Color.red()
        )
               

# This is the bad aguments embed, we create this embed when someone gives a bad command parameter for example member or option.
# This makes it easier for users to correct their error in the command.

class BadArgumentEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="",
            description="<:error:1326752911870660704> You provided an incorrect argument type.",
            color=discord.Color.red()
        )


# This is the forbidden error embed for when users perform forbidden actions using the bot and Discord API.

class ForbiddenEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="",
            description="<:error:1326752911870660704> I couldn't send you a DM. Please check your DM settings.",
            color=discord.Color.red()
        )


# This is the permission denied embed, this will be used for things like admin commands or places where certain roles
# can only run the command, if they dont meet those requirements this will be sent instead.

class MissingPermissionsEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="",
            description="<:error:1326752911870660704> You don't have the required permissions to run this command.",
            color=discord.Color.red()
        )


# This is the error embed, call the errors.py file as well as this file and class to pass an error

class UserErrorEmbed(discord.Embed):
    def __init__(self, error_id):
        super().__init__(
            title="Something Went Wrong",
            description=f"Please contact [Strive Support](https://discord.gg/rkRrRfRTwg) for support!\nError ID: `{error_id}`",
            color=discord.Color.red()
        )


# Developer error embed.

class DeveloperErrorEmbed(discord.Embed):
    def __init__(self, error, ctx, error_id):
        super().__init__(
            title="Something went wrong!",
            description=f'{error}',
            color=discord.Color.red()
        )
        self.add_field(name='Error ID', value=f'__{error_id}__', inline=True)
        self.add_field(name='User', value=f'{ctx.author.mention}(**{ctx.author.id}**)', inline=True)
        self.add_field(name='Server Info', value=f'{ctx.guild.name}(**{ctx.guild.id}**)', inline=True)
        self.add_field(name='Command', value=f"Name: {ctx.command.qualified_name}\nArgs: {ctx.command.params}", inline=True)
        

# This is the blacklist function for the blacklist system.

class BlacklistEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="Blacklist Notice",
            description="Your server or account is blacklisted and cannot use Strive.",
            color=discord.Color.red()
        )
        self.add_field(name="Reason", value="Please contact support [here](https://discord.gg/rkRrRfRTwg) for more details.")
                
        
# Setup Commands

class SetupEmbeds:
    def __init__(self):
        pass


    def get_welcome_embed(self):
        embed = discord.Embed(
            title="<:Strive:1330583510406267070> Welcome to Strive \n\n",
            description=(
                "> This is the setup system for <:Strive:1330583510406267070> **Strive** to configure your server and set up customization. We will walk you through setting up basic settings like prefix, embed color, and bot nickname. Then we will configure the modules and logging. \n\n"
                "**Current Configuration** \n - **Prefix:** `!` \n - **Disabled Commands:** `None`"
            ),
            color=constants.strive_embed_color_setup()
        )

        return embed


    def get_module_selection_embed(self):
        embed = discord.Embed(
            title="Module Selection",
            description="> Select the modules you'd like to enable for your server. Enabling certain modules may require additional configuration. \n\n",
            color=constants.strive_embed_color_setup()
        )
        
        embed.add_field(
            name="Available Modules",
            value="- Tickets\n- Management\n- Moderation",
            inline=False
        )
        
        embed.set_footer(text="You can enable or disable modules later via the settings menu.")
        return embed


    def get_logging_embed(self, category_name):
        embed = discord.Embed(
            title=f"Logging Setup - {category_name}",
            description=f"Select a channel to log {category_name.lower()} events.",
            color=constants.strive_embed_color_setup()
        )
        
        embed.set_footer(text="This can be updated later in the settings menu.")
        return embed


    def get_completion_embed(self):
        embed = discord.Embed(
            title="Setup Complete",
            description="Your bot setup is now complete! Here are some next steps:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Next Steps",
            value="- Use `/help` to view available commands\n"
                  "- Customize additional settings via the dashboard or commands",
            inline=False
        )
        
        embed.set_footer(text="Thank you for using Strive!")
        return embed
        
        
# This is for the new about command, edit the info for the command here instead of in the commands file.
# This allows replication late of info in the about command.

class AboutEmbed:
    @staticmethod
    def create_info_embed(uptime, guilds, users, latency, version, bot_name, bot_icon, shards, cluster, environment, command_run_time, thumbnail_url):
        embed = discord.Embed(
            description=(
                "Strive is an exceptional moderation and management tool designed specifically for community servers."
            ),
            color=discord.Color.from_str('#2a2c30')
        )


        embed.add_field(name="",value=(""),inline=False)


        embed.add_field(
            name="Strive Information",
            value=(
                f"> **Servers:** `{guilds:,}`\n"
                f"> **Users:** `{users:,}`\n"
                f"> **Uptime:** <t:{int((uptime.timestamp()))}:R>\n"
                f"> **Latency:** `{round(latency * 1000)}ms`"
            ),
            inline=True
        )


        embed.add_field(
            name="System Information",
            value=(
                f"> **Language:** `Python`\n"
                f"> **Database:** `MongoDB {version}`\n"
                f"> **Host OS:** `{platform.system()}`\n"
                f"> **Host:** `Nexure Solutions`"
            ),
            inline=True
        )
        
        
        embed.add_field(name="",value=(""),inline=False)
        
        
        embed.set_footer(
            text=f"Cluster {cluster} | Shard {shards} | {environment} • {command_run_time}"
        )


        embed.set_author(name=bot_name, icon_url=bot_icon)
        embed.set_thumbnail(url=thumbnail_url)
        return embed
    

# This passes the about pages buttons with the embed so that these do not need to be recalled.

class AboutWithButtons:
    @staticmethod
    def create_view():
        view = View()


        support_server_button = Button(
            label="Support Server", 
            style=discord.ButtonStyle.primary, 
            url="https://discord.gg/rkRrRfRTwg"
        )
        
        
        invite_button = Button(
            label="Invite Strive", 
            style=discord.ButtonStyle.link, 
            url="https://discord.com/oauth2/authorize?client_id=1328678328370204672&permissions=8&integration_type=0&scope=bot"
        )


        view.add_item(support_server_button)
        view.add_item(invite_button)


        return view
               
        
# This is the embed for the bots help center. This embed is the inital embed that shows that
# tells the user how to use the help center.

class HelpCenterEmbed(discord.Embed):
    def __init__(self, description: str, color: discord.Color = discord.Color.from_str('#dfa4ff')):
        super().__init__(
            title="Strive Help Center",
            description=description,
            color=color
        )
           
        
# This is the Nickname success embed. This will tell who was nicknamed, who nicknamed them,
# and what their previous and new name is. We do this in this file to allow it to be
# dynamic and edited once.

class NicknameSuccessEmbed(discord.Embed):
    def __init__(self, user, previous_name, new_name):
        super().__init__(
            title="Nickname Changed Successfully",
            description=(
                f"> **User**: {user.mention}\n"
                f"> **Previous Name**: ``{previous_name}``\n"
                f"> **New Name**: ``{new_name}``"
            ),
            color=discord.Color.green()
        )
          
        
# This is the server information emebed logic, this will accept things like server roles, channel counts,
# emojies, and much more. This embed will also format it like circle does. Simply call this emebed then pass
# the correct parameters. 

class ServerInformationEmbed:
    
    
    def __init__(self, guild, constants):
        self.guild = guild
        self.constants = constants



    def create_embed(self):
        
        
        # Define the predefined values
        
        owner = self.guild.owner
        member_count = self.guild.member_count
        created_at = f"<t:{int(self.guild.created_at.timestamp())}>"
        role_count = len(self.guild.roles)
        emoji_count = len(self.guild.emojis)
        text_channels = len(self.guild.text_channels)
        voice_channels = len(self.guild.voice_channels)
        announcement_channels = len([c for c in self.guild.channels if isinstance(c, discord.TextChannel) and c.is_news()])
        forum_channels = len(self.guild.forums)
        verification_level = str(self.guild.verification_level).capitalize()
        explicit_content_filter = str(self.guild.explicit_content_filter).replace('_', ' ').capitalize()
        two_factor_auth = "Enabled" if self.guild.mfa_level == 1 else "Disabled"
        boosts = self.guild.premium_subscription_count
        boost_tier = self.guild.premium_tier
        icon_url = self.guild.icon.url if self.guild.icon else None


        # Create the embed
        
        embed = discord.Embed(
            title=f"Server Info - {self.guild.name}",
            color=self.constants.strive_embed_color_setup(),
            timestamp=datetime.utcnow()
        )
        

        # Add fields to the embed
        
        embed.set_thumbnail(url=icon_url)
        embed.add_field(
            name="**Generic Information**", 
            value=f"- **Server Owner:** {owner}\n"
                  f"- **Member Count:** {member_count}\n"
                  f"- **Creation Date:** {created_at}\n"
                  f"- **Verification Level:** {verification_level}\n"
                  f"- **2FA Status:** {two_factor_auth}\n"
                  f"- **Explicit Content Filter:** {explicit_content_filter}", 
            inline=False
        )
        
        
        embed.add_field(
            name="Channels",
            value=f"> Text: {text_channels}\n > Voice: {voice_channels}\n > Announcements: {announcement_channels}\n > Forum: {forum_channels}",
            inline=False
        )


        # Roles
        
        roles_list = ', '.join([role.mention for role in self.guild.roles[1:20]])
        if role_count > 20:
            roles_list += f"... and {role_count - 20} more roles."
        embed.add_field(name=f"Roles ({role_count})", value=roles_list, inline=False)


        # Emojis
        
        emoji_list = ' '.join([str(emoji) for emoji in self.guild.emojis[:20]])
        if emoji_count > 20:
            emoji_list += f"... and {emoji_count - 20} more emojis."
        embed.add_field(name=f"Emojis ({emoji_count})", value=emoji_list, inline=False)


        # Boost info
        
        embed.add_field(name="Boosts", value=f"> {boosts} (Tier {boost_tier})", inline=False)


        return embed
    

# This is the role success emebed for when a action is performed with roles.
    
class RoleSuccessEmbed(discord.Embed):
    def __init__(self, title: str, description: str):
        super().__init__(title=title, description=description, color=discord.Color.green())
         
        
# This is the channel success emebed for when channel and category functions are used.        
        
class ChannelSuccessEmbed(discord.Embed):
    def __init__(self, title: str, description: str):
        super().__init__(title=title, description=description, color=discord.Color.green())
           

class SearchResultEmbed(discord.Embed):
    def __init__(self, title: str, description: str, case_number: int, collection: str, details: str):
        super().__init__(title=title, description=description, color=constants.strive_embed_color_setup())
        self.add_field(name="Case Number", value=case_number, inline=False)
        self.add_field(name="Collection", value=collection, inline=False)
        self.add_field(name="Details", value=details, inline=False)
           
 
# This contains the emebed and its parameters for the ping command. This shows things like uptime,
# latency to discors and mongodb.        
        
class PingCommandEmbed:
    @staticmethod
    def create_ping_embed(latency: float, database_latency: int, uptime, shard_info: List[dict], page: int = 0):
        embed = discord.Embed(
            title="<:Strive:1330583510406267070> Strive",
            color=constants.strive_embed_color_setup(),
        )
        
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1326735526740496444/1333643206226739312/StriveLogoGrey.png")
        

        if page == 0:
            embed.add_field(
                name="<:settings:1327195042602942508> **Network Information**",
                value=(
                    f"**Latency:** `{round(latency * 1000)}ms` \n"
                    f"**Database:** `{'Connected' if database_latency else 'Disconnected'}\n` "
                    f"**Uptime:** <t:{int(uptime.timestamp())}:R>"
                ),
                inline=False
            )
        else:
            embed.add_field(name="**Sharding Information**", value="", inline=False)

            start_index = (page - 1) * 5
            end_index = start_index + 5
            shards_to_display = shard_info[start_index:end_index]

            for shard in shards_to_display:
                embed.add_field(
                    name=f"<:clock:1334022552326111353> **Shard {shard['id']}**",
                    value=f"> **Latency:** `{shard['latency']}ms` \n> **Guilds:** `{shard['guilds']}`",
                    inline=False
                )

            

        return embed
      
    
# This is the embed for User Information command also known as whois. 

class UserInformationEmbed:
    def __init__(self, member, constants, strive):
        self.member = member
        self.constants = constants
        self.strive = strive
        
        

    async def fetch_guild_specific_badges(self):
        badges = []
        try:
            
            guild = self.strive.get_guild(1326476818894557217)
            guild_member = await guild.fetch_member(self.member.id)


            staff_roles = [1326488657959583745]  # Staff Role
            early_supporter_role_id = 1326781391861710899

            # Check for Strive Team role first
            if any(discord.utils.get(guild_member.roles, id=role_id) for role_id in [1326485348326314054]):
                badges.append("> <:Strive:1330583510406267070> Strive Team")

            # Check for staff roles second
            if any(discord.utils.get(guild_member.roles, id=role_id) for role_id in staff_roles):
                badges.append("> <:Strive:1330583510406267070> Strive Staff")

            # Check for Early Supporter role third
            if discord.utils.get(guild_member.roles, id=early_supporter_role_id):
                badges.append("> <:purple_heart:1329494247090421812> Early Supporter")
                
        except (discord.NotFound, discord.Forbidden):
            pass
        except Exception as e:
            print(f"Error fetching guild-specific badges: {e}")

        return badges


    def get_user_badges(self):
        flags = self.member.public_flags
        badges = []


        badge_map = {
            "hypesquad_bravery": "> <:sbHypeSquadBalanceBravery:1327111323477344379> HypeSquad Bravery",
            "hypesquad_brilliance": "> <:sbHypeSquadBalanceBrilliance:1327111453471281193> HypeSquad Brilliance",
            "hypesquad_balance": "> <:sbHypeSquadBalance:1327111176030785667> HypeSquad Balance",
            "verified_bot": "> <:sbVerified:1327112226913521695> Verified Bot",
            "early_supporter": "> <:sbDiscordStaff:1327112897884590162> Early Supporter",
            "active_developer": "> <:sbVerifiedDeveloper:1327111587139555422> Active Developer",
        }


        for flag, badge in badge_map.items():
            if getattr(flags, flag, False):
                badges.append(badge)


        return badges


    def get_permissions(self):
        permissions = [
            perm.replace("_", " ").title()
            for perm, value in self.member.guild_permissions
            if value
        ]
        return ", ".join(permissions[:5]) or "No Permissions"  # Limit to 5 permissions



    async def create_embed(self):
        try:
            
            # Basic user information
            
            user_mention = self.member.mention
            display_name = self.member.display_name
            user_id = self.member.id
            account_created = f"<t:{int(self.member.created_at.timestamp())}:F>"
            joined_server = f"<t:{int(self.member.joined_at.timestamp())}:F>" if self.member.joined_at else "N/A"
            
            
            roles = sorted(
                [role for role in self.member.roles if role.name != "@everyone"],
                key=lambda role: role.position,
                reverse=True,
            )[:5]  # Sort roles by position and limit to 5


            role_mentions = [role.mention for role in roles]
            role_count = len(role_mentions)


            # Fetch badges and permissions
            guild_badges = await self.fetch_guild_specific_badges()
            discord_badges = self.get_user_badges()
            badges = guild_badges + discord_badges
            permissions_display = self.get_permissions()


            # Create embed
            
            embed = discord.Embed(
                title=f"User Info - {display_name}",
                color=self.constants.strive_embed_color_setup(),
                timestamp=datetime.utcnow(),
            )


            embed.add_field(
                name="**User Information**",
                value=(
                    f"- **Mention:** {user_mention}\n"
                    f"- **Display Name:** {display_name}\n"
                    f"- **User ID:** {user_id}\n"
                    f"- **Account Created:** {account_created}\n"
                    f"- **Joined Server:** {joined_server}"
                ),
                inline=False,
            )
            

            embed.set_thumbnail(url=self.member.display_avatar.url)
            

            # Add badges and roles
            
            embed.add_field(name="Badges", value="\n".join(badges) if badges else "No badges", inline=False)
            
            embed.add_field(
                name=f"Roles ({role_count})",
                value=", ".join(role_mentions) if role_mentions else "No Roles",
                inline=False,
            )
            
            embed.add_field(name="Permissions", value=permissions_display, inline=False)


            if self.member.bot:
                embed.set_footer(text="This user is a bot.")


            return embed


        except Exception as e:
            print(f"Error generating embed: {e}")
            return None


class EmojiFindEmbed:
    def __init__(self, emoji):
        self.emoji = emoji
        self.constants = constants
    
    
    def create_embed(self):
        emoji_guild = self.emoji.guild
        emoji_name = self.emoji.name
        emoji_animated = self.emoji.animated
        emoji_created = self.emoji.created_at.timestamp()
        emoji_id = self.emoji.id
        emoji_url = self.emoji.url


        embed = discord.Embed(
            title="",
            description=f"**Name**\n> {emoji_name}\n\n**Id**\n> {emoji_id}\n\n**Animated**\n> {emoji_animated}\n\n**Created**\n> <t:{int(emoji_created)}:f>",
            color=self.constants.strive_embed_color_setup()
        )


        embed.set_author(name=f"{emoji_guild} emoji.", icon_url=emoji_guild.icon.url)
        embed.set_thumbnail(url=emoji_url)

        return embed    

# This is the embed for the Auto Moderation feature that gets the list of banned words from
# Mongo Db then lists it in a nice way.

class AutoModListWordsEmbed(discord.Embed):
    def __init__(self, guild_name: str, banned_words: str, color: discord.Color):
        super().__init__(title=f"Banned Words for {guild_name}", color=color)
        self.add_field(name="Banned Words", value=banned_words, inline=False)
        self.set_footer(text=f"Total words: {len(banned_words.split(', '))}")
        
        
# This is the embed that shows the current prefix for the bot.
        
class PrefixEmbed(discord.Embed):
    def __init__(self, current_prefix: str):
        super().__init__(
            title="",
            description=f"The current prefix for this server is `{current_prefix}`.",
            color=constants.strive_embed_color_setup()
        )


# This is the success embed when the bots prefix is successfully changed by the user.

class PrefixSuccessEmbed(discord.Embed):
    def __init__(self, new_prefix: str):
        super().__init__(
            title="",
            description=f"<:success:1326752811219947571> Prefix successfully changed to `{new_prefix}`.",
            color=discord.Color.green()
        )
        
        
class PrefixSuccessEmbedNoneChanged(discord.Embed):
    def __init__(self, new_prefix: str):
        super().__init__(
            title="",
            description=f"The current prefix for this server is `{new_prefix}`.",
            color=discord.Color.green()
        )
           
        
# This is the reminders success embed that shows when a reminder is successfully set.

class ReminderEmbed(discord.Embed):
    def __init__(self, reminder_time: str, **kwargs):
        super().__init__(**kwargs)


        # Set the embed title and color
        
        self.title = ""
        self.description = f"<:success:1326752811219947571> Got it! I have set a reminder. It will go off at <t:{reminder_time}:R>."
        self.color = discord.Color.green()
        

# This embed lists all the reminders in a guild.

class ReminderListEmbed:
    def __init__(self, reminders, current_page):
        self.reminders = reminders
        self.current_page = current_page
    
    
    def create_embed(self):
        embed = discord.Embed(title="Your Reminders", color=constants.strive_embed_color_setup())


        for reminder in self.reminders:
            embed.add_field(
                name=f"Reminder #{reminder['id']}",
                value=f"**Name:** `{reminder['name']}`\n**Time:** <t:{reminder['time']}:R>\n**Message:** `{reminder['message']}`",
                inline=False
            )


        return embed
        
        
# This is the Roles Information Embed that shows information about certain roles.        
        
class RolesInformationEmbed:
    
    
    @staticmethod
    def create(role: discord.Role, target):
        embed = discord.Embed(
            title=f"Role Information: {role.name}",
            color=constants.strive_embed_color_setup()
        )
        
        
        embed.add_field(name="Role ID", value=role.id, inline=False)
        embed.add_field(name="Role Color", value=str(role.color), inline=False)
        embed.add_field(name="Members", value=len(role.members), inline=False)
        embed.add_field(name="Mentionable", value=role.mentionable, inline=False)
        embed.add_field(name="Hoisted", value=role.hoist, inline=False)
        embed.add_field(name="Position", value=role.position, inline=False)
        embed.add_field(
            name="Permissions",
            value=', '.join(perm[0] for perm in role.permissions if perm[1]),
            inline=False
        )


        if isinstance(target, discord.Interaction):
            return embed
        else:
            embed.set_footer(text=f"Requested by {target.author}", icon_url=target.author.avatar.url)
            return embed
