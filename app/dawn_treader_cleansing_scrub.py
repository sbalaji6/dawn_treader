import os
import time
#import mchammer.ex

from datetime import datetime
from dawn_treader_subprocess import call_subprocess

# directories - one for the usb installers, one for cached images
INSTALLER_DIR = "/installers"
CACHE_DIR = "/images"

# ignore the .snapshot directory as messing with it does bad, bad things
IGNORABLE_DIR_LIST = [".snapshot"]

# how much disk space use is allowed?
MAX_USAGE_AT_FIRST_RUN = 70
MAX_USAGE_AT_SUBSEQUENT_RUN = 40

MAX_USB_INSTALLERS = 4

# helper class used by the installer cleanser - it contains a path and an associated time
# and then an array of them can be sorted by the time.
#
# it also contains the ability to remove itself.

class dt_Build(object):
  def __init__(self, path, mtime):
    self.path = path
    self.mtime = mtime

  def remove_dir(self):
    # sudo shouldn't really be needed here but experimentally it is.

    # possibly should be done with os.walk and os.remove/os.rmdir, AND i don't feell ike it.
    r, out = call_subprocess("sudo rm -rf {}".format(self.path))

  def is_young(self):
     right_now = datetime.now()
     formation = datetime.fromtimestamp(self.mtime)
     time_since_formation = right_now - formation
     seconds_since_formation =  time_since_formation.total_seconds()
     print("elapsed seconds: {}".format(seconds_since_formation))
     #if seconds_since_formation < 172800:
     if seconds_since_formation < 86400:
        return True
     else:
        return False
     

# class used to cleanse the /installers directory of lingering USB installs.
# the idea is that whenever this is run, if there are more than MAX BUILDS, they get
# removed. then the cleanse is rerun with max builds decremented, until disk space use is OK.

class dt_InstallerCleanser(object):
   def __init__(self, path, altpath):
     # irritating hack.
     # the INSTALLER_DIR and the CACHE_DIR are the *same hardware*
     # but contain different things
     # unfortunately df is only showing one of them.
     # so things that check to see if disk space is impacted need to check both.
     self.path = path
     self.altpath = altpath

   def should_run_based_on_runtime(self):
     return False 

   def get_builds(self, product_dir):
     r = []
     subfiles = os.listdir(product_dir)
     for _file in subfiles:
      __file = os.path.join(product_dir, _file)
      if os.path.isdir(__file):
        build = dt_Build(__file, os.path.getmtime(__file))
        r.append(build)
     return r

   def prune_builds(self, product_dir, max_builds):
     print("pruning: {}".format(product_dir))
     builds = self.get_builds(product_dir)
     print("len: {}, max: {}".format(len(builds), max_builds))
     if len(builds) > max_builds:
       builds.sort(key=lambda x: x.mtime, reverse=True)
       for build in builds[max_builds:]:
         print("looking at {}".format(build.path))
         if not build.is_young():
           build.remove_dir()
     return True

   def get_product_dirs(self):
     r = []
     subfiles = os.listdir(self.path)
     for _file in subfiles:
       __file = os.path.join(self.path, _file)
       if os.path.isdir(__file) and not is_ignorable_dir(_file):
         r.append(__file)
     return r

   def prune_children(self, iteration_level):
     max_builds = MAX_USB_INSTALLERS - iteration_level
     product_dirs = self.get_product_dirs()
     for product_dir in product_dirs:
       print("checking {}".format(product_dir))
       self.prune_builds(product_dir, max_builds)
     return True

   def check_and_prune_children(self, iteration_level):
     if self.should_run_based_on_runtime() or disk_space_is_impacted(self.path, iteration_level):
       print("pruning children")
       self.prune_children(iteration_level)
     self.prune_children(iteration_level)

   def cleanse(self):
     print("cleansing")
     for i in range(1,3):
       self.check_and_prune_children(i)

#### class used for cleansing the cache
class dt_CacheCleanser(object):
  def __init__(self, path, altpath):
    self.path = path
    self.altpath = path

  def dt_is_running(self):
     return dt_is_running()

  def path_is_valid(self):
     if self.path is not None and os.path.isdir(self.path):
        return True
     else:
        return False

  def cleanse(self):
     if self.path_is_valid() and not self.dt_is_running():
        # NOTE - there's an assumption here that the cache will be cleansed only after
        # the user space has been cleansed.
        # that maens that disk_space_is_impacted(PATH, 1) will NEVER be true.
        if disk_space_is_impacted(self.path, 2) or disk_space_is_impacted(self.altpath, 2):
           self.cleanse_files()
        if disk_space_is_impacted(self.path, 2) or disk_space_is_impacted(self.altpath, 2):
           self.recleanse_files()
        if disk_space_is_impacted(self.path, 2) or disk_space_is_impacted(self.altpath, 2):
           self.rerecleanse_files()
       
  def cleanse_files(self):
     if self.path_is_valid():
        subfiles = os.listdir(self.path)
        for _file in subfiles:
          if is_client_or_server_file(_file):
             self.remove_file(_file)

  def recleanse_files(self):
    if self.path_is_valid():
       subfiles = os.listdir(self.path)
       for _file in subfiles:
         if not is_ignorable_dir(_file) and is_older_than_a_week(os.path.join(self.path,_file)):
            self.remove_file(_file)
       
  def rerecleanse_files(self):
    if self.path_is_valid():
       subfiles = os.listdir(self.path)
       for _file in subfiles:
         if not is_ignorable_dir(_file) and is_older_than_three_days(os.path.join(self.path,_file)):
            self.remove_file(_file)

  def remove_file(self, _file):
    r, out = call_subprocess("sudo rm -rf {}".format(_file))

# helper function - should this directory be ignored? 
def is_ignorable_dir(dirname):
  if dirname in IGNORABLE_DIR_LIST:
    return True
  else:
    return False

# helper function - is disk space impacted? check the output of df!
# note that df does wierd things when the same remote volume
# is mounted to two different local volumes, in which case
# you may need to run iteratively on both local volumes in order to tell
def disk_space_is_impacted(root_dir, iteration_level):
   print("calling df {}".format(root_dir))
   r, out = call_subprocess("df {0}".format(root_dir))

   # expeected output looks like this:
   # Filesystem                  1K-blocks     Used Available Use% Mounted on
   # fcna13:/vol/app_calcinstall 134479872 15726400 118753472  12% /installers

   # that makes the desired string the eleventh element of the array after splitting

   PERCENTAGE_LOCATION_IN_ARRAY = 11

   reports = out.split()
   percent_string = reports[PERCENTAGE_LOCATION_IN_ARRAY]
   stripped_percent_string = percent_string[:-1]
   percentage = int(stripped_percent_string)
   
   return _disk_space_is_impacted(percentage, iteration_level)

# helper function to check and see if the percentage returned by df is a problem. or not.
def _disk_space_is_impacted(percentage, iteration_level):
   print("percentage: {}, iteration_level: {}".format(percentage, iteration_level))
   if iteration_level == 1:
     if percentage > MAX_USAGE_AT_FIRST_RUN:
       print("disk space is impacted")
       return True
     else:
       return False
   elif iteration_level > 1:
     if percentage > MAX_USAGE_AT_SUBSEQUENT_RUN:
       print("disk space is impacted")
       return True
     else:
       return False
   else:
     # what does it mean to have zero or negative iteration level?
     return False

# helper function to check and see if dawn_treader is running.
# this works by grabbing the output of ps and counting the number
# of instances of dawn_treader. if it's more than one, then something
# dawn-treaderish OTHER than this script is running, which 
# the script assumes means dawn_treader is running.
def dt_is_running():
  r, out = call_subprocess("ps ax")
  dt_count = 0
  for _line in out:
    if _line.find("dawn_treader") > -1:
      dt_count = dt_count + 1
  if dt_count > 0:
    return True
  else:
    return False

# helper function to tell if an image file is of a client or server ISO.
# the idea is that these should be deleted FIRST as they're least likely to get
# reused.
def is_client_or_server_file(_file):
   for prefix in ["client.", "server."]:
     if _file.find(prefix) > -1:
       return True
   return False

### helper function to tell if a file is older than seven days old.
def is_older_than_a_week(_file):
   if get_age_of_file_in_days(_file) > 7:
      return True
   else:
      return False

### helper function to tell if a file is older than three days old.
def is_older_than_three_days(_file):
   if get_age_of_file_in_days(_file) > 3:
      return True
   else:
      return False

### helper functions to get the number of days old a file is.
### this has a bug involving leap days, in that it IGNORES THEM.
### so the actual number is going to be slightly off.
### but for the purposes of this script, that's ok, since the idea
### is to compare two dates, and unless the anomaly occurs between
### the two, no harm done.

def get_age_of_file_in_days(_file):
   file_days = get_num_of_days(os.path.getctime(_file))
   cur_days = get_num_of_days(time.time())
   return cur_days - file_days

def get_num_of_days(age):
  _age = time.gmtime(age)
  r = (_age.tm_year * 365) + (_age.tm_mon * 12) + _age.tm_mday
  return r


# main program - get an installer cleanser and an image cleanser and run both of them
print "welcome to the dawn treader cleanser\n"

installer_cleanser = dt_InstallerCleanser(INSTALLER_DIR, CACHE_DIR)
installer_cleanser.cleanse()

cache_cleanser = dt_CacheCleanser(CACHE_DIR, INSTALLER_DIR)
cache_cleanser.cleanse()


print "au revoir.\n"
