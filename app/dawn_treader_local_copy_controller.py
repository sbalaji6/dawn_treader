import os

from dawn_treader_credentials import PROD_RMS_FTP_CREDS_FILE
from dawn_treader_credentials import LOCAL_RMS_FTP_CREDS_FILE

# netapp support is entirely mythological as of 10/7/2015, and strikes me as likely
# to remain so. 

class DawnTreaderRMSLocalCopyController(object):
  def __init__(self):
     self.local_rms_netapp_mount = False
     self.local_rms_ftp_capacity = False

  def has_local_rms_netapp_mount(self):
     return self.local_rms_netapp_mount

  def has_local_rms_ftp_capacity(self):
     return self.local_rms_ftp_capacity

  def ignore_local_copy_capacities(self):
     self.local_rms_netapp_mount = false
     self.local_rms_ftp_capacity = false

  def use_local_copy_capacities(self):
     self.local_rms_netapp_mount = self.check_for_local_netapp_mount()
     self.local_rms_ftp_capacity = self.check_for_local_rms_ftp_capacity()
     # print "local_rms_ftp_capacity: {}, local_rms_netapp_mount: {}\n".format(self.local_rms_ftp_capacity, self.local_rms_netapp_mount)

  def check_for_local_netapp_mount(self):
     return False
  
  def check_for_local_rms_ftp_capacity(self):
     if os.path.exists(LOCAL_RMS_FTP_CREDS_FILE):
        print "local rms ftp credential file {} found\n".format(LOCAL_RMS_FTP_CREDS_FILE)
        return True
     elif os.path.exists(PROD_RMS_FTP_CREDS_FILE):
        print "production rms ftp credential file {} found\n".format(PROD_RMS_FTP_CREDS_FILE)
        return True
     else:
        return False

#### YAY! A SINGLETON.
#### in theory this is bad thing, because it's an unprotected
#### global variable. boo.
#
#### and yet on the other hand, passing this down to everything and everyone is annoying
#### and creates some really cumbersome function logic.
#### and it's really NOT part of the ISO set OR something clients of the ISO set should need
#### to know about - it's a global state consideration.
####
#### maybe there should be a global state object, but i'm not there yet.

# PLEASE DO NOT EXPORT THIS SINGLETON. provide accessor functions instead!
RMS_local_copy_controller = DawnTreaderRMSLocalCopyController()

def get_rms_credential_file():
   if os.path.exists(LOCAL_RMS_FTP_CREDS_FILE):
      return LOCAL_RMS_FTP_CREDS_FILE
   elif os.path.exists(PROD_RMS_FTP_CREDS_FILE):
      return PROD_RMS_FTP_CREDS_FILE
   else:
      return NONE

def use_local_copy_capacities():
    RMS_local_copy_controller.use_local_copy_capacities()

def using_local_rms_ftp_capacity():
   # print "using_local_rms_ftp_capacity:: {}\n".format(RMS_local_copy_controller.has_local_rms_ftp_capacity())
   return RMS_local_copy_controller.has_local_rms_ftp_capacity()

def using_local_rms_netapp_mount():
   # print "using_local_rms_netapp_mount:: {}\n".format(RMS_local_copy_controller.has_local_rms_netapp_mount())
   return RMS_local_copy_controller.has_local_rms_netapp_mount()
