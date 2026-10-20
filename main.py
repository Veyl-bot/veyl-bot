import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

# --- CONFIGURATION (ROLE & USER IDs) ---
TOKEN = "MTU2MTk0NjYwNjk1NjMxODgxMQ.G8owW_.XailE2y6mBbL-IQpTizWbbbr46pJg1wb_9FpGA"
COUNTING_CHANNEL_ID = 1509825283522297886

# Role IDs
CLAN_MEMBER_ROLE_ID = 1509850816171741266
TRYOUT_STAFF_ROLE_IDS = [1535534125686063114, 1554476673167130775, 1554689265290715207, 1552940558719389726]
MOD_WAR_MENTION_TEXT = "<@1548620631971463209> <@1501121839219478652> <@&1509843380883165184> <@&1550185272065659051>"
TRYOUT_MENTION_TEXT = "<@&1535534125686063114> <@&1554476673167130775> <@&1554689265290715207> <@&1552940558719389726>"

# Setup Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class VeylBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("⚡ Veyl Slash Commands successfully synced globally!")

bot = VeylBot()

# Global Storage
afk_users = {}       # {user_id: reason}
counting_state = {"current": 0, "last_user": None}

@bot.event
async def on_ready():
    print(f"🎃 {bot.user.name} is online and operational for Veyl!")
    await bot.change_presence(activity=discord.Game(name="Roblox Rivals | Veyl Clan 🎃"))

# ==========================================
# 1. 🎟️ TICKET SYSTEM DROPDOWN & PANELS
# ==========================================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Clan War Ticket", description="Arrange or discuss clan wars", emoji="⚔️"),
            discord.SelectOption(label="Mod Application", description="Apply for staff / moderator positions", emoji="🛡️"),
            discord.SelectOption(label="Tryout Application", description="Request a tryout for Veyl Clan", emoji="🎯"),
            discord.SelectOption(label="Roster Application", description="Apply for the competitive main/sub roster", emoji="🏆"),
            discord.SelectOption(label="Tryouter Application", description="Apply to become an official Veyl tryouter", emoji="🎓")
        ]
        super().__init__(placeholder="Choose a ticket type to open...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        choice = self.values[0]
        
        # Permissions setup for ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Select ping group & title based on ticket type
        if choice in ["Tryout Application", "Roster Application", "Tryouter Application"]:
            ping_text = TRYOUT_MENTION_TEXT
            color = 0xff7700
        else:  # Mod Application & Clan War
            ping_text = MOD_WAR_MENTION_TEXT
            color = 0x8800ff

        clean_title = choice.lower().replace(" ", "-")
        channel_name = f"{clean_title}-{interaction.user.name}"
        ticket_chan = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        embed = discord.Embed(
            title=f"🎃 VEYL TICKET: {choice.upper()}",
            description=f"Welcome {interaction.user.mention}!\n\nThank you for opening a **{choice}** ticket. Please state your **Roblox Username**, **Rivals Level/Stats**, and details or clips below.\n\nAssigned Staff will be with you shortly!",
            color=color
        )
        embed.set_footer(text="Veyl Clan Ticket System")

        await ticket_chan.send(content=f"{interaction.user.mention} | {ping_text}", embed=embed)
        await interaction.response.send_message(f"✅ Your ticket has been created in {ticket_chan.mention}!", ephemeral=True)

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@bot.tree.command(name="setup_tickets", description="Deploy the Veyl Ticket System Selection Panel")
@app_commands.default_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎃 VEYL MANAGEMENT & TRYOUT HUB 🎃",
        description=(
            "Select an option from the menu below to open a private ticket channel:\n\n"
            "⚔️ **Clan War Ticket** — Arrange matches with staff\n"
            "🛡️ **Mod Application** — Apply for Veyl Staff\n"
            "🎯 **Tryout Application** — Request a Clan Tryout\n"
            "🏆 **Roster Application** — Apply for Competitive Roster\n"
            "🎓 **Tryouter Application** — Apply to become a Tryouter"
        ),
        color=0x8800ff
    )
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("Ticket panel deployed successfully!", ephemeral=True)

# ==========================================
# 2. 🏷️ STRICT ROLE GIVER, AFK & COUNTING HANDLER
# ==========================================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    # --- TRYOUT ROLE ASSIGNMENT HANDLER ---
    # Trigger format: "Give role @user clan member role" sent by authorized Tryouter/Roster staff
    msg_content = message.content.lower()
    if "give role" in msg_content and "clan member role" in msg_content:
        # Check if the sender has one of the authorized Tryout Staff roles
        author_role_ids = [role.id for role in message.author.roles]
        has_permission = any(role_id in author_role_ids for role_id in TRYOUT_STAFF_ROLE_IDS)

        if has_permission:
            # Check for user mentions in message
            if message.mentions:
                target_user = message.mentions[0]
                role_to_give = message.guild.get_role(CLAN_MEMBER_ROLE_ID)

                if role_to_give:
                    await target_user.add_roles(role_to_give)
                    await message.channel.send(f"🎉 **{target_user.mention}** has passed their tryout and received the **{role_to_give.name}** role!")
                else:
                    await message.channel.send("❌ Error: Could not find Clan Member role in server settings.")
            else:
                await message.channel.send("⚠️ Please tag the user you want to give the role to! Example: `Give role @user clan member role`.")
        else:
            await message.channel.send("❌ You do not have permission to give the Clan Member role.")

    # --- NON-RESETTING COUNTING CHANNEL ---
    if message.channel.id == COUNTING_CHANNEL_ID:
        try:
            num = int(message.content.strip())
            expected = counting_state["current"] + 1

            if message.author.id == counting_state["last_user"]:
                await message.add_reaction("❌")
                await message.channel.send(f"⚠️ {message.author.mention}, you cannot count twice in a row! Next number is **{expected}**.")
            elif num == expected:
                counting_state["current"] = expected
                counting_state["last_user"] = message.author.id
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")
                await message.channel.send(f"❌ Wrong number {message.author.mention}! Count stays at **{counting_state['current']}**. Next number is **{expected}**.")
        except ValueError:
            pass

    # --- AFK RETURN & MENTION NOTIFIER ---
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"👋 Welcome back {message.author.mention}, I removed your AFK status!", delete_after=5)

    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"💤 **{mention.display_name}** is currently AFK: *{afk_users[mention.id]}*")

    # --- CHAT ENGAGEMENT ---
    if "hello veyl" in msg_content or "hi veyl" in msg_content:
        await message.channel.send(f"👋 Hey {message.author.mention}! Welcome to Veyl general chat! 🎃")
    elif "veyl on top" in msg_content:
        await message.channel.send("⚡ **VEYL ALWAYS ON TOP!** ⚡")

    await bot.process_commands(message)

# ==========================================
# 3. 🚀 SERVER BOOSTER AUTO-WELCOME
# ==========================================
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.premium_since is None and after.premium_since is not None:
        embed = discord.Embed(
            title="🚀 NEW SERVER BOOST! 🚀",
            description=f"Thank you so much {after.mention} for boosting **Veyl**! You have unlocked VIP Perks!",
            color=0xf47fff
        )
        embed.set_thumbnail(url=after.display_avatar.url)
        target_chan = after.guild.system_channel or after.guild.text_channels[0]
        await target_chan.send(embed=embed)

# ==========================================
# 4. ⚔️ CLAN WARS, TOURNAMENTS & GIVEAWAYS
# ==========================================
@bot.tree.command(name="clanwar", description="Arrange a Clan War match")
@app_commands.describe(opponent="Opponent Clan Name", date="Match Date/Time", format="Team size e.g. 3v3 or 5v5")
async def clanwar(interaction: discord.Interaction, opponent: str, date: str, format: str):
    embed = discord.Embed(
        title="⚔️ VEYL CLAN WAR MATCH ANNOUNCEMENT ⚔️",
        description=f"**Opponent:** {opponent}\n**Format:** {format}\n**Date & Time:** {date}\n\nReact below to state your roster availability!",
        color=0xff0000
    )
    embed.set_footer(text="Veyl Competitive Roster")
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

@bot.tree.command(name="tournament", description="Generate a 4-team Tournament Bracket")
@app_commands.describe(team1="Team 1", team2="Team 2", team3="Team 3", team4="Team 4")
async def tournament(interaction: discord.Interaction, team1: str, team2: str, team3: str, team4: str):
    embed = discord.Embed(
        title="🏆 VEYL TOURNAMENT BRACKET 🏆",
        description=f"**Semi-Finals:**\n🥊 Match A: `{team1}` vs `{team2}`\n🥊 Match B: `{team3}` vs `{team4}`\n\n**Grand Finals:**\n👑 Winner Match A vs Winner Match B",
        color=0xffd700
    )
    await interaction.response.send_message(embed=embed)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entries = []

    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.success, custom_id="enter_giveaway")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entries:
            await interaction.response.send_message("⚠️ You have already entered this giveaway!", ephemeral=True)
        else:
            self.entries.append(interaction.user.id)
            await interaction.response.send_message("✅ You are entered into the giveaway! Good luck!", ephemeral=True)

@bot.tree.command(name="giveaway", description="Host a giveaway in the server")
@app_commands.describe(prize="Prize Name", duration_seconds="Duration in seconds")
async def giveaway(interaction: discord.Interaction, prize: str, duration_seconds: int):
    view = GiveawayView()
    embed = discord.Embed(
        title="🎁 VEYL OFFICIAL GIVEAWAY 🎁",
        description=f"**Prize:** {prize}\n**Hosted By:** {interaction.user.mention}\n\nClick the **🎉 Enter Giveaway** button below to participate!",
        color=0x00ff77
    )
    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(duration_seconds)

    if not view.entries:
        await interaction.channel.send(f"🎁 Giveaway for **{prize}** ended, but nobody entered!")
    else:
        winner_id = random.choice(view.entries)
        await interaction.channel.send(f"🎉 **CONGRATULATIONS <@{winner_id}>!** You won the **{prize}**!")

# ==========================================
# 5. 📋 ROSTER SETUP, AFK & MINIGAMES
# ==========================================
@bot.tree.command(name="afk", description="Set your AFK status")
@app_commands.describe(reason="Reason for going AFK")
async def afk(interaction: discord.Interaction, reason: str = "AFK"):
    afk_users[interaction.user.id] = reason
    await interaction.response.send_message(f"💤 {interaction.user.mention}, your AFK status is set: *{reason}*")

@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 **Coinflip Result:** {random.choice(['Heads 🪙', 'Tails 🪙'])}")

@bot.tree.command(name="roll", description="Roll a 6-sided die")
async def roll(interaction: discord.Interaction):
    await interaction.response.send_message(f"🎲 You rolled a **{random.randint(1, 6)}**!")

# --- RUN BOT ---
bot.run(TOKEN)
      
