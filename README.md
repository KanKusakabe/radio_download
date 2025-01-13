# radio_download

ラジオ番組をダウンロードするプログラム

## 事前準備

- radiko のアカウントに登録しておく（ダウンロード可能な番組は登録してあるアカウントに依存する）
- python（必要なパッケージは適宜 pip 等でダウンロードする）
- このプロジェクトの他に，radiko アカウントに登録したメールアドレスとパスワードを管理する`config.json`ファイルを作成する（以下に記述）
- **自己責任**

## 想定する環境

- mac os (その他 OS でも可能だろうが，author の環境は mac である)
- 過去 7 日間の番組情報から，事前に登録したキーワードが含まれる番組をダウンロードする
- mac の music アプリを利用して聴取することを目的としている．（music に取り込んだ mp3 ファイルはファイル構造的に一つ上の階層の"Music"というファイルに保存される）
- download.py で番組をダウンロードする

## download.py

### 基本的な使い方

主にこれを動かしてダウンロードする．

```shell
python download.py
```

同じ階層に"config.json"というファイルを作成する．そこでメールアドレスとパスワードを管理する．

```json
{
  "email": "radikoに登録したメールアドレス",
  "password": "radikoに登録したパスワード"
}
```

download.py の 27 行目あたりの `self.target_stations`に検索の対象とする放送局を設定する（下記）．

```python
	# ターゲットのラジオ局のidは下記のurlを参照
        # https://qiita.com/miyama_daily/items/87c7694a10c36a11a96c
        self.target_stations = {
            "TBS": "TBSラジオ",
            "LFR": "ニッポン放送",
            "MBS": "MBSラジオ",
            "OBCラジオ大阪": "OBC",

        }
```

download.py の 37 行目あたりの `self.keywords`にダウンロードの対象とする番組のキーワードを設定する（下記）

```python
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
```

### 保存場所

ダウンロード後はカレントディレクトリに保存される．しかし私は，上の階層の Music というファイルに保存したいので，そこのディレクトリにも，重複するファイルがないか検索をかける

```python
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
```

### キーワードに番組が引っかかりすぎる時の対策

あるキーワードだけでは検索に引っかかりすぎてしまうことがあります．例として「オールナイトニッポン」というキーワードを考えます．コードの中に，既存のファイルがある場合はダウンロードをスキップする部分がありますが，その中に除外するキーワードを加えました．"オールナイトニッポン GOLD", "オールナイトニッポン X", "オールナイトニッポンサタデースペシャル"のキーワードはダウンロードの除外としました．

```python
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
```
