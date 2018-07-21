from fractions import Fraction
from collections import OrderedDict
import skvideo
import pickle
import numpy
import json

# Script to to pair actions with video recording
# All times are in ms and we assume a actions list, a timestamp file, and a dis-syncronous mp4 video

filename = 'corrupt_bread_deamon'

# Load actions
#actions, timestamps = pickle.load(open("./actions.pkl", 'wb'))
actions = []
timestamps = range(start=1052, stop = 600000, step=49)

# Load video
videogen = skvideo.io.vreader("./recording.mp4")
metadata = skvideo.io.ffprobe("./recording.mp4")

# Load Markers
markers = json.load("./markers.json")


# Generate recording segments
# Sorted pairs of (start, stop, exprementName) timestamps (in ms)
segments = []

markers = OrderedDict()
for marker in json.load(open('./markers.json')):
    markers[marker['realTimestamp']] = marker

startTime = None
experementName = ""
for key, marker in sorted(markers.items()):

    expName = ""
    # Get experement name (its a malformed json so we have to look it up by hand)
    if 'value' in marker and 'metadata' in marker['value'] and 'expMetadata' in marker['value']['metadata']:
        marker = marker['value']['metadata']
        malformedStr = marker['expMetadata']
        expName = json.loads(malformedStr[malformedStr.find('experimentMetadata')+19:-1])['experement_name']

    if 'startRecording' in marker and marker['startRecording']:
        # If we encounter a start marker after a start marker there is an error and we should throw away this segemnt
        startTime = key
        experementName = expName
    
    if 'stopRecording' in marker and marker['stopRecording'] and startTime != None:
        #Experement name should be the same
        if experementName == expName:
            segments.append((startTime,startTime, expName))



# Frames per second expressed as a fraction, e.g. 25/1
fps = float(sum(Fraction(s) for s in metadata['video']['r_frame_rate'].split()))
timePerFrame = 1000 / fps
videoOffset = 1000
numFrames = metadata['video']['nb_frames']

actionTime = iter(zip(timestamps, actions))
currentTimestamp = 0 # Timestamps index
currentFrame = 0     # videogen index
frame = None
action = None

print("Video has", numFrames, "at", fps, "fps")

for pair in segments:
    print("Segment:", pair[0], "-", pair[1], pair[2])
    sarsa_pairs = []
    startTime = pair[0]
    stopTime = pair[1]
    experementName = pair[2]

    # Move timestamp file to start time
    while (currentTimestamp < startTime):
        try:
            (currentTimestamp, action) = next(actionTime)
        except StopIteration:
            # Be lazy
            print("ERROR")
            print("Could not get enough timestamp action pairs")
            exit(-1)

    # Record the aciton pair 
    while (currentTimestamp <= stopTime):
        # Get the closest frame
        frameNum = int(round((currentTimestamp - videoOffset) / timePerFrame))
        while (frameNum > currentFrame) :
            try:
                frame = next(videogen)
                currentFrame += 1
            except StopIteration:
                # Be lazy
                print("ERROR PARSING VIDEO")
                print("Could not get enough frames to fill timestamp file")
                exit(-1)

        # Generate numpy pair and append 
        if (currentFrame != None and action != None):
            sarsa = (currentFrame, action)
            sarsa_pairs.append(sarsa)

        # Itterate action and timestamp
        try:
            (currentTimestamp, action) = next(actionTime)
        except StopIteration:
            break

    outFile = open('../data/{}/{}.npy'.format(experementName,filename), 'w+')
    numpy.save(outFile, sarsa_pairs)

    

    

        
