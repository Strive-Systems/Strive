import discord
from discord.ext import commands
from discord.ui import View, Button
from utils.constants import StriveConstants, setup_col
from utils.utils import StriveContext


constants = StriveConstants()


class OnMemberJoin(commands.Cog):
    def __init__(self, strive: commands.Bot):
        self.strive = strive


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = member.guild.id
        guild_settings = await setup_col.find_one({"GUILD_ID": guild_id})


        if not guild_settings:
            print(f"No settings found for guild {guild_id}")
            return



        if not guild_settings.get("CUSTOM_WELCOME_MESSAGES", False):
            print("Custom welcome messages are disabled.")
            return



        welcome_channel_id = guild_settings.get("WELCOME_SETTINGS", {}).get("welcome_channel")


        if not welcome_channel_id:
            print("No welcome channel set.")
            return


        welcome_channel = member.guild.get_channel(welcome_channel_id)

        if not welcome_channel:
            print(f"Could not find channel with ID {welcome_channel_id}")
            return
        
        
        role_name = "Member"
        role = discord.utils.get(member.guild.roles, name=role_name)
        
        
        if role:
            try:
                await member.add_roles(role)
                print(f"Assigned {role_name} role to {member}")
            except discord.Forbidden:
                print("Bot does not have permission to assign roles.")
            except Exception as e:
                print(f"Error assigning role: {e}")
        else:
            print(f"Role {role_name} not found in guild {guild_id}")


        view = View()
        guild = self.strive.get_guild(1338770040820072523)


        try:
            guild_member = await guild.fetch_member(member.id)
            staff_roles = [1326488657959583745]


            for role_id in staff_roles:
                if discord.utils.get(guild_member.roles, id=role_id):
                    view = View().add_item(
                        Button(
                            label="Strive Staff",
                            emoji="<:Strive:1338783953598939157>",
                            disabled=True,
                            style=discord.ButtonStyle.grey,
                        )
                    )
                    break
                
                
        except discord.NotFound:
            print("Member not found.")
        except discord.Forbidden:
            print("Bot does not have permission to fetch this member.")
        except Exception as e:
            print(f"Error running the role check: {e}")


        member_count = member.guild.member_count
        welcome_message = f"<:wave:1326749927405129818> {member.mention} Welcome to <:Strive:1338783953598939157> **{member.guild.name}**! Feel free to explore. 🎉"


        view.add_item(
            Button(
                label=f"Members: {member_count}",
                disabled=True,
                emoji="<:striveUsers:1337248026942509129>",
                style=discord.ButtonStyle.grey,
            )
        )

        await welcome_channel.send(welcome_message, view=view)



async def setup(strive):
    await strive.add_cog(OnMemberJoin(strive))

