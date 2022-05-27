import googleapiclient.discovery
import googleapiclient.errors
import yt_dlp
import json
from PyInquirer import prompt

config = "./config.json"

api_service_name = "youtube"
api_version = "v3"

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

class Download:

def get_config(config):
    with open(config, 'r') as json_file:
        config_data = json.load(json_file)
    return config_data


def download(data, URLS):
    print(URLS)
    ydl_opts = {
        "postprocessors": [
            {"key": "SponsorBlock"},
            {"key": "ModifyChapters", "remove_sponsor_segments": ['sponsor']}
        ],
        "paths": {"home": data["path"]},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(URLS)


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
            publishedAfter="2022-05-24T00:00:00Z",
            type="video")
        response = request.execute()
        response = response["items"][0]
        print(response)
        videos.append({"name": response["snippet"]["title"], "id": response["id"]["videoId"],
                       "author": response["snippet"]["channelTitle"],
                       "pouceOngle": response["snippet"]["thumbnails"]["default"]["url"],
                       "time": response["snippet"]["publishTime"]})
    return videos


def craft_url(ids):
    urls = []
    base_url = "https://youtube.com/watch?v="
    for id in ids:
        urls.append(base_url + id)
    return urls


def subscribe(key, data, channel=None):
    if channel is None:
        search(key, data, type="channel")
    else:
        print(channel)
        print(data)
        data["subscribed_channels"].append({"name": channel["name"], "id": channel["id"]})
        with open(config, "w") as config_file:
            json.dump(data, config_file, indent=4)
            config_file.close()
        print("Your now subscribed to " + channel["name"])
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
        answer = answer["select_video"]
        print(answer)
    else:
        print(video)
        print("downloading " + video["name"] + " to " + data["path"])
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

    print("Here is what we found:")
    for i in request_response["items"]:
        if i["id"]["kind"] == "youtube#channel":
            content.append({"type": "channel", "name": i["snippet"]["title"], "id": i["snippet"]["channelId"],
                            "pouceOngle": i["snippet"]["thumbnails"]["medium"]["url"]})
            print("type: channel - " + content[-1]["name"])
        elif i["id"]["kind"] == "youtube#video":
            content.append({"type": "video", "name": i["snippet"]["title"], "id": i["id"]["videoId"],
                            "author": i["snippet"]["channelTitle"],
                            "pouceOngle": i["snippet"]["thumbnails"]["default"]["url"],
                            "time": i["snippet"]["publishTime"]})
            print(
                "type: video - " + content[-1]["name"] + " by " + content[-1]["author"] + " at " + content[-1]["time"])
    response = prompt(questions[1])
    if content[int(response["result_choice"])]["type"] == "video":
        print("Downloading Video")
        watch(key, data, video=content[int(response["result_choice"])])
    elif content[int(response["result_choice"])]["type"] == "channel":
        subscribe(key, data, channel=content[int(response["result_choice"])])


def main():
    data = get_config(config)
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
    main()
