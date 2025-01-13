import sys
import requests
from lxml import etree
from datetime import datetime, timedelta

def get_root(url):
    try:
        r = requests.get(url)
        r.encoding = r.apparent_encoding
        return etree.fromstring(r.text.encode('utf-8'))
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

def get_programs(date, station_id):
    root = get_root(f'http://radiko.jp/v3/program/station/date/{date}/{station_id}.xml')
    for p in root.xpath('//prog'):
        print(f'{p.attrib["ftl"]}-{p.attrib["tol"]} {p.xpath("pfm")[0].text=} {p.xpath("title")[0].text=}')

def main():
	programs = {
		"TBSラジオ": "TBS",
		"ニッポン放送": "LFR",
		"ラジオ大阪": "OBC",
		"MBSラジオ": "MBS",
	}
	
	# 標準入力から放送局を番号で選択し，さらに，過去何日ぶんの番組表を取得するかを入力
	# 気が済むまで繰り返す
	while True:
		while True:
			print("放送局を選択してください")
			for i, (k, v) in enumerate(programs.items()):
				print(f"{i}: {k}")
			station = input()
			if station.isdigit() and 0 <= int(station) < len(programs):
				station_id = list(programs.values())[int(station)]
				break
			print("Error: Invalid input")
	
		# 何日前までのデータを取得するかを入力（0から7まで）
		while True:
			print("何日前までのデータを取得しますか？（0から7まで）")
			days = input()
			if days.isdigit() and 0 <= int(days) <= 7:
				break
			print("Error: Invalid input")
	
		# 現在の日付を取得
		today = datetime.today()
		for i in range(int(days)):
			date = (today - timedelta(days=i)).strftime('%Y%m%d')
			print(f"{date}の番組表")
			get_programs(date, station_id)
			print()		
		# 続けるかどうかを入力	
		print("続けますか？（y/n）")
		if input() != 'y':
			break

if __name__ == "__main__":
    main()