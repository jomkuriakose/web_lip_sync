import sys
import webvtt
webvtt.from_srt(sys.argv[1]).save()