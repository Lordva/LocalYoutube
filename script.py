import os
import googleapiclient.discovery
import googleapiclient.errors
import yt_dlp
import json
import fnmatch
from PyInquirer import prompt
from enum import Enum

config = "./config.json"

api_service_name = "youtube"
api_version = "v3"

banner = """ ▄▄▄     ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄ ▄▄▄▄▄▄ ▄▄▄     ▄▄   ▄▄ ▄▄▄▄▄▄▄ ▄▄   ▄▄ ▄▄▄▄▄▄▄ ▄▄   ▄▄ ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄ 
█   █   █       █       █      █   █   █  █ █  █       █  █ █  █       █  █ █  █  ▄    █       █
█   █   █   ▄   █       █  ▄   █   █   █  █▄█  █   ▄   █  █ █  █▄     ▄█  █ █  █ █▄█   █    ▄▄▄█
█   █   █  █ █  █     ▄▄█ █▄█  █   █   █       █  █ █  █  █▄█  █ █   █ █  █▄█  █       █   █▄▄▄ 
█   █▄▄▄█  █▄█  █    █  █      █   █▄▄▄█▄     ▄█  █▄█  █       █ █   █ █       █  ▄   ██    ▄▄▄█
█       █       █    █▄▄█  ▄   █       █ █   █ █       █       █ █   █ █       █ █▄█   █   █▄▄▄ 
█▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█▄█ █▄▄█▄▄▄▄▄▄▄█ █▄▄▄█ █▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█ █▄▄▄█ █▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█
"""

main_menu = [
    {
        'type': 'list',
        'name': 'default',
        'message': 'welcome to BTYT, what would you like to do ?',
        'choices': [
            'Subscribe to a new channel',
            'Watch a video in my subscriptions',
            'search for a video',
            'exit'
        ]
    }
]


class Status(Enum):
    INFO = 0,
    WARNING = 1,
    ERROR = 2,
    DEBUG = 3,


Color = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "LIGHT_PURPLE": "\033[94m",
    "PURPLE": "\033[95m",
    "CYAN": "\033[96m ",
    "LIGHT_GRAY": "\033[97m",
    "BLACK": "\033[98m",
    "RESET": "\033[0m",
    "BOLD": "\033[01m"
}


def logger(message, status=Status.INFO):
    if status == Status.INFO:
        return print(Color["CYAN"] + "[INFO] " + Color["RESET"] + message)
    elif status == Status.WARNING:
        return print(Color["YELLOW"] + "[WARN] " + Color["RESET"] + message)
    elif status == Status.ERROR:
        return print(Color["RED"] + "[ERROR] " + Color["RESET"] + message)
    elif status == Status.DEBUG:
        return print(Color["LIGHT_GRAY"] + "[DEBUG] " + Color["RESET"] + message)
    else:
        return print(message)


def get_config(config):
    with open(config, 'r') as json_file:
        config_data = json.load(json_file)
    return config_data


def recover_download(data):
    question = [
        {
            'type': 'list',
            'name': 'default',
            'message': 'Would you like to finish this download ?',
            'choices': [
                'Yes',
                'No',
                'Skip all',
            ]
        }
    ]
    for file in os.listdir(data["path"]):
        if fnmatch.fnmatch(file, '*.part'):
            logger("Found a uncompleted download: " + file, Status.WARNING)
            a = prompt(question)
            if a["default"] == question[0]['choices'][0]:
                logger("Fetching download info", Status.INFO)
                try:
                    with open(file[:-15] + ".info.json", "r") as info_file:
                        id = json.load(info_file)["id"]
                except FileNotFoundError:
                    logger("Could not find data file for this download", Status.ERROR)
                    return False
                except FileExistsError:
                    logger("Could not find data file for this download", Status.ERROR)
                    return False
                download(data, craft_url([id]))
                return True
            elif a["default"] == question[0]['choices'][1]:
                continue
            else:
                return False


def download(data, URLS):
    logger(str(URLS), Status.DEBUG)
    ydl_opts = {
        "postprocessors": [
            {"key": "SponsorBlock"},
            {"key": "ModifyChapters", "remove_sponsor_segments": ['sponsor']}
        ],
        "paths": {"home": data["path"]},
        "writeinfojson": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(URLS)
    except yt_dlp.DownloadError:
        logger("Could not download the video", Status.ERROR)


def get_latest_videos(key, data):
    videos = []
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=key)
    channels = data["subscribed_channels"]
    for i in channels:
        request = youtube.search().list(
            part="snippet",
            channelId=i["id"],
            maxResults=1,
            order="date",
            type="video")
        try:
            response = request.execute()
        except googleapiclient.errors.Error:
            return logger("Could not reach google API", Status.ERROR)
        except:
            return logger("Unknown error", Status.ERROR)
        response = response["items"][0]
        videos.append({"name": response["snippet"]["title"], "id": response["id"]["videoId"],
                       "author": response["snippet"]["channelTitle"],
                       "pouceOngle": response["snippet"]["thumbnails"]["default"]["url"],
                       "time": response["snippet"]["publishTime"]})
    return videos


def craft_url(ids, type="video"):
    urls = []
    base_url = ""
    if type == "video":
        base_url = "https://youtube.com/watch?v="
    elif type == "channel":
        base_url = "https://youtube.com/channel/"
    for id in ids:
        urls.append(base_url + id)
    return urls


def subscribe(key, data, channel=None):
    if channel is None:
        search(key, data, type="channel")
    else:
        for i in data["subscribed_channels"]:
            if channel["id"] == i["id"]:
                return print(
                    Color["RED"] + "[ERROR]" + Color["RESET"] + " You are already subscribed to " +
                    channel["name"])
        data["subscribed_channels"].append({"name": channel["name"], "id": channel["id"]})
        with open(config, "w") as config_file:
            json.dump(data, config_file, indent=4)
            config_file.close()
        logger("Your now subscribed to " + channel["name"])
        main()


def watch(key, data, video=None):
    if video is None:
        question = [
            {
                "type": "input",
                "name": "select_video",
                "message": "select videos separated by a coma: "
            }]
        video_list = get_latest_videos(key, data)
        for i in range(len(video_list)):
            print(str(i) + ". " + video_list[i]["name"] + " by " + video_list[i]["author"])
        answer = prompt(question)
        answer = answer["select_video"].split(",")
        download(data, craft_url([video_list[int(i)]["id"] for i in answer]))
    else:
        logger("downloading " + video["name"] + " to " + data["path"])
        download(data, craft_url([video["id"]]))


def search(key, data, type=None):
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=key)
    questions = [{
        'type': 'input',
        'name': 'search_query',
        'message': 'input your search query',
    },
        {
            'type': 'input',
            'name': 'result_choice',
            'message': 'select a video or channel:',
        }]
    response = prompt(questions[0])
    if type == "channel":
        request = youtube.search().list(
            part="snippet",
            q=response["search_query"],
            type="channel",
            maxResults=10
        )
    elif type == "video":
        request = youtube.search().list(
            part="snippet",
            q=response["search_query"],
            type="video",
            maxResults=10
        )
    else:
        request = youtube.search().list(
            part="snippet",
            q=response["search_query"],
            maxResults=10
        )
    request_response = request.execute()
    content = []

    logger("Here is what we found:")
    for i in range(len(request_response["items"])):
        if request_response["items"][i]["id"]["kind"] == "youtube#channel":
            content.append({"type": "channel", "name": request_response["items"][i]["snippet"]["title"],
                            "id": request_response["items"][i]["snippet"]["channelId"],
                            "pouceOngle": request_response["items"][i]["snippet"]["thumbnails"]["medium"]["url"]})
            print(
                str(i) + ". channel - " + content[-1]["name"] + " - " + str(craft_url([content[-1]["id"]], "channel")))
        elif request_response["items"][i]["id"]["kind"] == "youtube#video":
            content.append({"type": "video", "name": request_response["items"][i]["snippet"]["title"],
                            "id": request_response["items"][i]["id"]["videoId"],
                            "author": request_response["items"][i]["snippet"]["channelTitle"],
                            "pouceOngle": request_response["items"][i]["snippet"]["thumbnails"]["default"]["url"],
                            "time": request_response["items"][i]["snippet"]["publishTime"]})
            print(str(i) + ". video - " + content[-1]["name"] + " by " + content[-1]["author"] + " at " + content[-1][
                "time"])
    response = prompt(questions[1])
    if content[int(response["result_choice"])]["type"] == "video":
        logger("Downloading Video")
        watch(key, data, video=content[int(response["result_choice"])])
    elif content[int(response["result_choice"])]["type"] == "channel":
        subscribe(key, data, channel=content[int(response["result_choice"])])


def main():
    try:
        data = get_config(config)
    except OSError:
        return logger("Could not access config file", Status.ERROR)
    recover_download(data)
    apikey = data["api_key"]
    answer = prompt(main_menu)
    if answer["default"] == main_menu[0]["choices"][0]:
        subscribe(apikey, data)
    elif answer["default"] == main_menu[0]["choices"][1]:
        watch(apikey, data)
    elif answer["default"] == main_menu[0]["choices"][2]:
        search(apikey, data)
    else:
        exit(0)


if __name__ == "__main__":
    print(banner)
    main()
