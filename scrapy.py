from lxml import html
import json
import os
import re
import urllib
from functools import reduce
from hashlib import md5
import urllib.parse
import time
import requests

def wib():
    mixinKeyEncTab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]

    def getMixinKey(orig: str):
        '对 imgKey 和 subKey 进行字符顺序打乱编码'
        return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

    def encWbi(params: dict, img_key: str, sub_key: str):
        '为请求参数进行 wbi 签名'
        mixin_key = getMixinKey(img_key + sub_key)
        curr_time = round(time.time())
        params['wts'] = curr_time  # 添加 wts 字段
        params = dict(sorted(params.items()))  # 按照 key 重排参数
        # 过滤 value 中的 "!'()*" 字符
        params = {
            k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
            for k, v
            in params.items()
        }
        query = urllib.parse.urlencode(params)  # 序列化参数
        wbi_sign = md5((query + mixin_key).encode()).hexdigest()  # 计算 w_rid
        params['w_rid'] = wbi_sign
        return params

    def getWbiKeys() -> tuple[str, str]:
        '获取最新的 img_key 和 sub_key'
        resp = requests.get('https://api.bilibili.com/x/web-interface/nav')
        resp.raise_for_status()
        json_content = resp.json()
        img_url: str = json_content['data']['wbi_img']['img_url']
        sub_url: str = json_content['data']['wbi_img']['sub_url']
        img_key = img_url.rsplit('/', 1)[1].split('.')[0]
        sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
        return img_key, sub_key

    img_key, sub_key = getWbiKeys()

    signed_params = encWbi(
        params={
            'foo': '114',
            'bar': '514',
            'baz': 1919810
        },
        img_key=img_key,
        sub_key=sub_key
    )
    query = urllib.parse.urlencode(signed_params)
    return query

def get_title_json(url):
    global pid
    head = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67'
    }
    r = requests.get(url, headers=head)

    # 通过xpath获取视频的标题
    tree = html.fromstring(r.text)
    title = str(tree.xpath('//*[@id="viewbox_report"]/h1/@title')[0])
    s = ['\n', '，', '。', ' ', '—', '”', '？', '“', '（', '）', '、', '|', '【', '】', '/', '\\']
    for i in s:
        title = title.replace(i, '')
    print(f'视频标题："{title}"')
    file_path = os.path.join('music', title + '.mp3')

    try:
        open(file_path + '.mp3', 'w')
    except Exception as e:
        title = str(pid)
        pid=pid+1
    # 通过re获取包含视频和音频地址的json字段
    json_data = re.findall('<script>window.__playinfo__=(.*?)</script>', r.text)[0]
    json_data = json.loads(json_data)

    audio_url = json_data['data']['dash']['audio'][0]['baseUrl']
    print('已提取到音频地址')
    video_url = json_data['data']['dash']['video'][0]['baseUrl']
    # print('已提取到视频地址')
    return file_path, audio_url, video_url


def download(title, audio_url, video_url):
    head = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
        'Referer': url
    }
    print('开始下载音频')
    r_audio = requests.get(url=audio_url, headers=head)
    audio_data = r_audio.content
    file = open(title + '.mp3', "w")
    file.close()
    with open(title + '.mp3', mode='wb') as f:
        f.write(audio_data)
    print('音频下载完成')

pid=1
mid = input("输入用户uid\n")
sessdata = input("输入cookie\n")
url = 'https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid=' + mid
head = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
    'Cookie': f'SESSDATA={sessdata}'
}
response = requests.get(url, headers=head)
if response.status_code != 200:
    print(response.status_code)
    exit(0)
data = json.loads(response.text)
id = data['data']['list'][0]['id']
if not data['data']:
    print("error")
    exit(0)
print("收藏夹mid为："+str(id))
url = 'https://api.bilibili.com/x/v3/fav/resource/ids?media_id='+str(id)
response = requests.get(url, headers=head)
if response.status_code != 200:
    print(response.status_code)
    exit(0)
data = json.loads(response.text)
bv_ids = [entry['bv_id'] for entry in data['data']]
wbi=wib()
if not os.path.exists('music'):
    os.makedirs('music')
for bvd in bv_ids:
    try:
        url = 'https://www.bilibili.com/video/' + bvd +'?'+ wbi
        title, audio_url, video_url=get_title_json(url)
        print(title)
        download(title, audio_url, video_url)
    except Exception as e:
        print('error:'+bvd)

