#!/usr/bin/python
import sys,srt,re,os,shutil, json
import subprocess
import argparse, fnmatch

TMPFILE='tmp.srt'

parser = argparse.ArgumentParser(description='Split a movie into sub-movies based on subtitle timing')
parser.add_argument('movie', metavar='MOVIE', type=str,
                    help='The movie to extract from')
parser.add_argument('srt', metavar='SRTFILE', type=str, nargs='?',
                    help='The accompanying subtitles file in srt format (optional: will be guessed if not given)')
parser.add_argument('-s', '--subs',dest='subs', action='store_true',
                    help='embed hard-subs into the video')
parser.add_argument('-o', '--out',dest='outdir', action='store', type=str, nargs='?',
                    help='destination directory for clips. Defaults to the movie name + " clips" (or " betweens" for the -b mode)')
parser.add_argument('-t', '--twitter', action='store_true',
                    help='Convert video to best play on twitter')
parser.add_argument('-b', '--between', action='store_true',
                    help='Instead of extracting the dialogue clips, extract the parts between them')
parser.add_argument('--end-early', dest="endearly", action='store', nargs='?', type=float, default=0.3,
                    help='When extracting between-segments, end them early by this many seconds')
parser.add_argument('--min-length', dest="minlength", action='store', nargs='?', type=float, default=1.0,
                    help="When extracting between-segments, don't write any files that'd be shorter than this many seconds")
parser.add_argument('-m', '--match', metavar='PATTERN', action='store', type=str,
                    help='Only output clips matching a given pattern')
parser.add_argument('-r', '--replace', metavar='NEWSUBS', action='store', type=str,
                    help='Change the subtitles to this string. Use $NL for a newline. Implies -s')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Print output from ffmpeg, and command being run')

args = parser.parse_args()

if args.outdir is None:
	args.outdir = os.path.splitext(args.movie)[0]+(' betweens' if args.between else ' clips')
if args.srt is None:
	args.srt = os.path.splitext(args.movie)[0] + '.srt'
	if not os.path.exists(args.srt):
		print >>sys.stderr,"Couldn't find SRT file! (guessed {})".format(args.srt)
		print >>sys.stderr,"Please specify SRT path explicitly!"
		sys.exit(1)
if args.replace:
	args.subs=True

def clean(msg):
	msg=re.sub("[^a-zA-Z0-9,.']",' ',msg)
	msg=re.sub(' {2, }',' ',msg)
	return msg.strip(' .,')

def ftime(td):
	return td.seconds + td.microseconds/1000000.0

def quiet_erase(path):
	try:
		os.unlink(path)
	except OSError:
		pass

def quiet_mkdir(path):
	try:
		os.mkdir(path)
	except OSError:
		pass

with open(args.srt,'rb') as f:
	subtitles=srt.parse(f.read())

# Extract some basic info from the movie
info = json.loads(subprocess.check_output(['ffprobe','-v','quiet','-print_format','json','-show_format','-show_streams', args.movie]))
# time_base looks like "30/100" so it's safe to eval it.
offset = eval(info['streams'][0]['time_base']+'.0')
# offset is basically "one frame" in terms of time, and we use it to delay starting the crop, so we don't miss
# the first frame of subtitles. It's a hack, yes, but it seems to work.

EXTENSION = os.path.splitext(args.movie)[1]
if args.twitter:
	EXTENSION='.mp4'

quiet_mkdir(args.outdir)

match_pattern='*'
if args.match:
	match_pattern = '*{}*'.format(args.match)

if args.subs:
	# We need the subs in a filename with no spaces, because ffmpeg filter parsing is terrible
	# so we save it locally and then delete at the end.
	quiet_erase(TMPFILE)
	if args.replace:
		# We need to both cache the list of subtitles (so we can iterate it twice)
		# and generate a new SRT file for ffmpeg!
		subtitles = list(subtitles)
		modified_subs = []
		new_subtitle = args.replace.replace('$NL','\n')
		for e in subtitles:
			modified_subs.append(srt.Subtitle(e.index,e.start,e.end,new_subtitle,e.proprietary))
		with open(TMPFILE,'wb') as f:
			f.write(srt.compose(modified_subs))
	else:
		shutil.copy(args.srt, TMPFILE)
try:
	last_end = 0.0
	for entry in subtitles:
		if not fnmatch.fnmatchcase(entry.content, match_pattern):
			continue
		if args.between:
			name = 'between'
		else:
			name = clean(entry.content)
		filename='clip{:04} {}{}'.format(entry.index,name,EXTENSION)
		path = os.path.join(args.outdir,filename)
		if args.between:
			start_secs = last_end + offset
			end_secs = ftime(entry.start) - offset - args.endearly
			duration = end_secs - start_secs

			last_end = ftime(entry.end)
			if duration < args.minlength:
				continue

		else:

			start_secs = offset + ftime(entry.start)
			end_secs = ftime(entry.end)
		print filename

		cmd = ['ffmpeg', '-y']
		if not args.verbose:
			cmd.extend(['-hide_banner','-loglevel','panic','-v','quiet'])
		cmd.extend(['-i', args.movie])
		if args.subs:
			cmd.extend(['-vf','subtitles='+TMPFILE])
		cmd.extend(['-ss',str(start_secs),'-to',str(end_secs)])
		if args.twitter:
			cmd.extend([
			'-pix_fmt', 'yuv420p', '-vcodec', 'libx264',
			#'-vf', 'scale=640:-1',
			'-acodec', 'aac', '-vb', '1024k',
			'-minrate', '1024k', '-maxrate', '1024k',
			'-bufsize', '1024k', '-ar', '44100', '-ac', '2', '-strict', 'experimental', '-r', '30',
		])
		cmd.append(path)

		if args.verbose:
			print subprocess.list2cmdline(cmd)
		subprocess.check_call(cmd)

finally:
	if args.subs:
		quiet_erase(TMPFILE)
