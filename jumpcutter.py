from contextlib import closing
from PIL import Image
from audiotsm import phasevocoder
from audiotsm.io.wav import WavReader, WavWriter
from scipy.io import wavfile
import numpy as np
from shutil import copyfile, rmtree
import os, subprocess, argparse, re, math
from pytube import YouTube
from tkinter import filedialog, simpledialog
from tkinter import *
def downloadFile(url):
    name = YouTube(url).streams.first().download()
    newname = name.replace(' ','_')
    os.rename(name,newname)
    return newname
def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)
def copyFrame(inputFrame,outputFrame):
    src = TEMP_FOLDER+"/frame{:06d}".format(inputFrame+1)+".jpg"
    dst = TEMP_FOLDER+"/newFrame{:06d}".format(outputFrame+1)+".jpg"
    if not os.path.isfile(src):
        return False
    copyfile(src, dst)
    if outputFrame%20 == 19:
        print(str(outputFrame+1)+" time-altered frames saved.")
    return True
def inputToOutputFilename(filename):
    dotIndex = filename.rfind(".")
    return filename[:dotIndex]+"_ALTERED"+filename[dotIndex:]
def createPath(s):
    try:  
        os.mkdir(s)
    except OSError:  
        assert False, "Creation of the directory %s failed. (The TEMP folder may already exist. Delete or rename it, and try again.)"
def deletePath(s): # Dangerous!
    try:  
        rmtree(s,ignore_errors=False)
    except OSError:  
        print ("Deletion of the directory %s failed" % s)
        print(OSError)
parser = argparse.ArgumentParser(description="Modifies a video file to play at different speeds when there is sound vs. silence.")
parser.add_argument('--input_file', type=str, help="the video file you want modified")
parser.add_argument('--url', type=str, help="A youtube url to download and process. Make sure to cut out the \"https://www.\" part.")
parser.add_argument('--output_file', type=str, default="", help="The output file. (optional. if not included, it'll just modify the input file name)")
parser.add_argument('--silent_threshold', type=float, default=0.03, help="The volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume)")
parser.add_argument('--sounded_speed', type=float, default=1.00, help="The speed that sounded (spoken) frames should be played at. Typically 1.")
parser.add_argument('--silent_speed', type=float, default=99999, help="The speed that silent frames should be played at. Enter nothing for just jumpcutting.")
parser.add_argument('--frame_margin', type=float, default=1, help="Make this 0 for the jumpiest footage, around 1 for normal, 2 if you're having some sounds cut out unintentionally, and >3 if you want it very smooth.")
parser.add_argument('--sample_rate', type=float, default=44100, help="Sample rate of the input and output videos")
parser.add_argument('--frame_rate', type=float, default=30, help="Frame rate of the input and output videos. optional... I try to find it out myself, but it doesn't always work.")
parser.add_argument('--frame_quality', type=int, default=2, help="Quality of frames to be extracted from input video. 1 is highest, 31 is lowest, 2 is the default.")
args = parser.parse_args()
choice=input("Jumpcutter made by carykh and ThatOneCalculator! Enter Y for youtube video, Q for quit, or anything else to choose a file\n\n").upper()
root=Tk()
root.wm_state("iconic") #gets rid of the stupid window
if choice == "Y":
	try:
		urlget = simpledialog.askstring("Input", "Enter URL", parent=root)
		if "youtube.com" not in urlget:
			quit()
		if "https://" in urlget:
			urlget = urlget.strip("https://")
		if "www." in urlget:
			urlget = urlget.strip("www.")
		if "youtube" not in urlget:
			quit()
		print("Downloading ",urlget)
	except:
		quit()
elif choice == "Q":
	quit()
else:
	root.filename =  filedialog.askopenfilename(initialdir = "/Desktop",title = "Select video file", filetypes = (("All files","*.*"),("MP4","*.mp4*")))
custom=input("Enter C for custom values, else hit enter").upper()
if custom=="C":
	frameRate = input("Enter frame rate. Leave blank for default.\n")
	if frameRate is None:
		frameRate=30
	SAMPLE_RATE = input("Enter sample rate. Leave blank for default.\n")
	if SAMPLE_RATE is None:
		SAMPLE_RATE=44100
	SILENT_THRESHOLD = input("Enter silent threshold. The volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume). Leave blank for default.\n")
	if SILENT_THRESHOLD is None:
		SILENT_THRESHOLD=0.03
	FRAME_SPREADAGE = input("Enter silent threshold. Leave blank for default.\n")
	if FRAME_SPREADAGE is None:
		FRAME_SPREADAGE=1
	silent_speed=input("Enter silent speed. Leave blank for default.\n")
	if silent_speed is None:
		silent_speed=99999
	sounded_speed=input("Enter sounded speed. The speed that sounded (spoken) frames should be played at. Typically 1. Leave blank for default.\n")
	if sounded_speed is None:
		sounded_speed=1
	NEW_SPEED = [silent_speed, sounded_speed]
	FRAME_QUALITY = input("Enter frame quality. Leave blank for default.\n")
	if FRAME_QUALITY is None:
		FRAME_QUALITY=2
else:
	frameRate = args.frame_rate
	SAMPLE_RATE = args.sample_rate
	SILENT_THRESHOLD = args.silent_threshold
	FRAME_SPREADAGE = args.frame_margin
	NEW_SPEED = [args.silent_speed, args.sounded_speed]
if choice == "Y":
	INPUT_FILE = downloadFile(urlget)
else:
	if root.filename is None:
		quit()
	else:
		INPUT_FILE=root.filename
URL = args.url
FRAME_QUALITY = args.frame_quality
assert INPUT_FILE != None , "Make sure there's an input file. Please don't run this via the shell, run it in CMD with `py jumpcutter.py -h`"
if len(args.output_file) >= 1:
    OUTPUT_FILE = args.output_file
else:
    OUTPUT_FILE = inputToOutputFilename(INPUT_FILE)
TEMP_FOLDER = "TEMP"
AUDIO_FADE_ENVELOPE_SIZE = 400
createPath(TEMP_FOLDER)
command = "ffmpeg -i "+INPUT_FILE+" -qscale:v "+str(FRAME_QUALITY)+" "+TEMP_FOLDER+"/frame%06d.jpg -hide_banner"
subprocess.call(command, shell=True)
command = "ffmpeg -i "+INPUT_FILE+" -ab 160k -ac 2 -ar "+str(SAMPLE_RATE)+" -vn "+TEMP_FOLDER+"/audio.wav"
subprocess.call(command, shell=True)
command = "ffmpeg -i "+TEMP_FOLDER+"/input.mp4 2>&1"
f = open(TEMP_FOLDER+"/params.txt", "w")
subprocess.call(command, shell=True, stdout=f)
sampleRate, audioData = wavfile.read(TEMP_FOLDER+"/audio.wav")
audioSampleCount = audioData.shape[0]
maxAudioVolume = getMaxVolume(audioData)
f = open(TEMP_FOLDER+"/params.txt", 'r+')
pre_params = f.read()
f.close()
params = pre_params.split('\n')
for line in params:
    m = re.search('Stream #.*Video.* ([0-9]*) fps',line)
    if m is not None:
        frameRate = float(m.group(1))
samplesPerFrame = sampleRate/frameRate
audioFrameCount = int(math.ceil(audioSampleCount/samplesPerFrame))
hasLoudAudio = np.zeros((audioFrameCount))
for i in range(audioFrameCount):
    start = int(i*samplesPerFrame)
    end = min(int((i+1)*samplesPerFrame),audioSampleCount)
    audiochunks = audioData[start:end]
    maxchunksVolume = float(getMaxVolume(audiochunks))/maxAudioVolume
    if maxchunksVolume >= SILENT_THRESHOLD:
        hasLoudAudio[i] = 1
chunks = [[0,0,0]]
shouldIncludeFrame = np.zeros((audioFrameCount))
for i in range(audioFrameCount):
    start = int(max(0,i-FRAME_SPREADAGE))
    end = int(min(audioFrameCount,i+1+FRAME_SPREADAGE))
    shouldIncludeFrame[i] = np.max(hasLoudAudio[start:end])
    if (i >= 1 and shouldIncludeFrame[i] != shouldIncludeFrame[i-1]):
        chunks.append([chunks[-1][1],i,shouldIncludeFrame[i-1]])
chunks.append([chunks[-1][1],audioFrameCount,shouldIncludeFrame[i-1]])
chunks = chunks[1:]
outputAudioData = np.zeros((0,audioData.shape[1]))
outputPointer = 0
lastExistingFrame = None
for chunk in chunks:
    audioChunk = audioData[int(chunk[0]*samplesPerFrame):int(chunk[1]*samplesPerFrame)]
    sFile = TEMP_FOLDER+"/tempStart.wav"
    eFile = TEMP_FOLDER+"/tempEnd.wav"
    wavfile.write(sFile,SAMPLE_RATE,audioChunk)
    with WavReader(sFile) as reader:
        with WavWriter(eFile, reader.channels, reader.samplerate) as writer:
            tsm = phasevocoder(reader.channels, speed=NEW_SPEED[int(chunk[2])])
            tsm.run(reader, writer)
    _, alteredAudioData = wavfile.read(eFile)
    leng = alteredAudioData.shape[0]
    endPointer = outputPointer+leng
    outputAudioData = np.concatenate((outputAudioData,alteredAudioData/maxAudioVolume))
    if leng < AUDIO_FADE_ENVELOPE_SIZE:
        outputAudioData[outputPointer:endPointer] = 0 # audio is less than 0.01 sec, let's just remove it.
    else:
        premask = np.arange(AUDIO_FADE_ENVELOPE_SIZE)/AUDIO_FADE_ENVELOPE_SIZE
        mask = np.repeat(premask[:, np.newaxis],2,axis=1) # make the fade-envelope mask stereo
        outputAudioData[outputPointer:outputPointer+AUDIO_FADE_ENVELOPE_SIZE] *= mask
        outputAudioData[endPointer-AUDIO_FADE_ENVELOPE_SIZE:endPointer] *= 1-mask
    startOutputFrame = int(math.ceil(outputPointer/samplesPerFrame))
    endOutputFrame = int(math.ceil(endPointer/samplesPerFrame))
    for outputFrame in range(startOutputFrame, endOutputFrame):
        inputFrame = int(chunk[0]+NEW_SPEED[int(chunk[2])]*(outputFrame-startOutputFrame))
        didItWork = copyFrame(inputFrame,outputFrame)
        if didItWork:
            lastExistingFrame = inputFrame
        else:
            copyFrame(lastExistingFrame,outputFrame)
    outputPointer = endPointer
wavfile.write(TEMP_FOLDER+"/audioNew.wav",SAMPLE_RATE,outputAudioData)
command = "ffmpeg -framerate "+str(frameRate)+" -i "+TEMP_FOLDER+"/newFrame%06d.jpg -i "+TEMP_FOLDER+"/audioNew.wav -strict -2 "+OUTPUT_FILE
subprocess.call(command, shell=True)
deletePath(TEMP_FOLDER)