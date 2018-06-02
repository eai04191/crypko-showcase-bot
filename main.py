import math
import json
import re
import os
import random
import requests
from requests_oauthlib import OAuth1Session


def get_max_page():
    url = 'https://api.crypko.ai/crypkos/search'
    query = {
        'category': 'all',
        'sort': '-id',
        'attributes': 'hasbio,hasname'
    }
    response = requests.get(url, params=query).json()
    max_page = math.ceil(response['totalMatched'] / 12)
    return max_page


def get_random_crypko(page):
    url = 'https://api.crypko.ai/crypkos/search'
    query = {
        'category': 'all',
        'sort': '-id',
        'attributes': 'hasbio,hasname',
        'page': page
    }
    response = requests.get(url, params=query).json()
    count = len(response['crypkos'])
    rand = random.randrange(count)-1
    return response['crypkos'][rand]


def get_crypko_details(id):
    url = 'https://s.crypko.ai/c/' + str(id)
    response = requests.get(url)
    html = response.text
    name = re.search(
        '<meta name="twitter:title" content="(.*?)">', html).group(1)
    bio = re.search(
        '<meta name="twitter:description" content="([\s\S]*?)">', html).group(1)
    image_url = re.search('<img src="(.*?)">', html).group(1)
    details = {
        'id': id,
        'name': name,
        'bio': bio,
        'image_url': image_url
    }
    return details


def tweet(text, image_url):
    # https://qiita.com/yubais/items/864eedc8dccd7adaea5d
    CK = os.environ['CK']
    CS = os.environ['CS']
    AT = os.environ['AT']
    AS = os.environ['AS']

    url_media = 'https://upload.twitter.com/1.1/media/upload.json'
    url_text = 'https://api.twitter.com/1.1/statuses/update.json'

    twitter = OAuth1Session(CK, CS, AT, AS)

    # 画像投稿
    image = requests.get(image_url)
    files = {'media': image.content}
    req_media = twitter.post(url_media, files=files)

    # レスポンスを確認
    if req_media.status_code != 200:
        print('画像アップデート失敗: %s' % req_media.text)
        exit()

    # Media ID を取得
    media_id = json.loads(req_media.text)['media_id']
    print('Media ID: %d' % media_id)

    # Media ID を付加してテキストを投稿
    params = {'status': text, "media_ids": [media_id]}
    req_text = twitter.post(url_text, params=params)

    # 再びレスポンスを確認
    if req_text.status_code != 200:
        print('テキストアップデート失敗: %s' % req_text.text)
        return False

    print('ツイート成功')
    return True


def lambda_handler(event, context):
    maxPage = get_max_page()
    page = random.randrange(maxPage)
    crypko = get_random_crypko(page)
    print('Crypko #' + str(crypko['id']))
    details = get_crypko_details(75456)
    print(details)

    tweet_text = '%s - %s https://crypko.ai/#/card/%s #crypkoshowcase' % (
        details['name'], details['bio'], str(details['id'])
    )
    print('ツイート: '+tweet_text)
    tweet_success = tweet(tweet_text, details['image_url'])
    if tweet_success is False:
        # bioを切り詰める
        if len(details['bio']) > 90:
            bio = details['bio'][:90] + '……'
        else:
            bio = details['bio']

        tweet_text = '%s - %s https://crypko.ai/#/card/%s #crypkoshowcase' % (
            details['name'], bio, str(details['id'])
        )
        print('切り詰めて再ツイート: '+tweet_text)
        tweet(tweet_text, details['image_url'])
