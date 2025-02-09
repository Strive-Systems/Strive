import discord
import re
import time
from discord.ext import commands
from utils.constants import StriveConstants, setup_col, prefixes
from utils.embeds import SetupEmbeds, ErrorEmbed

class SetupCommandCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.constants = StriveConstants()
        self.embeds = SetupEmbeds()
        self.selected_modules = []

    @commands.hybrid_command(description="Run this command upon installation of Strive to configure and customize settings.", with_app_command=True, extras={"category": "General"})
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: commands.Context):
        try:
            welcome_embed = self.embeds.get_welcome_embed()
            view = discord.ui.View()
            continue_button = discord.ui.Button(label="Continue", style=discord.ButtonStyle.grey)

            async def continue_callback(interaction: discord.Interaction):
                if interaction.user == ctx.author:
                    await self.run_basic_settings(ctx, interaction, message=interaction.message)

            continue_button.callback = continue_callback
            view.add_item(continue_button)
            
            message = await ctx.send(embed=welcome_embed, view=view)
            
        except Exception as e:
            await ctx.send(embed=ErrorEmbed(
                title="",
                description=f"<:error:1326752911870660704> An error occurred during setup: {e}."
            ))

    async def run_basic_settings(self, ctx, interaction, message):
        class BasicSettingsModal(discord.ui.Modal, title="Strive Setup - Basic Settings"):
            prefix = discord.ui.TextInput(label="Bot Prefix", placeholder="Enter the bot's prefix", required=True)
            nickname = discord.ui.TextInput(label="Bot Nickname", placeholder="Enter the bot's nickname", required=True)
            embed_color = discord.ui.TextInput(label="Embed Color (Hex)", placeholder="#000000", required=True)

            def __init__(self, cog_instance, **kwargs):
                super().__init__(**kwargs)
                self.cog_instance = cog_instance

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    await interaction.response.defer()

                    if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.embed_color.value):
                        await interaction.followup.send("<:error:1326752911870660704> Invalid color format. Please use #RRGGBB format.", ephemeral=True)
                        return

                    await prefixes.update_one(
                        {"guild_id": ctx.guild.id},
                        {"$set": {"prefix": self.prefix.value}},
                        upsert=True
                    )

                    try:
                        await ctx.guild.me.edit(nick=self.nickname.value)
                    except discord.Forbidden:
                        await interaction.followup.send("<:error:1326752911870660704> I do not have permission to change the bot's nickname.", ephemeral=True)
                        return

                    guild_owner = ctx.guild.owner
                    settings = {
                        "GUILD_ID": ctx.guild.id,
                        "GUILD_NAME": ctx.guild.name,
                        "OWNER": {
                            "id": guild_owner.id if guild_owner else None,
                            "name": guild_owner.name if guild_owner else "Unknown"
                        },
                        "CUSTOM_WELCOME_MESSAGES": False,
                        "CUSTOM_EMBED_COLOR": self.embed_color.value,
                        "IS_PREMIUM_GUID": False,
                        "MODULES": [],
                        "TIMESTAMP": int(time.time())
                    }
                    
                    await setup_col.update_one(
                        {"GUILD_ID": ctx.guild.id},
                        {"$set": settings},
                        upsert=True
                    )

                    await self.cog_instance.run_module_selection(ctx, message)
                    
                except Exception as e:
                    await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

        await interaction.response.send_modal(BasicSettingsModal(self))

    async def run_module_selection(self, ctx, message):
        module_embed = self.embeds.get_module_selection_embed()
        view = discord.ui.View()

        modules = {
            "tickets": ("Tickets", discord.ButtonStyle.primary, self.setup_tickets),
            "logging": ("Logging", discord.ButtonStyle.secondary, self.setup_logging),
            "moderation": ("Moderation", discord.ButtonStyle.secondary, self.setup_moderation),
            "welcome": ("Welcome", discord.ButtonStyle.primary, self.setup_welcome),
            "suggestions": ("Suggestions", discord.ButtonStyle.primary, self.setup_suggestions)
        }

        for module_id, (label, style, setup_func) in modules.items():
            button = discord.ui.Button(label=label, style=style)
            
            async def make_callback(mod_id=module_id, setup=setup_func):
                async def callback(interaction: discord.Interaction):
                    if mod_id not in self.selected_modules:
                        self.selected_modules.append(mod_id)
                        await setup(ctx, interaction)
                return callback
                
            button.callback = await make_callback()
            view.add_item(button)

        done_button = discord.ui.Button(label="Finish Setup", style=discord.ButtonStyle.green)
        
        async def done_callback(interaction: discord.Interaction):
            if not self.selected_modules:
                await interaction.response.send_message("<:error:1326752911870660704> Please select at least one module!", ephemeral=True)
                return
                
            await setup_col.update_one(
                {"GUILD_ID": ctx.guild.id},
                {"$set": {"MODULES": self.selected_modules}}
            )
            
            finish_embed = discord.Embed(
                title="Setup Complete!",
                description="All selected modules have been configured successfully. Use the help command to learn more about the enabled features.",
                color=discord.Color.green()
            )
            await message.edit(embed=finish_embed, view=None)
            self.selected_modules = []

        done_button.callback = done_callback
        view.add_item(done_button)

        await message.edit(embed=module_embed, view=view)

    async def setup_logging(self, ctx, interaction):
        class LoggingSetupModal(discord.ui.Modal, title="Logging Setup"):
            log_channel = discord.ui.TextInput(
                label="Log Channel ID",
                placeholder="Enter the channel ID for logs",
                required=True
            )

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    logging_settings = {
                        "log_channel": int(self.log_channel.value)
                    }
                    
                    await setup_col.update_one(
                        {"GUILD_ID": ctx.guild.id},
                        {"$set": {"LOGGING_SETTINGS": logging_settings}}
                    )
                    
                    await interaction.response.send_message("<:success:1326752811219947571> Logging system configured successfully!", ephemeral=True)
                except ValueError:
                    await interaction.response.send_message("<:error:1326752911870660704> Please enter a valid channel ID.", ephemeral=True)

        await interaction.response.send_modal(LoggingSetupModal())

    async def setup_welcome(self, ctx, interaction):
        class WelcomeSetupModal(discord.ui.Modal, title="Welcome System Setup"):
            welcome_channel = discord.ui.TextInput(
                label="Welcome Channel ID",
                placeholder="Enter the channel ID for welcomes",
                required=True
            )
            welcome_message = discord.ui.TextInput(
                label="Welcome Message",
                placeholder="Enter your welcome message",
                required=True,
                style=discord.TextStyle.paragraph
            )

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    welcome_settings = {
                        "welcome_channel": int(self.welcome_channel.value),
                        "welcome_message": self.welcome_message.value
                    }
                    
                    await setup_col.update_one(
                        {"GUILD_ID": ctx.guild.id},
                        {"$set": {"WELCOME_SETTINGS": welcome_settings}}
                    )
                    
                    await interaction.response.send_message("<:success:1326752811219947571> Welcome system configured successfully!", ephemeral=True)
                except ValueError:
                    await interaction.response.send_message("<:error:1326752911870660704> Please enter a valid channel ID.", ephemeral=True)

        await interaction.response.send_modal(WelcomeSetupModal())

    async def setup_tickets(self, ctx, interaction):
        class TicketSetupModal(discord.ui.Modal, title="Ticket System Setup"):
            category = discord.ui.TextInput(
                label="Ticket Category ID",
                placeholder="Enter the category ID where tickets will be created",
                required=True
            )
            support_role = discord.ui.TextInput(
                label="Support Role ID",
                placeholder="Enter the support role ID",
                required=True
            )

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    ticket_settings = {
                        "ticket_category": int(self.category.value),
                        "support_role": int(self.support_role.value)
                    }
                    
                    await setup_col.update_one(
                        {"GUILD_ID": ctx.guild.id},
                        {"$set": {"TICKET_SETTINGS": ticket_settings}}
                    )
                    
                    await interaction.response.send_message("<:success:1326752811219947571> Ticket system configured successfully!", ephemeral=True)
                except ValueError:
                    await interaction.response.send_message("<:error:1326752911870660704> Please enter valid numeric IDs.", ephemeral=True)

        await interaction.response.send_modal(TicketSetupModal())

    async def setup_moderation(self, ctx, interaction):
        class ModerationSetupModal(discord.ui.Modal, title="Moderation Setup"):
            mute_role = discord.ui.TextInput(
                label="Mute Role ID",
                placeholder="Enter the mute role ID",
                required=True
            )
            mod_log_channel = discord.ui.TextInput(
                label="Mod Log Channel ID",
                placeholder="Enter the mod log channel ID",
                required=True
            )

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    moderation_settings = {
                        "mute_role": int(self.mute_role.value),
                        "mod_log_channel": int(self.mod_log_channel.value)
                    }
                    
                    await setup_col.update_one(
                        {"GUILD_ID": ctx.guild.id},
                        {"$set": {"MODERATION_SETTINGS": moderation_settings}}
                    )
                    
                    await interaction.response.send_message("<:success:1326752811219947571> Moderation system configured successfully!", ephemeral=True)
                except ValueError:
                    await interaction.response.send_message("<:error:1326752911870660704> Please enter valid numeric IDs.", ephemeral=True)

        await interaction.response.send_modal(ModerationSetupModal())

    async def setup_suggestions(self, ctx, interaction):
        class SuggestionSetupModal(discord.ui.Modal, title="Suggestion System Setup"):
            channel = discord.ui.TextInput(
                label="Suggestion Channel ID",
                placeholder="Enter the channel ID for suggestions",
                required=True
            )
            upvote_emoji = discord.ui.TextInput(
                label="Upvote Emoji",
                placeholder="Enter the upvote emoji",
                required=True
            )
            downvote_emoji = discord.ui.TextInput(
                label="Downvote Emoji",
                placeholder="Enter the downvote emoji",
                required=True
            )

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    suggestion_settings = {
                        "suggestion_channel": int(self.channel.value),
                        "upvote_emoji": self.upvote_emoji.value,
                        "downvote_emoji": self.downvote_emoji.value
                    }
                    
                    await setup_col.update_one(
                        {"GUILD_ID": ctx.guild.id},
                        {"$set": {"SUGGESTION_SETTINGS": suggestion_settings}}
                    )
                    
                    await interaction.response.send_message("<:success:1326752811219947571> Suggestion system configured successfully!", ephemeral=True)
                except ValueError:
                    await interaction.response.send_message("<:error:1326752911870660704> Please enter a valid channel ID.", ephemeral=True)

        await interaction.response.send_modal(SuggestionSetupModal())

async def setup(strive):
    await strive.add_cog(SetupCommandCog(strive))