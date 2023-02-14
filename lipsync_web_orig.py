import os
import json
import requests
import numpy as np
import math
#import sys

import webvtt

import moviepy.editor as mp
import moviepy.audio.AudioClip as ac
import moviepy.video.fx.all as vfx

import pyvtt
import pysrt
import traceback

AUDIO_EXT = ["mp3", "wav", "webm"]
VIDEO_EXT = ["mp4"]

LANG_CODE = {
    "Hindi": "hin",
    "Marathi": "mr",
    "English" : "eng",
    "Telugu" : "te",
    "Tamil" : "ta",
    "Gujarati": "guj"    
}

def tts_rest_service(text="",gender="male", lang="Hindi", text_list=[]):
    if not text:
        text = "\n".join(text_list)
    
    payload = {
        "text":text,
        "gender": gender,
        "lang": lang
    }
    payload = json.dumps(payload)
    url = "https://asr.iitm.ac.in/IITM_TTS/API/tts.php"
    headers = {'Content-Type': 'application/json'}
    print("sending request")
    resp = requests.request("POST", url=url,headers=headers, data=payload)
    print("response receved")
    return resp

def hh_mm_ss_to_ss(text):
    hh,mm,ss = list(map(float,text.split(":")))
    total_sec = hh*60*60 + mm*60 + ss
    return total_sec

def ss_to_hh_mm_ss(seconds):
    SECONDS_IN_HOUR = 3600
    SECONDS_IN_MINUTE = 60
    HOURS_IN_DAY = 24
    MICROSECONDS_IN_MILLISECOND = 1000
    hrs, secs_remainder = divmod(seconds, SECONDS_IN_HOUR)
    mins, secs = divmod(secs_remainder, SECONDS_IN_MINUTE)
    msecs = round((secs - int(secs))*MICROSECONDS_IN_MILLISECOND)
    secs = int(secs)
    return "%02d:%02d:%02d.%03d" % (hrs, mins, secs, msecs)


def path_correction(file_list):
    domain="https://asr.iitm.ac.in/"
    local_path_prefix = "/var/www/html/"
    return [fp.replace(domain, local_path_prefix)for fp in file_list]


    # wav_dir = "./download/" 
    # file_list = list(map(lambda x: wav_dir+x.split("/")[-1],file_list))
    # return file_list


def change_video_audio(resp_json, vtt_obj, vtt_filepath, audio_file, video_file, lang):
    
    file_list = resp_json["outspeech_filepath"]
    file_list = path_correction(file_list)
    audio_iterator = []

    # check video file's ext
    ext_vid = video_file.split("/")[-1].split(".")[-1]
    if ext_vid in AUDIO_EXT:
        audio_file = video_file
    main_audio_clip = mp.AudioFileClip(audio_file)

    for vtt, filepath in zip(vtt_obj.captions, file_list):
        print(f"i {filepath}")
        stime = hh_mm_ss_to_ss(vtt.start)
        etime = hh_mm_ss_to_ss(vtt.end)
        
        audio_clip_obj = mp.AudioFileClip(filepath)
        audio_iterator.append((stime, etime, audio_clip_obj))

    main_audio_array = main_audio_clip.to_soundarray()
    fps = main_audio_clip.fps
    adur = main_audio_array.shape[0]
    # print(np.shape(main_audio_array))
    main_audio_array = []
    vclips=[]
    if ext_vid in VIDEO_EXT:
        # print(ext_vid)
        try:
            vclip = mp.VideoFileClip(video_file)
            vclip = vclip.without_audio()
            num = 1
            for st, end, tmp_clip in audio_iterator:
                # print('num: '+str(num))
                # print('st: '+str(st))
                # print('end: '+str(end))
                st_idx = int(st*fps)
                end_idx = int(end*fps)
                tmp_arry = tmp_clip.to_soundarray()
                # print('len tmp_arry: '+str(tmp_arry.shape[0]))
                if num==1:
                    tmp_vclip=vclip.subclip(st, end)
                    warp_ratio = float(tmp_vclip.duration/(len(tmp_arry)/fps))
                    #print('v_dur: '+str(tmp_vclip.duration))
                    #print('a_dur: '+str((len(tmp_arry)/fps)))
                    #print('warp_ratio: '+str(warp_ratio))
                    #print('fps: '+str(tmp_vclip.fps))
                    #print('fps * warp ratio: '+str(math.ceil(tmp_vclip.fps * warp_ratio)))
                    # tmp_vclip = tmp_vclip.set_fps(math.ceil(tmp_vclip.fps * warp_ratio))
                    tmp_vclip = tmp_vclip.fx(vfx.speedx, warp_ratio)
                    #print('fps (just making sure): '+str(tmp_vclip.fps))
                    #print('v_dur after warp: '+str(tmp_vclip.duration))
                    # tmp_vclip = tmp_vclip.fx(vfx.speedx, 2)
                    if st_idx >= 0.01:
                        #print(st_idx)
                        #print('Add zero padding in audio')
                        zero_padding = np.zeros((st_idx, 2))
                        #print('zero pad len: '+str(st_idx))
                        #print('zero pad dur: '+str(st))
                        tmp_arry = np.concatenate((zero_padding,tmp_arry), axis=0)
                        #print('Add begin clip')
                        zero_vid_clip = vclip.subclip(0, st)
                        #print('zero_vid_clip dur: '+str(zero_vid_clip.duration))
                        #print('zero_vid_clip fps: '+str(zero_vid_clip.fps))
                        vclips = [zero_vid_clip]
                        vclips.append(tmp_vclip)
                        vtt_obj[num-1].start=ss_to_hh_mm_ss(st)
                    else:
                        vclips = [tmp_vclip]
                        vtt_obj[num-1].start=ss_to_hh_mm_ss(0)
                    prev_end = end
                    main_audio_array=tmp_arry
                    vtt_obj[num-1].end=ss_to_hh_mm_ss(main_audio_array.shape[0]/fps)
                    #print('len main_audio_array: '+str(main_audio_array.shape[0]))
                    num=num+1
                else:
                    tmp_vclip=vclip.subclip(st, end)
                    warp_ratio = float(tmp_vclip.duration/(len(tmp_arry)/fps))
                    #print('v_dur: '+str(tmp_vclip.duration))
                    #print('a_dur: '+str((len(tmp_arry)/fps)))
                    #print('warp_ratio: '+str(warp_ratio))
                    #print('fps: '+str(tmp_vclip.fps))
                    #print('fps * warp ratio: '+str(math.ceil(tmp_vclip.fps * warp_ratio)))
                    # tmp_vclip = tmp_vclip.set_fps(math.ceil(tmp_vclip.fps * warp_ratio))
                    tmp_vclip = tmp_vclip.fx(vfx.speedx, warp_ratio)
                    #print('fps (just making sure): '+str(tmp_vclip.fps))
                    #print('v_dur after warp: '+str(tmp_vclip.duration))
                    # tmp_vclip = tmp_vclip.fx(vfx.speedx, 2)
                    if st-prev_end >= 0.01:
                        #print(end-prev_end)
                        #print('Add zero padding in audio')
                        zero_padding = np.zeros((int(st_idx-(prev_end*fps)), 2))
                        #print('zero pad len: '+str(int(st_idx-(prev_end*fps))))
                        #print('zero pad dur: '+str(int(st_idx-(prev_end*fps))/44100))
                        tmp_arry = np.concatenate((zero_padding,tmp_arry), axis=0)
                        #print('Add inter srt segments')
                        zero_vid_clip = vclip.subclip(prev_end,st)
                        #print('zero_vid_clip dur: '+str(zero_vid_clip.duration))
                        #print('zero_vid_clip fps: '+str(zero_vid_clip.fps))
                        vclips.append(zero_vid_clip)
                        vclips.append(tmp_vclip)
                        vtt_obj[num-1].start=ss_to_hh_mm_ss((main_audio_array.shape[0]/fps)+(int(st_idx-(prev_end*fps))/44100))
                    else:
                        vclips.append(tmp_vclip)
                        vtt_obj[num-1].start=ss_to_hh_mm_ss(main_audio_array.shape[0]/fps)
                    prev_end=end
                    main_audio_array=np.concatenate((main_audio_array,tmp_arry), axis=0)
                    vtt_obj[num-1].end=ss_to_hh_mm_ss(main_audio_array.shape[0]/fps)
                    #print('len main_audio_array: '+str(main_audio_array.shape[0]))
                    num=num+1
                #print()
            if vclip.duration-prev_end >= 0.1:
                #print('Add last segment')
                zero_padding = np.zeros((int(adur-(prev_end*fps)), 2))
                main_audio_array = np.concatenate((main_audio_array,zero_padding), axis=0)
                vclips.append(vclip.subclip(prev_end,vclip.duration))
            
            final_clip = ac.AudioArrayClip(main_audio_array, fps=fps)
            lang_code = LANG_CODE[lang]
            #print('vclips')
            #print(vclips)
            #print(len(vclips))
            fclip=mp.concatenate_videoclips(vclips)
            fclip=fclip.set_audio(final_clip)
            new_file_path = "./static/"+video_file.split("/")[-1]
            # new_file_path = "./"+video_file.split("/")[-1]
            vtt_obj.save()
            new_file_path = new_file_path.replace(".mp4", f"_{lang_code}.mp4")
            fclip.write_videofile(new_file_path, verbose=True,                                       
                                    codec="libx264",
                                    threads=16,                                                           
                                    audio_codec='aac',                                                           
                                    temp_audiofile='temp-audio.m4a',                                             
                                    remove_temp=True,                                                            
                                    preset="medium",                                                             
                                    ffmpeg_params=["-profile:v","baseline", "-level","3.0","-pix_fmt", "yuv420p"])
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            # handle when extension is video but it is an audio
            lang_code = LANG_CODE[lang]
            num=1
            for st, end, tmp_clip in audio_iterator:
                tmp_arry = tmp_clip.to_soundarray()
                if num==1:
                    main_audio_array=tmp_arry
                    num=num+1
                else:
                    main_audio_array=np.concatenate((main_audio_array,tmp_arry), axis=0)
            final_clip = ac.AudioArrayClip(main_audio_array, fps=fps)
            new_file_path = "./static/"+video_file.split("/")[-1].split(".")[0]
            new_file_path = new_file_path + f"_{lang_code}.wav"
            final_clip.write_audiofile(new_file_path,codec='pcm_s16le') 
    elif ext_vid in AUDIO_EXT:
        lang_code = LANG_CODE[lang]
        num=1
        for st, end, tmp_clip in audio_iterator:
            tmp_arry = tmp_clip.to_soundarray()
            if num==1:
                main_audio_array=tmp_arry
                num=num+1
            else:
                main_audio_array=np.concatenate((main_audio_array,tmp_arry), axis=0)
        final_clip = ac.AudioArrayClip(main_audio_array, fps=fps)
        new_file_path = "./static/"+video_file.split("/")[-1].split(".")[0]
        new_file_path = new_file_path + f"_{lang_code}.wav"
        
        final_clip.write_audiofile(new_file_path,codec='pcm_s16le')        
    return new_file_path[1:]



def tts_vtt(gender, lang, vtt_filepath, audio_filepath,video_filepath):
    vtt_obj = webvtt.read(vtt_filepath)
    all_lines=[cap.text for cap in vtt_obj]
    all_lines = "\n".join(all_lines)
    resp = tts_rest_service(text=all_lines, gender=gender, lang=lang)
    #resp_str = json.dumps(resp.json(), indent=4)
    #open("resp_tts.json", "w").write(resp_str)

    result_video_path = change_video_audio(resp.json(), vtt_obj, vtt_filepath, audio_filepath, video_filepath, lang)
    lipsynced_vtt = open(vtt_filepath, "r").read()
    return {"translated_video":result_video_path, 'lipsynced_vtt': lipsynced_vtt}




if __name__ == "__main__":
    # resp_json = json.loads(open("resp_tts.json").read())
    # vtt_obj = webvtt.read("/home/anish/work/asr_e2e_demo/srt_vtt_file/dr_kalam_and_sarabhai_hin.vtt")
    # audio_file = "./audio_file/dr_kalam_and_sarabhai.wav"
    # video_file = "./uploaded_file/dr_kalam_and_sarabhai.mp4"
    # change_video_audio(resp_json, vtt_obj, audio_file, video_file)
    vtt_filepath = "./srt_vtt_file/approx_30secs_clip_hin.vtt"
    audio_filepath = "./audio_file/approx_30secs_clip.wav"
    video_filepath = "./uploaded_file/approx_30secs_clip.mp4"
    vid_path = tts_vtt("female", "Hindi", vtt_filepath, audio_filepath, video_filepath)
    print(vid_path)
