#!/usr/bin/env python
"""
NOTE: many settings in here are specific to the NIKON3000 and will need to be 
tweaked for other cameras

TODO:
* slow down interval at night
* do an image diff between the past few images to see how fast things are
  changing.  If they are changing slowly, slow down the interval
* fix how the delay is computed (should just compute the time to sleep 
  directly instead of waiting by increments of 1 minute)
"""

from datetime import datetime, timedelta
import time
import subprocess
import sys
import os
from Shoot import Shoot

from argparse import ArgumentParser

import logging
import sun

DEBUG = False

# specify the path to the gphoto2 executable
gphoto2Executable = 'export LD_LIBRARY_PATH=/usr/local/lib; /usr/local/bin/gphoto2'

# Setup logger
logger = logging.getLogger('Capture')
logger.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# create handlers
streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.INFO)
streamHandler.setFormatter(formatter)

logger.addHandler(streamHandler)

parser = ArgumentParser()
parser.add_argument("configFile", help="XML configuration file", type=file)
parser.add_argument("-d", "--download", help="Download images on disk, don't actually capture", 
                    action="store_true")
parser.add_argument("--delete", help="When the 'download' option is enabled, this will also delete files OBfrom the folder", 
                    action="store_true")
parser.add_argument("-p", "--pi", help="Specifies that the program is run on the Raspberry Pi",
                    action="store_true")
parser.add_argument("-n", "--num-shots", help="Number of shots to capture (overrides XML file)", 
                    type=int)
parser.add_argument("-w", "--wait", help="Delay between shots in seconds (overrides XML file)",
                    type=int)
parser.add_argument("-i", "--initial-wait", help="Wait before doing anything (in seconds)", type=int, dest="initialWait")
parser.add_argument("-l", "--log", help="Log file", dest="logFilename")
args = parser.parse_args()

# Must we wait before starting?
if args.initialWait != None:
  time.sleep(args.initialWait)

# create file handler
if args.logFilename != None:
  fileHandler = logging.FileHandler(args.logFilename, mode='a')
  fileHandler.setLevel(logging.DEBUG)
  fileHandler.setFormatter(formatter)
  
  logger.addHandler(fileHandler)

# create a default Shoot object, read the XML file
shootInfo = Shoot()
shootInfo.fromXMLFile(args.configFile)

if args.num_shots != None:
  shootInfo.nbShots = args.num_shots
  
if args.wait != None:
  shootInfo.delay = timedelta(seconds = args.wait)

def run(cmd) :
  # try running the command once and if it fails, reset_camera
  # and then try once more
  logger.debug("running %s" % cmd)
    
  if not DEBUG: 
    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                       )
      
    
    (stdout, stderr) = p.communicate()
    ret = p.returncode
      
    if ret == 1:
      if 'No camera found' in stderr:
        raise RuntimeError('Error talking to the camera: ' + stderr)
      
    return stdout
  
  return ''

def readNumImagesFromCamera() :
  # not sure what's going on, but it's better to reset more than not enough I guess.
  reset()
  
  cmd = gphoto2Executable + " --folder=" + shootInfo.folder + " --num-files --quiet"
  numExistingImages = int(run(cmd))
  
  logger.debug("Found %d images on the folder %s" % (numExistingImages, shootInfo.folder))
  
  return numExistingImages

def takeShot(filename = None) :
  # if we're not downloading images, first check how many images there are in the destination folder
  prevExistingImages = 0
  if not shootInfo.downloadImages:
    prevExistingImages = readNumImagesFromCamera()
  
  logger.info('Taking %d exposure(s)', len(shootInfo.exposures))
  (call, filenames) = shootInfo.toGphotoCaptureCall(gphoto2Executable)
  
  run(call)
  
  if shootInfo.downloadImages:
    for filename in filenames:
      # check if images were correctly saved to disk
      if not os.path.exists(filename):
        raise RuntimeError('File not successfully saved to disk: ' + filename)
      else: 
        logger.debug('File successfully saved to disk: ' + filename)
        
    logger.info('Image(s) saved to %s', shootInfo.filename)
        
  else:
    # we're leaving the images on the camera. check if they were correctly captured. how?
    curNumExistingImages = readNumImagesFromCamera()
    
    if (curNumExistingImages-prevExistingImages) != len(shootInfo.exposures):
      raise RuntimeError('Not all images were captured on the camera!')
    else:
      logger.info('Image(s) saved to %s', shootInfo.folder) 
      
    
def reset():
  # use gphoto2's reset command (new with gphoto 2.5.2 and above)
  cmd = gphoto2Executable + ' --reset'
  run(cmd)
  
  run("killall PTPCamera")


def initialize() :
  logger.info('Initializing settings')
  
  if args.pi:
    # If we're on the Pi, disable the gphoto2 daemon process
    run("killall gphoto2")
    run("killall gvfsd-gphoto2")
    run("killall gvfs-gphoto2-volume-monitor")

  else:
    # In Mac OSX, disable the PTPCamera process
    run("killall PTPCamera")
    
  # Also, reset the usb to make sure everything works
  reset()
  
  # make sure picture mode is set to "faithful" (not sure if this affects RAW files...)
  # In our case, this should be equal to 5
  # TODO: add these checks to the configuration files
  #out = run(gphoto2Executable + " --get-config /main/capturesettings/picturestyle")
  #if not 'Current: Faithful' in out:
  #  raise RuntimeError('Camera needs to be set in the "Faithful" picture style')
  #logger.info('Camera in the faithful picture style')
  
  # we should also check whether we are in 'M' mode 
  out = run(gphoto2Executable + " --get-config /main/capturesettings/autoexposuremode")
  if not 'Current: Manual' in out:
    raise RuntimeError('Camera needs to be set in "Manual" mode')
  logger.info('Camera in manual mode')
    
  # set initialization configuration
  call = shootInfo.toGphotoInitCall(gphoto2Executable)
  run(call)
  
if args.download:
  if shootInfo.downloadImages:
    raise RuntimeError('Configuration file indicates that images should already be on disk')
  
  logger.info('Downloading files to disk from folder %s' % shootInfo.folder)

  reset()
  
  cmd = gphoto2Executable + " --folder=" + shootInfo.folder + " --get-all-files --force-overwrite"
  run(cmd)
  
  if args.delete:
    cmd = gphoto2Executable + " --folder=" + shootInfo.folder + " --delete-all-files"
    run(cmd)

  sys.exit()

# Display high-level information
logger.info('Taking a total of %d shots, and waiting %s between each shot', 
            shootInfo.nbShots, str(shootInfo.delay))
logger.info('Each shot will have %d exposure(s)', len(shootInfo.exposures))
  
initialize()

nbShots = 0
# loop until we have the required number of shots
while nbShots < shootInfo.nbShots:
  tInit = datetime.utcnow()
  
  # only take pictures when it is light out
  if shootInfo.ignoreSun or sun.is_light(tInit):
    # reset_camera()
    takeShot()
    nbShots += 1
  else :
    logger.info('Waiting for the sun to come out')
  
  if nbShots < shootInfo.nbShots:
    # wait only if we still need to shoot
    tCur = datetime.utcnow()
  
    tDelay = tCur - tInit
    if tDelay < shootInfo.delay:
      # wait only if the delay is larger than the time it took to take the shot (gphoto2 can be quite slow)
      waitTime = shootInfo.delay - tDelay
    
      logger.info('Waiting ' + str(waitTime.seconds) + 's...')
      time.sleep(waitTime.seconds)
      
logger.info('All done!')
    
