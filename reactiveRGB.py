import tkinter as tk
from tkinter.filedialog import askopenfilename
from PIL import Image
import numpy as np
import cv2
from ctypes import WinDLL
import ctypes
import os
from multiprocessing import Pool
import time
from scipy.io import wavfile
from scipy import signal
import subprocess
import yaml
import winsound
# import moviepy.editor as mp

rgbhuetransform = WinDLL("./rgbhuetransform.so")
rgbhuetransform.TransformImageHSV.argtypes = np.ctypeslib.ndpointer(dtype=ctypes.c_int), ctypes.c_int, ctypes.c_int,ctypes.c_bool
rgbhuetransform.TransformImageHSV.restype = None
rgbhuetransform.TransformImageHSL.argtypes = np.ctypeslib.ndpointer(dtype=ctypes.c_int), ctypes.c_int, ctypes.c_float, ctypes.c_float, ctypes.c_float,ctypes.c_int
rgbhuetransform.TransformImageHSL.restype = None
rgbhuetransform.LinearAdd.argtypes = np.ctypeslib.ndpointer(dtype=ctypes.c_int), np.ctypeslib.ndpointer(dtype=ctypes.c_int), ctypes.c_int, ctypes.c_float, ctypes.c_bool,ctypes.c_bool
rgbhuetransform.LinearAdd.restype = None
rgbhuetransform.AudioFormatter.argtypes = np.ctypeslib.ndpointer(dtype=ctypes.c_float), np.ctypeslib.ndpointer(dtype=ctypes.c_float), np.ctypeslib.ndpointer(dtype=ctypes.c_float), np.ctypeslib.ndpointer(dtype=ctypes.c_float), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
rgbhuetransform.AudioFormatter.restype = None

class ReactiveRGB:
    #files and file accesories
    backgroundFile = None #main image
    changeAreaFile = None #change base colour
    changeAreaMask = False #whether to change the main area or replace it
    glowAreaFile = None #add colour on top of
    audio = None #audio file

    #imagedata
    backgroundData = None
    changeAreaData= None
    glowAreaData= None

    changeAreaBlurredData = None


    #settings
    config={}
    # frameRate:int = 30
    # rainbowRate:int = 4 #number of seconds on average to do a full colour rotation
    # changeAreaGlowMin:int = 10      #min change area opacity
    # changeAreaGlowMax:int = 100     #max change area opacity
    # changeAreaGlowRadius:int = 20   #gaussian blur radius
    # changeAreaGlowBase:int = 50    #percent of glow
    # changeAreaGlowLinAdd:int = 30   #percent of linadd
    # glowAreaMin:int = 0             #min opacity of glow
    # glowAreaMax:int = 100           #max opacity of glow
    # dbPercentileFloor:int = 10      #percentage of frames considered 0
    # dbPercentileCeiling:int = 90    #percentage of frames considered 100
    # glowMaxIncrease:int = 50          #highest amount of glow change from frame to frame
    # glow2MaxIncrease:int = 50         #highest amount of glow2 change from frame to frame
    # glowMaxDecrease:int = 10          #highest amount of glow change from frame to frame
    # glow2MaxDecrease:int = 10         #highest amount of glow2 change from frame to frame

    # maxBoom:int = 5                #how much it can grow (100 is double height and width)
    # boomSensitivity = 50
    # boomP:int=10            #highest amount of boom change from frame to frame
    # boomI:int=30         #highest amount of boom change from frame to frame
    # boomD:int =50             #the smallest difference in boom to even bother trying to change it 

    # threadCount:int = 20             #max number of threads to use 
    # maxRAM:int = 12                 #max amount of ram usage, in GB

    # eqRainbow:list = [100,100,100,100,100,100,100,100,100,100]
    # eqGlow:list = [100,100,100,100,100,100,100,100,100,100]
    # eqGlow2:list = [100,100,100,100,100,100,100,100,100,100]
    # eqBoom:list = [100,50,0,0,0,0,0,0,0,0]

    EQFREQS = [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]

    def __init__(self):
        if not os.path.exists("temp"):
            os.makedirs("temp")
        if not os.path.exists("output"):
            os.makedirs("output")
        if not os.path.exists("config.txt"):
            os.popen('copy defaultconfig.txt config.txt')
            time.sleep(1)
        self.loadConfig()
        
        print(self.config)



    def preProcessImageFile(self,filename):
        return Image.open(filename).convert('RGBA')
        # newImage = Image.open(filename)
        # if newImage.has_transparency_data:
        #     return newImage
        # output = Image.new("RGBA",newImage.size)
        # output.paste(newImage)
        # return output

    def setBackground(self, filename):
        self.backgroundFile = filename
        self.backgroundData = self.preProcessImageFile(filename)

    def setChangeArea(self, filename):
        self.changeAreaFile = filename
        if self.changeAreaMask:
            self.changeAreaData = Image.new("RGBA",size = self.backgroundData.size)
            mask = self.preProcessImageFile(filename)
            mask = mask.convert("L")
            self.changeAreaData.paste(self.backgroundData, mask = mask)
        else:
            self.changeAreaData = self.preProcessImageFile(filename)

    def setChangeAreaMask(self, setting):
        self.changeAreaMask = setting
        self.setChangeArea(self.changeAreaFile)

    def setGlowArea(self, filename):
        self.glowAreaFile = filename
        self.glowAreaData = self.preProcessImageFile(filename)

    def setAudio(self, filename):
        self.audio = filename

    def loadConfig(self):
        with open("config.txt") as f:
            self.config = yaml.safe_load(f)

    def saveConfig(self):
        with open("config.txt", "w") as f:
            yaml.safe_dump(self.config, f)
    def resetConfig(self):
        os.popen('copy defaultconfig.txt config.txt')
        time.sleep(1)
        self.loadConfig()

    def setConfig(self,key:str,val:int):
        self.config[key] = val
    def setConfigInt(self,key:str,val:int):
        self.config[key] = int(val)
    def setFrameRate(self,val:int):
        self.config["frameRate"] = int(val)
    def setRainbowRate(self,val:int):
        self.config["rainbowRate"] = int(val)
    def setChangeAreaGlowMin(self,val:int):
        self.config["changeAreaGlowMin"] = int(val)
    def setChangeAreaGlowMax(self,val:int):
        self.config["changeAreaGlowMax"] = int(val)
    def setChangeAreaGlowRadius(self,val:int):
        self.config["changeAreaGlowRadius"] = int(val)
    def setChangeAreaGlowBase(self,val:int):
        self.config["changeAreaGlowBase"] = int(val)
    def setChangeAreaGlowLinAdd(self,val:int):
        self.config["changeAreaGlowLinAdd"] = int(val)
    def setGlowAreaMin(self,val:int):
        self.config["glowAreaMin"] = int(val)
    def setGlowAreaMax(self,val:int):
        self.config["glowAreaMax"] = int(val)
    def setMaxBoom(self,val:int):
        self.config["maxBoom"] = int(val)
    def setDbPercentileFloor(self,val:int):
        self.config["dbPercentileFloor"] = int(val)
    def setDbPercentileCeiling(self,val:int):
        self.config["dbPercentileCeiling"] = int(val)
    def setGlowMaxIncrease(self,val:int):
        self.config["glowMaxIncrease"] = int(val)
    def setGlow2MaxIncrease(self,val:int):
        self.config["glow2MaxIncrease"] = int(val)
    def setGlowMaxDecrease(self,val:int):
        self.config["glowMaxDecrease"] = int(val)
    def setGlow2MaxDecrease(self,val:int):
        self.config["glow2MaxDecrease"] = int(val)
    def setBoomSensitivity(self,val:int):
        self.config["boomSensitivity"] = int(val)    
    def setBoomP(self,val:int):
        self.config["boomP"] = int(val)    
    def setBoomI(self,val:int):
        self.config["boomI"] = int(val)
    def setBoomD(self,val:int):
        self.config["boomD"] = int(val)
    def setThreadCount(self,val:int):
        self.config["threadCount"] = int(val)
    def setMaxRAM(self,val:int):
        self.config["maxRAM"] = int(val)
    def setEqGlow(self,vals:list):
        self.config["eqGlow"] = vals
    def setEqGlow(self, pos:int, val:int):
        self.config["eqGlow"][pos] = int(val)
    def setEqGlow2(self,vals:list):
        self.config["eqGlow2"] = vals
    def setEqGlow2(self, pos:int, val:int):
        self.config["eqGlow2"][pos] = int(val)
    def setEqBoom(self,vals:list):
        self.config["eqBoom"] = vals
    def setEqBoom(self, pos:int, val:int):
        self.config["eqBoom"][pos] = int(val)
    def setEqRainbow(self,vals:list):
        self.config["eqRainbow"] = vals
    def setEqRainbow(self, pos:int, val:int):
        self.config["eqRainbow"][pos] = int(val)

class Frame():
    hue = 0
    glow = 100
    boom = 0
    wobble = 0
    tilt = 0

    def __init__(self, hue:int=0,glow:int=100,boom:int=0,wobble:int=0,tilt:int=0) -> None:
        self.hue = int(hue%360)
        
        if glow>100:
            glow = 100
        elif glow<0:
            glow = 0
        self.glow = int(glow)
        if boom>100:
            boom = 100
        elif boom<0:
            boom = 0
        self.boom = int(boom)
        self.wobble = int(wobble)
        self.tilt = int(tilt)
    def __str__(self) -> str:
        return f'h{self.hue}g{self.glow}b{self.boom}w{self.wobble}t{self.tilt}'
    def setGlow(self, val):
        val = int(val)
        if val>100:val=100
        elif val<0:val=0
        self.glow = val


class AudioData():
    project:ReactiveRGB = None
    audioData = None
    # audioSorted = None
    totals = None
    frameCount = None
    runningTotals = None
    glowSorted = None
    glow2Sorted = None
    boomSorted = None

    def __init__(self, project:ReactiveRGB):
        self.project = project
        if self.project.audio.split(".")[-1].lower() == "wav":
            sf, audio = wavfile.read(self.project.audio)
        else:
            subprocess.call(['ffmpeg', '-i', self.project.audio,
                    'temp/tempaudio.wav'])
            sf, audio = wavfile.read('temp/tempaudio.wav')
            os.remove('temp/tempaudio.wav') 

        sig = np.mean(audio, axis=1)
        npts = int(sf/self.project.config["frameRate"])
        f, t, Sxx = signal.spectrogram(sig, sf, nperseg=npts,nfft=npts*4)

        self.frameCount = int(t[-2]*self.project.config["frameRate"])
        adata = np.zeros((self.frameCount,10), dtype=np.single)
        f = np.single(f)
        t = np.single(t)
        Sxx = np.single(Sxx)
        rgbhuetransform.AudioFormatter(adata, Sxx, f, t, self.frameCount, len(t), len(f), self.project.config["frameRate"])

        self.audioData = adata.astype(float)
        # np.savetxt("audios.csv", self.audioData, delimiter=",") #sometimes a gal's gotta just see the data
        self.totals = [0,0,0,0,0,0,0,0,0,0]
        self.runningTotals = []
        print(self.audioData.shape)
        for row in range(self.audioData.shape[0]):
            thisLine = []
            for col in range(self.audioData.shape[1]):
                self.totals[col] = self.totals[col] + self.audioData[row][col]
                thisLine.append(self.totals[col])
            self.runningTotals.append(thisLine)
        # self.audioSorted = self.audioData.copy()
        # sidx = self.audioSorted.argsort(axis=0)
        # self.audioSorted = self.audioSorted[sidx, np.arange(sidx.shape[1])]
        self.glowSorted = []
        self.glow2Sorted = []
        self.boomSorted = []
        total = 0
        totalweight =0
        for row in range(self.audioData.shape[0]):
            total = 0
            totalweight =0
            for freq in range(10):
                total = total + self.project.config["eqGlow"][freq]*self.audioData[row][freq]
                totalweight = totalweight + self.project.config["eqGlow"][freq]
            self.glowSorted.append(total/totalweight)
            total = 0
            totalweight =0
            for freq in range(10):
                total = total + self.project.config["eqGlow2"][freq]*self.audioData[row][freq]
                totalweight = totalweight + self.project.config["eqGlow2"][freq]
            self.glow2Sorted.append(total/totalweight)
            total = 0
            totalweight =0
            for freq in range(10):
                total = total + self.project.config["eqBoom"][freq]*self.audioData[row][freq]
                totalweight = totalweight + self.project.config["eqBoom"][freq]
            self.boomSorted.append(total/totalweight)
        # with open("glowIntensityunsort.csv","w") as f:
        #     for line in self.glowSorted:
        #         f.write(f'{line}\n')
        self.glowSorted.sort()
        self.glow2Sorted.sort()
        self.boomSorted.sort()
        # with open("glowIntensity.csv","w") as f:
        #     for line in self.glowSorted:
        #         f.write(f'{line}\n')
        
        self.boomProcessed = []
        for i in range(self.audioData.shape[0]):
            self.boomProcessed.append(self.boom(i))

        if self.project.config["boomwinlen"]>1:  
            self.boomProcessed = signal.savgol_filter(self.boomProcessed,self.project.config["boomwinlen"],self.project.config["boompolyorder"], deriv=self.project.config["boomderiv"] , delta=self.project.config["boomdelta"])
            self.boomProcessed = self.boomProcessed.tolist()
            for i in range(abs(self.project.config["boomoffset"])):
                if self.project.config["boomoffset"]>0:
                    self.boomProcessed.insert(0,0)
                    self.boomProcessed.pop()
                elif self.project.config["boomoffset"]<0:
                    self.boomProcessed.append(0)
                    self.boomProcessed.pop(0)
        self.boomProcessed =rescaleList(self.boomProcessed,0,100,True)
                

    def hueProgression(self,frame)->int:
        total = 0.0
        totalweight = 0.0
        for freq in range(10):
            total = total + self.project.config["eqRainbow"][freq]*self.runningTotals[frame][freq]/self.totals[freq]
            totalweight = totalweight + self.project.config["eqRainbow"][freq]
        hue= ((self.frameCount/self.project.config["frameRate"]/self.project.config["rainbowRate"])*360*(total/totalweight))%360
        return hue
    
    def glow(self,frame)->int:
        total = 0.0
        totalweight = 0.0
        for freq in range(10):
            total = total + self.project.config["eqGlow"][freq]*self.audioData[frame][freq]
            totalweight = totalweight + self.project.config["eqGlow"][freq]

        if totalweight==0 or total==0: return 0

        glow = self.project.config["changeAreaGlowMin"] + (self.project.config["changeAreaGlowMax"] - self.project.config["changeAreaGlowMin"]) * (total/totalweight-self.glowSorted[int(len(self.glowSorted)*self.project.config["dbPercentileFloor"]/100)])/(self.glowSorted[int(len(self.glowSorted)*self.project.config["dbPercentileCeiling"]/100)]-self.glowSorted[int(len(self.glowSorted)*self.project.config["dbPercentileFloor"]/100)]) 
        if glow<0:glow=0
        elif glow>100:glow=0
        return int(glow)
    
    def boom(self,frame)->int:
        total = 0.0
        totalweight = 0.0
        for freq in range(10):
            total = total + self.project.config["eqBoom"][freq]*self.audioData[frame][freq]
            totalweight = totalweight + self.project.config["eqBoom"][freq]

        if totalweight==0 or total==0: return 0
        boom = (total/totalweight-self.boomSorted[int(len(self.boomSorted)*self.project.config["dbPercentileFloor"]/100)])/(self.boomSorted[int(len(self.boomSorted)*self.project.config["dbPercentileCeiling"]/100)]-self.boomSorted[int(len(self.boomSorted)*self.project.config["dbPercentileFloor"]/100)])*100
        if boom<0:boom=0
        elif boom>100:boom=0
        return int(boom)

def rescaleList(things:list,newMin,newMax,isInt:bool = False):
    oldMax = max(things)
    oldMin = min(things)
    m = (newMax-newMin)/(oldMax-oldMin)
    b = newMin-oldMin*(newMax-newMin)/(oldMax-oldMin)
    for thing in range(len(things)):
        things[thing] = m*things[thing]+b
        if isInt:things[thing]=int(things[thing])
    return things

def preProcessStack(project:ReactiveRGB):
    if project.changeAreaFile:
        project.changeAreaBlurredData = Image.fromarray(cv2.blur(np.array(project.changeAreaData),(project.config["changeAreaGlowRadius"],project.config["changeAreaGlowRadius"])))
    
def processFrame(project:ReactiveRGB, frame:Frame)-> Image:
    # print("--------------------------")
    # t = time.time_ns()
    newImage = project.backgroundData.copy()
    if project.changeAreaData:

        # blurred part
        alpha=(project.config["changeAreaGlowBase"] * (project.config["changeAreaGlowMin"] + frame.glow*float(project.config["changeAreaGlowMax"] - project.config["changeAreaGlowMin"])/100)/10000)
        if(alpha>0):
            changearea = shiftColour(project.changeAreaBlurredData,frame.hue)
            newblur = project.backgroundData.copy()
            newblur.paste(changearea,mask=changearea)
            newImage = Image.blend(newImage, newblur, alpha=(project.config["changeAreaGlowBase"] * (project.config["changeAreaGlowMin"] + frame.glow*float(project.config["changeAreaGlowMax"] - project.config["changeAreaGlowMin"])/100)/10000))
        
        # regular part
        changearea = shiftColour(project.changeAreaData,frame.hue)
        newImage.paste(changearea,mask=changearea)

        #linear
        alpha=project.config["changeAreaGlowLinAdd"] * (project.config["changeAreaGlowMin"] + frame.glow*float(project.config["changeAreaGlowMax"] - project.config["changeAreaGlowMin"])/100)/10000
        if(alpha>0):
            changearea = shiftColour(project.changeAreaBlurredData,frame.hue)
            newImage = linearAdd(newImage,changearea,alpha)
        
    if project.glowAreaData:
        alpha=(project.config["glowAreaMin"] + frame.glow*float(project.config["glowAreaMax"] - project.config["glowAreaMin"])/100)/100
        if(alpha>0):
            glowarea = shiftColour(project.glowAreaData,frame.hue)
            newImage = linearAdd(newImage,glowarea,alpha)

    if project.config["maxBoom"]>0 and frame.boom>0:
        scale = 1 + project.config["maxBoom"]*frame.boom/10000.0 
        imgArr = np.asarray(newImage)
        newArr = imgArr[int((newImage.size[1]-newImage.size[1]/scale)/2) :int((newImage.size[1]+newImage.size[1]/scale)/2), int((newImage.size[0]-newImage.size[0]/scale)/2) :int((newImage.size[0]+newImage.size[0]/scale)/2)]
        newImage = Image.fromarray(cv2.resize(newArr,( newImage.size[0],newImage.size[1])))

    # print(time.time_ns()-t)
    return newImage

def threadProcessFrame(things):
    project, frames = things
    output = []
    for frame in frames:
        output.append([frame[0], processFrame(project, frame[1])])
    return output
def tempSave(imgandname):
    imgandname[0].save(f"./temp/{imgandname[1]}.png")
#HSL version
def shiftColour(image:Image, hueShift:float, saturationShift:float=0.0, luminanceShift = 0.0)->Image:
    img = np.asarray(image, dtype=np.int32)
    # print(img.shape[0]*img.shape[1])
    # print(img[0][0])
    rgbhuetransform.TransformImageHSL(img,int(img.shape[0]*img.shape[1]), hueShift,saturationShift,luminanceShift, len(img[0][0]))
    return Image.fromarray(np.uint8(img))

def linearAdd(img:Image, imgadd:Image, alpha:float)->Image:
    if alpha>1:alpha=1
    elif alpha<0:alpha=0
    imgArr = np.asarray(img, dtype=np.int32)
    imgAddArr = np.asarray(imgadd, dtype=np.int32)
    rgbhuetransform.LinearAdd(imgArr,imgAddArr,int(imgArr.shape[0]*imgArr.shape[1]),alpha, True, True)

    return Image.fromarray(np.uint8(imgArr))

def PID(pid:list,pidsettings:list):
    current,target,errorlast,ierror = pid
    p,i,d = pidsettings
    error = target - current
    ierror+=error
    derror = error - errorlast
    output = p*error + i*ierror + d*derror
    return [int(output), target, error, ierror]

def preview(project:ReactiveRGB):
    processFrame(project,Frame(hue=0)).save("rainbowoutput1.png")
    processFrame(project,Frame(hue=85)).save("rainbowoutput2.png")
    processFrame(project,Frame(hue=170)).save("rainbowoutput3.png")

def render(project:ReactiveRGB):
    t =time.time_ns()
    p = Pool(project.config["threadCount"])

    #remove all temp files from any previous cancelled/crashed attempts
    for f in [os.path.join("./temp",f) for f in os.listdir("./temp")]:
        os.remove(f) 

    preProcessStack(project)

    frameOrder = []
    frames = {}
    if project.audio:
        audioData = AudioData(project)
        frameCount = audioData.frameCount
        print("making frames")
        lastGlow = 0

        for f in range(frameCount):

            hue = audioData.hueProgression(f)

            glow=audioData.glow(f)
            if lastGlow+project.config["glowMaxIncrease"]<glow: glow = lastGlow+project.config["glowMaxIncrease"]
            elif lastGlow-project.config["glowMaxDecrease"]>glow: glow = lastGlow-project.config["glowMaxDecrease"]
            lastGlow = glow

            if project.config["maxBoom"]>0: 
                boom = audioData.boomProcessed[f]

            else:
                boom = 0

            newFrame = Frame(hue, glow = glow,boom=boom)
            # print(newFrame)
            frameOrder.append(newFrame)
        for f in range(len(frameOrder)):
            # frameOrder[f].setGlow(100*frameOrder[f].glow/maxGlow)
            if frameOrder[f].__str__() not in frames:
                frames[frameOrder[f].__str__()] = {"frame":frameOrder[f],"num":0,"hasFile":False}
            frames[frameOrder[f].__str__()]['num']+=1
            frameOrder[f]=str(frameOrder[f])
        

    else:
        frameCount = project.config["frameRate"]*project.config["rainbowRate"]
        for f in range(frameCount):
            newFrame = Frame(hue=f*360/frameCount)
            frameOrder.append(newFrame.__str__())
            if newFrame.__str__() not in frames:
                frames[newFrame.__str__()] = {"frame":newFrame,"num":0,"hasFile":False}
            frames[newFrame.__str__()]['num']+=1
    print("frames made")

    vidname = f'./temp/temp{time.time()}.mp4'
    finalvidname = f'./output/output{time.time()}.mp4'

    video = cv2.VideoWriter(vidname,0,project.config["frameRate"],project.backgroundData.size)
    batchSize = project.config["maxRAM"]*1000000000/(project.backgroundData.size[0]*project.backgroundData.size[1]*4*4)
    batchCount = 0
    

    frameNum = 0
    workFrameNum = 0
    while batchSize*batchCount<frameCount:
        #prepping the frame work list list
        thisBatchSize = 0
        frameWork = []
        framesToDo = set()
        for i in range(project.config["threadCount"]):
            frameWork.append([project,[]])
        nextThread = 0
        while thisBatchSize<batchSize and workFrameNum<len(frameOrder):

            if not frames[frameOrder[workFrameNum]]["hasFile"] and frameOrder[workFrameNum] not in framesToDo:
                frameWork[nextThread][1].append([frameOrder[workFrameNum],frames[frameOrder[workFrameNum]]['frame']])
                framesToDo.add(frameOrder[workFrameNum])
                thisBatchSize+=1
                nextThread=(nextThread+1)%project.config["threadCount"]
            workFrameNum+=1


        #process all the new frames
        output = p.map(threadProcessFrame,frameWork)

        newFrames = {}
        for frameSet in output:
            for frame in frameSet:
                newFrames[frame[0]]=frame[1]
        
        while(frameNum<workFrameNum):
            #get images either from the new processed images or from disk
            if frameOrder[frameNum] in newFrames:
                thisFrame = np.asarray(newFrames[frameOrder[frameNum]], dtype=np.uint8)
            else:
                thisFrame = np.asarray(Image.open(f".temp/{frameOrder[frameNum]}.png"), dtype=np.uint8)

            #WHY DOES CV2 USE BGR
            thisFrame = cv2.cvtColor(thisFrame, cv2.COLOR_RGB2BGR)
            video.write(thisFrame)

            frames[frameOrder[frameNum]]["num"]-=1
            frameNum+=1
        #if any images will be used in the future, save them
        savelist = []
        for frame in newFrames.keys():
            if frames[frame]["num"]>0 and not frames[frame]["hasFile"]:
                savelist.append([newFrames[frame], frame])
        p.map(tempSave, savelist)
                
        
        batchCount+=1

    video.release()
    
    if project.audio:
        # with mp.VideoFileClip(vidname) as video:
        #     audio = mp.AudioFileClip(project.audio)
        #     video = video.set_audio(audio)
        #     video.write_videofile(finalvidname)
        subprocess.call(["ffmpeg", "-i", vidname, "-i", project.audio, "-c:v", "libx264", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", "-crf",str(project.config['crf']), finalvidname])
    else:
        subprocess.call(["ffmpeg", "-i", vidname, "-c:v", "libx264", "-crf", str(project.config['crf']), finalvidname])

    #remove all temp files
    for f in [os.path.join("./temp",f) for f in os.listdir("./temp")]:
        os.remove(f) 

    print(f"TIME: {(time.time_ns()-t)/1000000}ms")
    beep()

def beep():
    winsound.Beep(440, 200)
    winsound.Beep(880, 100)


def maskButton(button, project:ReactiveRGB):
    project.setChangeAreaMask(project.changeAreaMask == False)
    if project.changeAreaMask:
        button.config(relief="sunken")
    else:
        button.config(relief="raised")

def loadUI(ui, project:ReactiveRGB):
    project.loadConfig()
    for thing in ui.winfo_children():
        thing.destroy()
    populateUI(ui, project)

def resetUI(ui, project:ReactiveRGB):
    project.resetConfig()
    for thing in ui.winfo_children():
        thing.destroy()
    populateUI(ui, project)

def populateUI(ui, project):
        #images
    # minImage = tk.Label( ui ,height= 20)
    # midImage = tk.Label(ui ,height= 20)
    # maxImage = tk.Label(ui ,height= 20)
    # minImage.grid(column = 1)
    # midImage.grid(column = 1)
    # maxImage.grid(column = 1)

    #mainbuttons
    backgroundButton = tk.Button(ui, text='Background', width=25, command=lambda:project.setBackground(askopenfilename()))
    changeAreaButton = tk.Button(ui, text='Changing Area', width=25, command=lambda:project.setChangeArea(askopenfilename()))
    changeAreaMaskButton = tk.Button(ui, text='Changing Area is mask', width=25, command=lambda:maskButton(changeAreaMaskButton,project))
    glowAreaButton = tk.Button(ui, text='Glow Area', width=25, command=lambda:project.setGlowArea(askopenfilename()))
    audioFileButton = tk.Button(ui, text='Audio', width=25, command=lambda:project.setAudio(askopenfilename()))
    saveButton = tk.Button(ui, text="Save Settings", command=lambda:project.saveConfig())
    loadButton = tk.Button(ui, text="Load Settings", command=lambda:loadUI(ui,project))
    resetButton = tk.Button(ui, text="Reset Settings", command=lambda:resetUI(ui,project))
    setButton = tk.Button(ui, text="PREVIEW", command=lambda:preview(project))
    renderButton = tk.Button(ui, text="RENDER", command=lambda:render(project))
    # setButton = tk.Button(ui, text="SET", command=lambda:previewImage(minImage,midImage,maxImage,project))
    
    buttonList = [backgroundButton,changeAreaButton,changeAreaMaskButton , glowAreaButton,audioFileButton,saveButton,loadButton,resetButton,setButton,renderButton]
    i=0
    for num in range(len(buttonList)):
        buttonList[i].grid(row = i, column = 0)
        i+=1
        

    #sliders
    sliders = [
        # [label, description, start value, lambda, min, max]
        ["Frame Rate","",project.config["frameRate"],lambda val:project.setFrameRate(int(val)),1,100],
        ["crf","Video Quality",project.config["crf"],lambda val:project.setConfig("crf",int(val)),1,51],
        ["Rainbow Rate","Average number of seconds per rainbow rotation",project.config["rainbowRate"],lambda val:project.setRainbowRate(int(val)),0,100],
        ["Minimum Glow","min change area opacity",project.config["changeAreaGlowMin"],lambda val:project.setChangeAreaGlowMin(int(val)),0,100],
        ["Maximum Glow","max change area opacity",project.config["changeAreaGlowMax"],lambda val:project.setChangeAreaGlowMax(int(val)),0,100],
        ["Glow Radius","gaussian blur radius on glow",project.config["changeAreaGlowRadius"],lambda val:project.setChangeAreaGlowRadius(int(val)) ,0,100],
        ["Change Area Glow","Base Change Area Glow",project.config["changeAreaGlowBase"],lambda val:project.setChangeAreaGlowBase(int(val)),0,100],
        ["change Area linAdd","Glowy glow",project.config["changeAreaGlowLinAdd"],lambda val:project.setChangeAreaGlowLinAdd(int(val)),0,100],
        ["2nd Glow Area Min","",project.config["glowAreaMin"],lambda val:project.setGlowAreaMin(int(val)) ,0,100],
        ["2nd Glow Area Max","",project.config["glowAreaMax"],lambda val:project.setGlowAreaMax(int(val)),0,100],
        ["db floor","Percentage of values considered '0'",project.config["dbPercentileFloor"],lambda val:project.setDbPercentileFloor(int(val)) ,0,100],
        ["db ceiling","Percentage of values considered '100'",project.config["dbPercentileCeiling"],lambda val:project.setDbPercentileCeiling(int(val)),0,100],
        ["max glow increase","Max rate of glow increase",project.config["glowMaxIncrease"],lambda val:project.setGlowMaxIncrease(int(val)) ,0,100],
        ["max glow decrease","Max rate of glow decrease",project.config["glowMaxDecrease"],lambda val:project.setGlowMaxDecrease(int(val)) ,0,100],
        ["glow2 max increase","",project.config["glow2MaxIncrease"],lambda val:project.setGlow2MaxIncrease(int(val)),0,100],
        ["glow2 max decrease","",project.config["glow2MaxDecrease"],lambda val:project.setGlow2MaxDecrease(int(val)),0,100],
        ["Boom MAX","Maximum amount image can grow",project.config["maxBoom"],lambda val:project.setMaxBoom(int(val)),0,100],
        ["boomoffset","shift boom by frames",project.config["boomoffset"],lambda val:project.setConfig("boomoffset",int(val)),-50,50],
        ["boomwinlen","softening range for boom",project.config["boomwinlen"],lambda val:project.setConfig("boomwinlen",int(val)),1,100],
        ["boompolyorder","",project.config["boompolyorder"],lambda val:project.setConfig("boompolyorder",int(val)),1,10],
        ["boomderiv","",project.config["boomderiv"],lambda val:project.setConfig("boomderiv",int(val)),0,10],
        ["boomdelta","",project.config["boomdelta"],lambda val:project.setConfig("boomdelta",int(val)),0,10],
        ["thread count","",project.config["threadCount"],lambda val:project.setThreadCount(int(val)),1,64],
        ["max RAM (GB)","THIS IS AN ESTIMATE",project.config["maxRAM"],lambda val:project.setMaxRAM(int(val)),1,64]
    ]
    
    sliderObjects = []
    counter = 0
    for slider in sliders:
        newSlider = tk.Scale(ui, from_=slider[4], to=slider[5], orient=tk.HORIZONTAL, command= slider[3] )
        newSlider.grid(row = counter, column = 4)
        newLabel = tk.Label(text=slider[0])
        newLabel.grid(row =  counter, column=  3)
        newDescr = tk.Label(text=slider[1])
        newDescr.grid(row =  counter, column=  5)
        newSlider.set(slider[2])
        sliderObjects.append([newSlider,newLabel,newDescr])
        counter+=1

    eqRainbowParts = []
    eqRainbowLabel = tk.Label(text="Rainbow Reactivity")
    eqRainbowLabel.grid(row =  1, column=  6)
    for n in range(len(project.EQFREQS)):
        eqRainbowParts.append({})
        eqRainbowParts[n]['slider'] = tk.Scale(ui, from_=100, to=0, orient=tk.VERTICAL, command= lambda val:project.setEqRainbow(n, int(val)) )
        eqRainbowParts[n]['slider'].grid(row = 1, column = 7+n)
        eqRainbowParts[n]['slider'].set(project.config["eqRainbow"][n])
        eqRainbowParts[n]['label'] = tk.Label(text=project.EQFREQS[n])
        eqRainbowParts[n]['label'].grid(row =  2, column=  7+n)

    eqGlowParts = []
    eqGlowLabel = tk.Label(text="Glow Reactivity")
    eqGlowLabel.grid(row =  3, column=  6)
    for n in range(len(project.EQFREQS)):
        eqGlowParts.append({})
        eqGlowParts[n]['slider'] = tk.Scale(ui, from_=100, to=0, orient=tk.VERTICAL, command= lambda val:project.setEqGlow(n, int(val)) )
        eqGlowParts[n]['slider'].grid(row = 3, column = 7+n)
        eqGlowParts[n]['slider'].set(project.config["eqGlow"][n])
        eqGlowParts[n]['label'] = tk.Label(text=project.EQFREQS[n])
        eqGlowParts[n]['label'].grid(row =  4, column=  7+n)

    eqGlow2Parts = []
    eqGlow2Label = tk.Label(text="Glow2 Reactivity")
    eqGlow2Label.grid(row =  5, column=  6)
    for n in range(len(project.EQFREQS)):
        eqGlow2Parts.append({})
        eqGlow2Parts[n]['slider'] = tk.Scale(ui, from_=100, to=0, orient=tk.VERTICAL, command= lambda val:project.setEqGlow2(n, int(val)) )
        eqGlow2Parts[n]['slider'].grid(row = 5, column = 7+n)
        eqGlow2Parts[n]['slider'].set(project.config["eqGlow2"][n])
        eqGlow2Parts[n]['label'] = tk.Label(text=project.EQFREQS[n])
        eqGlow2Parts[n]['label'].grid(row =  6, column=  7+n)

    eqBoomParts = []
    eqBoomLabel = tk.Label(text="BOOM Reactivity")
    eqBoomLabel.grid(row =  7, column=  6)
    for n in range(len(project.EQFREQS)):
        eqBoomParts.append({})
        eqBoomParts[n]['slider'] = tk.Scale(ui, from_=100, to=0, orient=tk.VERTICAL, command= lambda val:project.setEqBoom(n, int(val)) )
        eqBoomParts[n]['slider'].grid(row = 7, column = 7+n)
        eqBoomParts[n]['slider'].set(project.config["eqBoom"][n])
        eqBoomParts[n]['label'] = tk.Label(text=project.EQFREQS[n])
        eqBoomParts[n]['label'].grid(row =  8, column=  7+n)


def UI(project:ReactiveRGB = None):
    if project is None: project = ReactiveRGB()
    ui = tk.Tk()
    ui.title('Rainbowing Audio')
    populateUI(ui, project)
    


    ui.mainloop()
if __name__ == "__main__":
    UI()