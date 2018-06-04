import math
import json
import re
import os
import random
import requests
from requests_oauthlib import OAuth1Session
from xml.sax.saxutils import unescape


def get_total_crypko_count():
    url = 'https://api.crypko.ai/crypkos/search'
    query = {
        'category': 'all',
        'sort': '-id'
    }
    response = requests.get(url, params=query).json()
    return response['totalMatched']


def get_max_page():
    url = 'https://api.crypko.ai/crypkos/search'
    query = {
        'category': 'all',
        'sort': '-id',
        'attributes': 'hasbio,hasname'
    }
    response = requests.get(url, params=query).json()
    max_page = math.ceil(response['totalMatched'] / 12)
    return max_page, response['totalMatched']


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


def update_profile(named_crypko_count):
    CK = os.environ['CK']
    CS = os.environ['CS']
    AT = os.environ['AT']
    AS = os.environ['AS']

    url_profile = 'https://api.twitter.com/1.1/account/update_profile.json'

    twitter = OAuth1Session(CK, CS, AT, AS)

    crypko_count = get_total_crypko_count()
    percentage = named_crypko_count / crypko_count * 100.0

    params = {
        'location': 'Count of Crypkos with name and bio: %d (%.2f%%)' % (named_crypko_count, percentage)
    }
    response = twitter.post(url_profile, params=params)

    if response.status_code != 200:
        print('プロフィールアップデート失敗: %s' % response.text)
        exit()
    print('プロフィールアップデート成功')


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


def replace_ng_words(text):
    ng_words = [
        '奇形',
        '原爆'
    ]

    for ng_word in ng_words:
        text = text.replace(ng_word, 'xxx')

    return text


def lambda_handler(event, context):
    temp = get_max_page()
    max_page = temp[0]
    crypko_count = temp[1]
    page = random.randrange(max_page)
    crypko = get_random_crypko(page)
    print('Crypko #%d' % crypko['id'])
    details = get_crypko_details(crypko['id'])
    print(details)

    update_profile(crypko_count)

    # NGワードを置換
    name = replace_ng_words(details['name'])
    bio = replace_ng_words(details['bio'])

    # @を置換
    name = name.replace('@', '@ ')
    bio = bio.replace('@', '@ ')

    # エスケープを解除
    name = unescape(name, {'&quot;': '"'})
    bio = unescape(bio, {'&quot;': '"'})

    tweet_text = '%s - %s https://crypko.ai/#/card/%d #crypkoshowcase' % (
        name, bio, details['id']
    )
    print('ツイート: '+tweet_text)
    tweet_success = tweet(tweet_text, details['image_url'])

    if tweet_success is False:
        # bioを切り詰める
        bio = bio[:90] + '……'

        tweet_text = '%s - %s https://crypko.ai/#/card/%d #crypkoshowcase' % (
            name, bio, details['id']
        )
        print('切り詰めて再ツイート: '+tweet_text)
        tweet(tweet_text, details['image_url'])
