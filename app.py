import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import time

class MinecraftStatusBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix='!', intents=intents)
        self.status_message = None
        self.server_channels = {}
        self.next_update_time = time.time() + 30

    async def on_ready(self):
        print(f'Bot已連線：{self.user}')
        self.check_server_status.start()

    def create_server_embed(self, server_statuses):
        embed = discord.Embed(
            title="🌐 Allenpixel 伺服器狀態",
            description="目前各分流連線狀態",
            color=discord.Color.green() if all(status['online'] for status in server_statuses) else discord.Color.red()
        )
        
        for status in server_statuses:
            status_text = "🟢 線上" if status['online'] else "🔴 離線"
            ping_text = f"{status['ping']}ms" if status['online'] else "N/A"
            player_count_text = f"{status['players_online']}/{status['players_max']}" if status['online'] else "N/A"
            
            embed.add_field(
                name=status['name'], 
                value=f"狀態：{status_text}\n延遲：{ping_text}\n玩家人數：{player_count_text}", 
                inline=False
            )
        
        current_time = int(time.time())
        next_update = current_time + 30
        
        embed.add_field(
            name="下次更新",
            value=f"<t:{next_update}:R>",
            inline=False
        )
        
        return embed

    def ping_server(self, host, port):
        try:
            server = JavaServer.lookup(f"{host}:{port}")
            status = server.status()
            return {
                "online": True,
                "ping": round(status.latency),
                "players_online": status.players.online,
                "players_max": status.players.max
            }
        except Exception:
            return {
                "online": False,
                "ping": 0,
                "players_online": 0,
                "players_max": 0
            }

    @tasks.loop(seconds=30)
    async def check_server_status(self):
        self.next_update_time = time.time() + 30
        server_statuses = []
        servers = [
            {"name": "節點伺服器", "host": "localhost", "port": 25565},
            {"name": "分流1", "host": "localhost", "port": 25566},
            {"name": "分流2", "host": "localhost", "port": 25567},
            {"name": "分流3", "host": "localhost", "port": 25568}
        ]

        total_players_online = 0
        total_players_max = 0

        for server_info in servers:
            status = self.ping_server(server_info['host'], server_info['port'])
            status['name'] = server_info['name']
            server_statuses.append(status)
            if status['online']:
                total_players_online += status['players_online']
                total_players_max += status['players_max']

        # 如果是 BungeeCord 伺服器，顯示總玩家人數
        if total_players_max > 0:
            server_statuses.append({
                "name": "總玩家人數",
                "online": True,
                "ping": "N/A",
                "players_online": total_players_online,
                "players_max": total_players_max
            })

        embed = self.create_server_embed(server_statuses)

        for channel_id in self.server_channels.values():
            channel = self.get_channel(channel_id)
            if channel:
                try:
                    if self.status_message is None:
                        self.status_message = await channel.send(embed=embed)
                    else:
                        await self.status_message.edit(embed=embed)
                except discord.errors.HTTPException as e:
                    print(f"更新訊息時發生錯誤：{e}")
                    self.status_message = await channel.send(embed=embed)

    @commands.command(name='pingserver')
    async def force_server_check(self, ctx):
        self.check_server_status.restart()
        await ctx.send("已強制檢查伺服器狀態並重置計時器")

    @check_server_status.before_loop
    async def before_check_server_status(self):
        await self.wait_until_ready()

    def set_status_channel(self, channel_id):
        self.server_channels['default'] = channel_id

    async def close(self):
        if self.status_message:
            try:
                await self.status_message.delete()
                print("已刪除狀態訊息")
            except Exception as e:
                print(f"刪除訊息時發生錯誤：{e}")
        await super().close()

def main():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = MinecraftStatusBot(intents)
    
    bot.set_status_channel(YOUR_CHANNEL_ID)
    bot.run('YOUR_BOT_TOKEN')

if __name__ == "__main__":
    main()
