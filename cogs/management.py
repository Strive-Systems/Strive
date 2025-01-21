import discord
import uuid
import time
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from utils.utils import get_next_case_id
from utils.constants import StriveConstants, reminders, afks, notes
from utils.embeds import UserInformationEmbed, ReminderEmbed, RoleSuccessEmbed, RolesInformationEmbed, SuccessEmbed, ErrorEmbed, AfkEmbed, NicknameSuccessEmbed


constants = StriveConstants()


class ManagementCommandCog(commands.Cog):
    def __init__(self, strive):
        self.strive = strive
        self.constants = StriveConstants()
        self.mongo_db = None
        self.check_for_reminders.start()
        self.cooldown = 2



    @tasks.loop(minutes=1)
    async def check_for_reminders(self):
        async for reminder in reminders.find({}):
            if reminder["time"] == datetime.now().strftime('%Y-%m-%d %H:%M'):
                print("Reminder went off.")
                await self.strive.get_user(reminder["user_id"]).send("Your reminder went off :)")
                reminders.delete_one(reminder)
        



    @commands.hybrid_command(description="This will create a reminder.", with_app_command=True, extras={"category": "General"})
    async def addreminder(self, ctx: commands.Context, name:str, time:str, message:str):
        try:
            newtime = self.time_converter(datetime.now().strftime('%Y-%m-%d %H:%M'),time)
        except ValueError:
            return await ctx.send(embed=discord.Embed(
                title="Invalid time",
                description="You provided a invalid time.",
                color=discord.Color.red()
            ))

        
        data = {
            "id": str(uuid.uuid4().int)[:4],
            "user_id": ctx.author.id,
            "name": name,
            "message": message,
            "time": newtime
        }

        reminders.insert_one(data)

        reminder_embed = ReminderEmbed(reminder_time=newtime)

        await ctx.send(embed=reminder_embed)
        
    

    def time_converter(self, current_date: str, parameter: str) -> int:
        conversions = {
            ("s", "seconds"): 1,
            ("m", "minutes"): 60,
            ("h", "hours"): 60 * 60,
            ("d", "days"): 24 * 60 * 60,
            ("w", "weeks"): 7 * 24 * 60 * 60
        }

        current_date = datetime.strptime(current_date, '%Y-%m-%d %H:%M')
        parameter = parameter.strip()
        
        for aliases, multiplier in conversions.items():
            for alias in aliases:
                if parameter.lower().endswith(alias.lower()):
                    number_part = parameter[:-len(alias)].strip()
                    
                    if number_part.isdigit():
                        time_to_add = int(number_part) * multiplier
                        new_date = current_date + timedelta(seconds=time_to_add)
                        return new_date.strftime('%Y-%m-%d %H:%M')
                    else:
                        raise ValueError(f"Invalid number: {number_part}")

        raise ValueError(f"Invalid time format: {parameter}")



    @commands.hybrid_command(description="Show all information about a certain user.", aliases=["w"], with_app_command=True, extras={"category": "General"})
    async def whois(self, ctx, member: discord.User = None):

        if member is None:
            member = ctx.author
        
        try:
            fetched_member: discord.Member = await ctx.guild.fetch_member(member.id)
        except discord.NotFound:
            fetched_member = member

        embed = await UserInformationEmbed(fetched_member, self.constants, self.strive).create_embed()

        await ctx.send(embed=embed)
        
        
    
    @commands.hybrid_group(description='Allows you to change user roles with Strive.', with_app_command=True)
    async def role(self, ctx: commands.Context):
        return
    
    

    @role.command(description="Allows server administrators to delete a role.", with_app_command=True, extras={"category": "Administration"})
    @commands.has_permissions(manage_roles=True)
    async def delete(self, ctx: commands.Context, role: discord.Role):
        await role.delete(reason=f"Deleted by {ctx.author}")
        embed = RoleSuccessEmbed(title="", description=f"<:success:1326752811219947571> Role {role.mention} has been deleted.")
        await ctx.send(embed=embed)



    @role.command(description="Allows server administrators to add a role.", with_app_command=True, extras={"category": "Administration"})
    @commands.has_permissions(manage_roles=True)
    async def create(self, ctx: commands.Context, *, role_name: str):
        new_role = await ctx.guild.create_role(name=role_name, reason=f"Created by {ctx.author}")
        embed = RoleSuccessEmbed(title="", description=f"<:success:1326752811219947571> Role {new_role.name} has been created.")
        await ctx.send(embed=embed)



    @role.command(description="Allows server administrators to assign a role.", with_app_command=True, extras={"category": "Administration"})
    @commands.has_permissions(manage_roles=True)
    async def add(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        await member.add_roles(role, reason=f"Assigned by {ctx.author}")
        embed = RoleSuccessEmbed(title="", description=f"<:success:1326752811219947571> Role {role.mention} has been assigned to {member.mention}.")
        await ctx.send(embed=embed)



    @role.command(description="Allows server administrators to unassign a role.", with_app_command=True, extras={"category": "Administration"})
    @commands.has_permissions(manage_roles=True)
    async def remove(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        await member.remove_roles(role, reason=f"Unassigned by {ctx.author}")
        embed = RoleSuccessEmbed(title="", description=f"<:success:1326752811219947571> Role {role.mention} has been removed from {member.mention}.")
        await ctx.send(embed=embed)
        
        
        
    @role.command(description="Shows information about a specific role.", with_app_command=True, extras={"category": "Setup"})
    async def info(self, target, role: discord.Role):
        embed = RolesInformationEmbed.create(role, target)

        if isinstance(target, discord.Interaction):
            await target.response.send_message(embed=embed)
        else:
            await target.send(embed=embed)
            
            
            
    # Purge command to purge user messages from discord channels.
    
    @commands.hybrid_command(name="purge", description="Clear a large number of messages from the current channel.", with_app_command=True, extras={"category": "General"})
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def purge(self, ctx, option: str = None, limit: int = None, *, user: discord.User = None):
        if hasattr(ctx, "interaction") and ctx.interaction is not None:
            await ctx.interaction.response.defer()


        if option is not None and option.isdigit():
            limit = int(option)
            option = "any"
        


        if option is None and limit is not None:
            option = "any"
        


        if limit is None or limit < 1:
            await ctx.send("Please specify a valid number of messages to delete (greater than 0).")
            return


        option = option.lower()
        

        if option == "any":
            deleted = await ctx.channel.purge(limit=limit)
            embed = SuccessEmbed(
                title="Messages Cleared",
                description=f"<:success:1326752811219947571> Cleared {len(deleted)} messages from this channel."
            )


        elif option == "bots":
            deleted = await ctx.channel.purge(limit=limit, check=lambda m: m.author.bot)
            embed = SuccessEmbed(
                title="Bot Messages Cleared",
                description=f"<:success:1326752811219947571> Cleared {len(deleted)} bot messages from this channel."
            )


        elif option == "user":
            if user is None:
                await ctx.send("Please specify a user to purge messages from.")
                return
            deleted = await ctx.channel.purge(limit=limit, check=lambda m: m.author.id == user.id)
            embed = SuccessEmbed(
                title="User Messages Cleared",
                description=f"<:success:1326752811219947571> Cleared {len(deleted)} messages from {user.mention}."
            )


        elif option == "strive":
            deleted = await ctx.channel.purge(limit=limit, check=lambda m: m.author.id == self.strive.user.id)
            embed = SuccessEmbed(
                title="Strive Messages Cleared",
                description=f"<:success:1326752811219947571> Cleared {len(deleted)} messages from Strive."
            )


        else:
            await ctx.send("Please specify a valid option: any, bots, user, or strive.")
            return


        await ctx.send(embed=embed, delete_after=5)
    
    
    
    # These are the cog error handlers they determine how the error is sent.
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="Cooldown",
                description=f"You are running the command too fast! Please wait {self.cooldown} seconds before using this command again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        
        
        
    @commands.hybrid_command(description="Lists the amount of members a role is assigned to. You can pass specific_role to run the command.", with_app_command=True, extras={"category": "General"})
    async def members(self, ctx, *, specific_role: discord.Role):

        if not specific_role:
            await ctx.send("Role not found.")
            return
        

        await ctx.guild.chunk()
        members_with_role = [member for member in ctx.guild.members if specific_role in member.roles]
        
        
        if not members_with_role:
            await ctx.send(f"No members have the role {specific_role.name}.")
            return
        
        
        embed = discord.Embed(
            title=f"Members with the role `{specific_role.name}`",
            description=f"{len(members_with_role)} members have this role",
            color=constants.strive_embed_color_setup()
        )

        
        member_list = "\n".join([f"**{member.display_name}** (`{member.id}`)" for member in members_with_role])


        embed.add_field(
            name="",
            value=member_list,
            inline=False
        )

        
        await ctx.send(embed=embed)
        
        
        
    @commands.hybrid_command(description="This lists the servers members", with_app_command=True, extras={"category": "General"})
    async def membercount(self, ctx: commands.Context):
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
            description="",
            color=constants.strive_embed_color_setup()
        )
        
        if server_icon_url:
            embed.set_author(name=server_name, icon_url=server_icon_url)

        embed.add_field(
            name="Member Count",
            value=member_count,
            inline=True
        )
        
        # embed.add_field(
        #     name="Online Members",
        #     value=online_members,
        #     inline=True
        # )
        
        embed.add_field(
            name="Server Boosts",
            value=server_boosts,
            inline=True
        )
        
        await ctx.send(embed=embed)
        
        
        
    @commands.hybrid_group(description="Set your AFK status with an optional reason.")
    async def afk(self, ctx: commands.Context):
        return
    
    
    
    @afk.group(name='mod', description="Group of a group")
    async def afk_mod(self, ctx: commands.Context):
        return
        
        
        
    @afk.command(name='set', description="Set yourself as AFK.", with_app_command=True)
    async def afk_set(self, ctx: commands.Context, *, message: str = "none"):
        afk_data = await afks.find_one({"user_id": ctx.author.id})
        
        if not afk_data:
            afk_doc = {
                'user_id': ctx.author.id,
                'guild_id': ctx.guild.id,
                'message': message,
                'timestamp': int(time.time())
            }
            
            
            await afks.insert_one(afk_doc)


            afk_doc_2 = {
                'user_id': ctx.author.id,
                'guild_id': ctx.guild.id
            }
            
            
            self.strive.afk_users.append(afk_doc_2)
            
            
            await ctx.send(embed=SuccessEmbed(
                title="",
                description=f"<:success:1326752811219947571> I set your AFK: `{message}`!"
            ))


        elif afk_data:
            await ctx.send(embed=ErrorEmbed(
                title="",
                description="<:error:1326752911870660704> You are already AFK."
            ))



    @afk.command(name="return", description="Return from your AFK")
    async def afk_return(self, ctx: commands.Context):
        afk_data = await afks.find_one({"user_id": ctx.author.id})
        
        
        if afk_data:
            await afks.delete_one({"user_id": ctx.author.id})


            for item in self.strive.afk_users:
                if item['user_id'] == ctx.author.id and item['guild_id'] == ctx.guild.id:
                    self.strive.afk_users.remove(item)
                    break


            await ctx.send(embed=SuccessEmbed(
                title="",
                description="<:success:1326752811219947571> You are now back online!"
            ))
            
            
        else:
            await ctx.send(embed=ErrorEmbed(
                title="",
                description="<:error:1326752911870660704> You are not AFK."
            ))
    
    
    
    @afk_mod.command(name='mod_return', description="Force an AFK return", with_app_command=True)
    async def afk_return_mod(self, ctx: commands.Context, member: discord.Member, *, reason: str = "None"):
        afk_data = await afks.find_one_and_delete({"user_id": ctx.author.id})
        
        if afk_data:
            await member.edit(nick=None)


            for item in self.strive.afk_users:
                if item['user_id'] == member.id and item['guild_id'] == ctx.guild.id:
                    self.strive.afk_users.remove(item)
                    break
                
                
            await ctx.send(embed=SuccessEmbed(
                title="",
                description=f"<:success:1326752811219947571> **{member.name}**'s AFK has been ended!"
            ))
            
            
            await member.send(f"<:success:1326752811219947571> Your AFK has been ended in **{ctx.guild.name}** by **{ctx.author.mention}** for reason: {reason}")
        
        
        else:
            await ctx.send("I could not find an AFK for this person!")
    
    
    
    @afk_mod.command(name='list', description="List all AFK's in this server", with_app_command=True)
    async def afk_list(self, ctx: commands.Context):
        all_afks = afks.find({"guild_id": ctx.guild.id})
        number = 0
        embed = discord.Embed(title="Current AFK's", description="", color=self.constants.strive_embed_color_setup())


        async for afk in all_afks:
            number += 1
            embed.add_field(name=f"AFK Number: {number}", value=f"User: <@{afk.get('user_id')}>\nMessage: {afk.get('message')}", inline=False)
        
        
        if number == 0:
            embed = discord.Embed(title="Not Found", description="No AFK logs could be found for this server!", color=self.constants.strive_embed_color_setup())
        else:
            embed.set_footer(text=f"Moderator ID: {ctx.author.id} • Total AFK's: {number}")
        
        
        await ctx.send(embed=embed)



    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return


        afk_data = self.strive.afk_users


        afk_key = {'user_id': message.author.id, 'guild_id': message.guild.id}
        if afk_key in afk_data:
            
            await afks.delete_one({"user_id": message.author.id, 'guild_id': message.guild.id})
            
            
            embed = SuccessEmbed(
                title="",
                description="<:success:1326752811219947571> Your AFK has ended as you sent a message indicating your return."
            )
                
            await message.channel.send(embed=embed)
            
            
            self.strive.afk_users.remove(afk_key)
            return


        if message.mentions:
            for user in message.mentions:
                afk_key = {'user_id': user.id, 'guild_id': message.guild.id}
                if afk_key in afk_data:
                    result = await afks.find_one({'user_id': user.id, 'guild_id': message.guild.id})
                    await message.channel.send(embed=AfkEmbed(user, result.get('message')))
                    
                    
                    
    @commands.hybrid_group(description='Allows modification of user notes.', with_app_command=True)
    async def note(self, ctx: commands.Context):
        return
    
    @note.command(description="Adds a moderator note to a user.", with_app_command=True, extras={"category": "Moderation"})
    async def add(self, ctx: commands.Context, member: discord.Member, reason):        
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
            "timestamp": ctx.message.created_at.isoformat() 
        }

        await notes.insert_one(note_entry)

        await ctx.send(f"<:success:1326752811219947571> **{note_id}** has been logged for {member}.")



    @note.command(description="Delete a note on a user", with_app_command=True, extras={"category": "Moderation"})
    async def remove(self, ctx: commands.Context, id):
        await notes.delete_one({"note_id": f"Note #{id}"})

        await ctx.send(f"<:success:1326752811219947571> **Note #{id}** has been removed.")



    @note.command(description="Search for a note on a user", with_app_command=True, extras={"category": "Moderation"})
    async def search(self, ctx: commands.Context, id):
        result = await notes.find_one({"note_id": f"{id}"})

        if result:
            user_id = result.get('noted_user_id', 'N/A')
            user_name = result.get('noted_user_name', 'N/A')
            mod_id = result.get('noted_by_id', 'N/A')
            mod_name = result.get('noted_by_name', 'N/A')

            note = result.get('note', 'No note provided')

            embed = discord.Embed(
                title=f"Notes | Note #{id}",
                color=constants.strive_embed_color_setup()
            )

            embed.add_field(name="Member", value=f"<@{user_id}> ({user_id})", inline=True)
            embed.add_field(name="Moderator", value=f"<@{mod_id}> ({mod_id})", inline=True)
            embed.add_field(name="Note", value=note, inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"<:error:1326752911870660704> No note found with the ID {id}.")
        
        
        
    # This is the command that you can use to nickname users. You can enter the user you want to nickname
    # followed by the new name. To clear a nickname you can do m-nick @User followed by no new name.
    # You can also use User IDs instead of pinging the user.

    @commands.hybrid_command(description="Allows you to nickname a user in a server to whatever you want.", with_app_command=True, extras={"category": "General"})
    @commands.has_permissions(administrator=True)
    async def nick(self, ctx, member: discord.Member, *, nickname: str = None):


        previous_nickname = member.display_name


        await member.edit(nick=nickname if nickname else None)

        embed = NicknameSuccessEmbed(
            user=member,
            previous_name=previous_nickname,
            new_name=nickname if nickname else "Cleared"
        )
        
        await ctx.send(embed=embed)
        
        
    
async def setup(strive):
    await strive.add_cog(ManagementCommandCog(strive))