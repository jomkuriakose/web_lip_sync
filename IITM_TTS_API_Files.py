#!/usr/bin/python3

# TTS using API synthesis code
# Author: Jom Kuriakose
# email: jom@cse.iitm.ac.in
# Date: 16/02/2021

import requests
import shutil
import wave
import json
import wget
import sys
import os

def main():

	# Read variables
	textFile = sys.argv[1]
	audioFolder = sys.argv[2]
	lang = sys.argv[3]
	gender = sys.argv[4]

	try:
		os.makedirs(audioFolder)
	except OSError as e:
		sys.exit('Error: Output already exists!!')
		
	# Read text file
	fid = open(textFile,'r')
	text = fid.read().strip()
	text_split = text.split('\n')
	num_lines = len(text_split)
	fid.close()
	
	# IITM API
	if (num_lines <= 10):
		wav_list = IITM_API_request(text,gender,lang)
	else:
		n = 10
		text_split_final = [text_split[i * n:(i + 1) * n] for i in range((len(text_split) + n - 1) // n)]
		wav_list = []
		for i in range(0,len(text_split_final)):
			wav_list_split = IITM_API_request('\n'.join(text_split_final[i]),gender,lang)
			wav_list.extend(wav_list_split)

	# Output audio
	fileList = []
	for i in range(0,len(wav_list)):
		url = wav_list[i]
		filename = wget.download(url, out=audioFolder)
		fileList.append(filename)

# API function
def IITM_API_request(text,gender,lang):
	url = "https://asr.iitm.ac.in/fs2"
	payload = json.dumps({
		"text": text,
		"gender": gender,
		"lang": lang,
                "speed": 1.2
	})
	headers = {
		'Content-Type': 'application/json'
	}
	response = requests.request("POST", url, headers=headers, data=payload)
	if (response.json()['status'] == 'success'):
		wav_list_str = response.json()['outspeech_filepath']
	else:
		sys.exit(response.json()['reason'])
	wav_list = wav_list_str.replace('"','').strip('][').split(', ')
	return wav_list

if __name__ == "__main__":
	main()

