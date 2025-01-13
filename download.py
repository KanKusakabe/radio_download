import requests
from lxml import etree
import datetime
import subprocess
import base64
import json
from concurrent.futures import ThreadPoolExecutor
import os, sys

class RadioDownloader:
    def __init__(self):
        self.authkey = 'bcd151073c03b352e1ef2fd66c32209da9ca0afa'
        # config.jsonから読み込む
        """
        このファイルと同じ階層に"config.json"というファイルが必要
        下記のようなファイルを想定している
        {
        "email": "radikoに登録したメールアドレス",
        "password": "radikoに登録したパスワード"
        }
        """
        with open("config.json") as f:
            config = json.load(f)
            self.email = config["email"]
            self.password = config["password"]
        
        # ターゲットのラジオ局のidは下記のurlを参照
        # https://qiita.com/miyama_daily/items/87c7694a10c36a11a96c
        self.target_stations = {
            "TBS": "TBSラジオ",
            "LFR": "ニッポン放送",
            "MBS": "MBSラジオ",
            "OBCラジオ大阪": "OBC",
            
        }
        
        # ここのダウンロードの対象となるキーワードを設定
        self.keywords = [
            "オールナイトニッポン",
            "爆笑問題カーボーイ",
            "メガネびいき", 
            "ブタピエロ",
            "アルコ＆ピース",
            "空気階段の踊り場",
            "山里亮太の不毛な議論",
            "ハライチのターン！",
            "マイナビ Laughter Night",            
        ]

    def file_exists(self, filename):
        """ファイルが既に存在するかチェック"""
        # ファイルの場所は，カレントディレクトリか，"../Music/.../"に保存される
        if os.path.exists(f"{filename}.mp3"):
            return True
        # ../Music/ に保存されているか確認
        for root, dirs, files in os.walk("../Music"):
            if f"{filename}.mp3" in files:
                return True
        return False

    def auth(self):
        authkey = self.authkey
        email = self.email
        password = self.password
        session = requests.session()
        user_data = {'mail':email, 'pass':password}

        #radiko login apiにpostして session_idとcookiesを取得します。
        response_login = session.post('https://radiko.jp/v4/api/member/login', data=user_data)
        if response_login.status_code != 200:
            print("login missed.")
            return "prohibited"
        session_id = json.loads(response_login.content)["radiko_session"]
        premium_cookie = session.cookies

        #auth1にgetしてauthtokenを取得します。authtokenは最終的にffmpegでm3u8から音声データを取得する際に必要です。
        #authtokenを認証させるためのpartialkeyを作成するためのkeyoffsetとkeylengthを取得します。
        headers_1 = {
        'User-Agent': 'curl/7.52.1', 
        'Accept': '*/*', 
        'x-radiko-user': 'dummy_user', 
        'x-radiko-app': 'pc_html5', 
        'x-radiko-app-version': '0.0.1', 
        'x-radiko-device': 'pc'
        }
        response_1 = requests.get('https://radiko.jp/v2/api/auth1', headers=headers_1, cookies=premium_cookie)
        if response_1.status_code != 200:
            print("auth 1 missed.")
            return "prohibited"
        authtoken = response_1.headers['X-Radiko-AUTHTOKEN']
        length = int(response_1.headers['X-Radiko-KeyLength'])
        offset = int(response_1.headers['X-Radiko-KeyOffset'])

        #謎の固定文字列authkeyからpartialkeyを作成します。
        partialkey = base64.b64encode(authkey[offset: offset + length].encode('utf-8')).decode('utf-8')

        #auth2にgetしてauth1で取得したauthtokenを認証します。
        headers_2 = {
            'User-Agent': 'curl/7.52.1', 
            'Accept': '*/*', 
            'x-radiko-user': 'dummy_user', 
            'X-RADIKO-AUTHTOKEN': authtoken, 
            'x-radiko-partialkey': partialkey, 
            'X-Radiko-App' : 'pc_html5',
            'X-Radiko-App-Version': '0.0.1', 
            'x-radiko-device': 'pc'
            }
        response_2 = requests.get(f'https://radiko.jp/v2/api/auth2?radiko_session={session_id}', headers=headers_2, cookies=premium_cookie)
        if response_2.status_code != 200:
            print("auth 2 missed.")
            return "prohibited"

        #取得したauthtokenを使って自由に音声データのダウンロードが可能になりました。
        return authtoken


    def get_root(self, url):
        try:
            r = requests.get(url)
            r.encoding = r.apparent_encoding
            return etree.fromstring(r.text.encode('utf-8'))
        except Exception as e:
            print(f"Error fetching data: {e}")
            sys.exit(1)
    
    def download_thumbnail(self, img_url, filename):
        """画像URLから画像をダウンロードして保存"""
        if not img_url:
            return None
            
        thumbnail_filename = f"thumbnails/{filename}.jpg"
        os.makedirs("thumbnails", exist_ok=True)
        
        # すでに存在する場合はそのパスを返す
        if os.path.exists(thumbnail_filename):
            return thumbnail_filename
            
        try:
            response = requests.get(img_url)
            if response.status_code == 200:
                with open(thumbnail_filename, 'wb') as f:
                    f.write(response.content)
                return thumbnail_filename
        except Exception as e:
            print(f"Error downloading thumbnail: {e}")
        
        return None

    def download_program(self, program, date):
        authtoken = self.auth()
        if authtoken == "prohibited":
            print("Authentication failed")
            return

        filename = f"{program['title']}-{date}"
        
        # 既にファイルが存在する場合はスキップ
        if self.file_exists(filename):
            print(f"File already exists: {filename}.mp3")
            return

        # XMLから取得した画像URLを使用してサムネイルをダウンロード
        thumbnail_path = None
        if 'img_url' in program and program['img_url']:
            thumbnail_path = self.download_thumbnail(program['img_url'], filename)

        # メタデータオプションを設定
        metadata_options = (
            f'-metadata artist="{self.target_stations[program["station_id"]]}" '
            f'-metadata album="{program["title"]}"'
        )

        # サムネイル用のコマンドを構築
        if thumbnail_path:
            command = (
                f'ffmpeg -loglevel error -headers "X-RADIKO-AUTHTOKEN: {authtoken}" '  # -loglevel error を追加
                f'-i "https://radiko.jp/v2/api/ts/playlist.m3u8?station_id={program["station_id"]}'
                f'&l=15&ft={program["ft"]}&to={program["to"]}" '
                f'-i "{thumbnail_path}" -map 0:a -map 1:v -c:v copy '
                f'-id3v2_version 3 -metadata:s:v title="Album cover" '
                f'-metadata:s:v comment="Cover (front)" '
                f'-acodec libmp3lame -b:a 128k {metadata_options} "{filename}.mp3"'
            )
        else:
            command = (
                f'ffmpeg -loglevel error -headers "X-RADIKO-AUTHTOKEN: {authtoken}" '  # -loglevel error を追加
                f'-i "https://radiko.jp/v2/api/ts/playlist.m3u8?station_id={program["station_id"]}'
                f'&l=15&ft={program["ft"]}&to={program["to"]}" '
                f'-acodec libmp3lame -b:a 128k {metadata_options} "{filename}.mp3"'
            )

        try:
            subprocess.run(command, shell=True, check=True)
            print(f"Successfully downloaded: {filename}")
        except subprocess.CalledProcessError as e:
            print(f"Download failed for {filename}: {e}")

    def get_programs(self, date, station_id):
        url = f'http://radiko.jp/v3/program/station/date/{date}/{station_id}.xml'
        try:
            r = requests.get(url)
            r.encoding = r.apparent_encoding
            root = etree.fromstring(r.text.encode('utf-8'))
            programs = []
            
            for prog in root.xpath('//prog'):
                title = prog.xpath("title")[0].text
                ft = prog.attrib["ft"]
                to = prog.attrib["to"]
                
                # img要素があれば取得
                img_url = None
                img_elements = prog.xpath("img")
                if img_elements and len(img_elements) > 0:
                    img_url = img_elements[0].text
                
                # キーワードが番組タイトルに含まれているかチェック
                if any(keyword in title for keyword in self.keywords):
                    # 「オールナイトニッポン」は，「オールナイトニッポンX」を含むため，この場合はスキップ
                    if any(key in title for key in ["オールナイトニッポンGOLD", "オールナイトニッポンX", "オールナイトニッポンサタデースペシャル"]):
                        continue
                    programs.append({
                        'title': title,
                        'ft': ft,
                        'to': to,
                        'station_id': station_id,
                        'img_url': img_url
                    })
            
            return programs
        except Exception as e:
            print(f"Error fetching programs for {station_id} on {date}: {e}")
            return []
    
    # メイン処理. 7日分の番組をダウンロード.
    def run(self):
        # 本日の日付から過去7日分の日付を取得
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)).strftime('%Y%m%d') for i in range(7)]

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for date in dates:
                for station_id in self.target_stations.keys():
                    programs = self.get_programs(date, station_id)
                    
                    # programsをprintして確認
                    for p in programs:
                        print(f"{station_id=}, {date=}", {p['title']}, {p['ft']}, {p['to']})
                    # print(f"{station_id=}, {date=}", {p['title'] for p in programs})
                    
                    for program in programs:
                        # programが空だったらスキップ
                        if not program:
                            continue
                        else:
                            futures.append(
                                executor.submit(self.download_program, program, date)
                            )
                    

            for future in futures:
                future.result()

if __name__ == "__main__":
    downloader = RadioDownloader()
    downloader.run()