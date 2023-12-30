import discord
import os
from dotenv import load_dotenv
import json
import datetime
from discord.ext import tasks, commands
import requests
from embed import create_embed, add_field

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


def call_api():
    return requests.get(f'https://www.nytimes.com/svc/wordle/v2/{datetime.date.today().strftime("%Y-%m-%d")}.json').json()

def read_database():
    with open('database.json', 'r') as database:
        data = None
        if (os.path.isfile(os.getcwd() + '\\database.json')) and (os.path.getsize(os.getcwd() + '\\database.json') > 0):
            data = json.load(database)
        else:
            data = {}
        
        if not(data):
            data = {}
    return data

def read_stats():
    with open('stats.json', 'r') as database:
        data = None
        if (os.path.isfile(os.getcwd() + '\\stats.json')) and (os.path.getsize(os.getcwd() + '\\stats.json') > 0):
            data = json.load(database)
        else:
            data = {}
        
        if not(data):
            data = {}
    return data


class MyCog(commands.Cog):
    def __init__(self):
        self.wordle_answer = {
            'id': None,
            'solution': None,
            'print_date': None,
            'days_since_launch': None,
            'editor': None,
        }
        self.newest_day = None
        self.api_call.start()
        self.checker.start()

    def cog_unload(self):
        self.checker.cancel()
        self.api_call.cancel()
    
    def today_wordle(self):
        data = read_database()

        today = {}

        for player in data.keys():
            if player in data and str(self.wordle_answer['days_since_launch']) in (data[player]).keys():
                wordle = data[player][str(self.wordle_answer['days_since_launch'])]
                ratio = int(wordle['ratio'].split('/')[0])
                if ratio in today:
                    today[ratio].append((player, wordle))
                else:
                    today[ratio] = [(player, wordle)]
        
        return today
    
    def best_answer(self, today: dict):
        minimum = min(today.keys())
        return today[minimum]

        
    def worst_answer(self, today: dict):
        maximum = max(today.keys())
        return today[maximum]

    def weekly_average(self):
        last_seven = [i for i in range(int(self.wordle_answer['days_since_launch']), int(self.wordle_answer['days_since_launch']) - 7, -1)]
        data = read_database()
        
        averages = {}
        for user in data.keys():
            for day in last_seven:
                if str(day) in data[user].keys():
                    day = str(day)
                    if user in averages:
                        averages[user][0] += int(data[user][day]['ratio'].split('/')[0])
                        averages[user][1] += 1
                    else:
                        averages[user] = [int(data[user][day]['ratio'].split('/')[0]), 1]
        result = []
        for user in averages.keys():
            result.append((user, averages[user][0] / averages[user][1]))
        
        result.sort(key=lambda a: a[1])

        stats_data = read_stats()

        if 'weekly' in stats_data:
            stats_data['weekly'][str(self.wordle_answer['days_since_launch'])] = {'winner': result[0], 'loser': result[1]}
        else:
            stats_data['weekly'] = {str(self.wordle_answer['days_since_launch']): {'winner': result[0], 'loser': result[1]}}
        with open('stats.json', 'w') as stats_database:
            json.dump(stats_data, stats_database, indent=4)
        
        return result

    def daily_average(self):
        # Determine the gorup's daily average
        average = [0, 0]

        data = read_database()
        for user in data.keys():
            if str(self.wordle_answer['days_since_launch']) in data[user].keys():
                average[0] += int(data[user][str(self.wordle_answer['days_since_launch'])]['ratio'].split('/')[0])
                average[1] += 1
        
        stats_data = read_stats()

        if 'daily_group_average' in stats_data:
            stats_data['daily_group_average'][str(self.wordle_answer['days_since_launch'])] = {
                'total': average[1],
                'average': average[0]
            }
        else:
            stats_data['daily_group_average'] = {str(self.wordle_answer['days_since_launch']): {
                'total': average[1],
                'average': average[0]
            }}
        with open('stats.json', 'w') as stats_database:
            json.dump(stats_data, stats_database, indent=4)
        
        return average

    @tasks.loop(seconds=45.0)
    async def checker(self):
        hour, minute = datetime.datetime.now().strftime("%H %M").split(" ")
        if hour == 11 and (minute == 58 or minute == 59) and self.newest_day != self.wordle_answer['days_since_launch']:
        # if hour == "02" and (minute == "00" or minute == "01") and self.newest_day != self.wordle_answer['days_since_launch']:
            self.newest_day = self.wordle_answer['days_since_launch']
        else:
            return
        
        embed = create_embed('Wordle Recap', f'**#{self.wordle_answer["days_since_launch"]}** *{self.wordle_answer["solution"]}* - {self.wordle_answer["print_date"]}', 'orange')
        
        guild = await client.fetch_guild(int(os.getenv('server')))
        channel = await guild.fetch_channel(int(os.getenv('channel_id')))
        
        today = self.today_wordle()
        best_answer = self.best_answer(today)
        worst_answer = self.worst_answer(today)

        if len(best_answer) == 1:
            best_answer = best_answer[0]
            result = f'<@{best_answer[0]}> with **{best_answer[1]["ratio"]}**:'
            for s in best_answer[1]['board']:
                print('s', s)
                result += "\n" + s
            add_field(embed, f'Winner!', result, True)

        if len(worst_answer) == 1:
            worst_answer = worst_answer[0]
            result = f'<@{worst_answer[0]}> with **{worst_answer[1]["ratio"]}**:'
            for s in worst_answer[1]['board']:
                result += "\n" + s
            add_field(embed, f'Loser (just kidding)!', result, True)

        # Weekly Average
        averages = self.weekly_average()
        if len(averages) != 0:
            averages_string = f'<@{averages[0][0]}>: {averages[0][1]}/6'
            for avg in range(1, len(averages), 1):
                averages_string += '\n'
                averages_string += f'<@{averages[avg][0]}>: {averages[avg][1]}/6'
        add_field(embed, f'Weekly Averages', averages_string, False)

        # Daily Average
        daily_average = self.daily_average()
        if len(daily_average) == 2:
            add_field(embed, f"Group's Daily Average", f"{daily_average[0]/daily_average[1]}/6", True)

        await channel.send(embed=embed)

    @tasks.loop(hours=1)
    async def api_call(self):
        if int(datetime.datetime.now().strftime("%H")) == 11:
            return
        self.wordle_answer = call_api()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    cog = MyCog()

@client.event
async def on_message(message):
    print('message.aut')
    if message.author == client.user:
        return

    if not(message.content.startswith("Wordle")):
        return
    
    msg = message.content.split('\n')
    date, ratio = msg[0].split(' ')[1::]

    user_id = message.author.id
    wordle_board = msg[2::]
    
    entry = {'worldle_date': date, 'ratio': ratio, 'date': str(datetime.datetime.now()), 'board': wordle_board}

    data = read_database()    

    with open('database.json', 'w') as database:
        if str(user_id) in data:
            data[str(user_id)][date] = entry
        else:
            data[str(user_id)] = {date: entry}

        json.dump(data, database, indent=4)


    




client.run(os.getenv('token'))