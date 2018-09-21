# SplitBySubs
This script splits up movie files according to subtitle files.

So you get one output file per line of dialogue. It takes any file format ffmpeg can handle and an SRT subtitles file.

You can see some of the results of this script in this twitter thread:
https://twitter.com/Foone/status/1043220977675452416

## Usage
You need python 2.7 and the srt module. I usually set up a virtualenv:
```
$ virtualenv venv
$ . venv/bin/activate
$ pip install -r requirements.txt
```
Then just run split_by_subs.py with python:
```
$ python split_by_subs.py moviefile.avi some_srt_file.srt
```
If you don't get give the SRT filename, it guesses it by trying the same filename as the movie but with an ".srt" extension.

## Known bugs/improvements needed
* The between-dialogue mode has an off-by-one error: the final bit of silence between 
the last spoken line and the end of the video is not exported.
* There should be an option to manually resynchronize the subtitles by some arbitrary amount of time
* Often subtitles are included into video files, like inside MKV containers. That's not at all supported yet.
* Subtitle formats other than SRT should be supported
* I commented out the scaling part of my favorite twitter-mp4 flavor: it may need to be re-added for big videos, so that 
should be an option.
* Add an option to convert directly to GIFs instead of movies, maybe by calling mov2gif? 
