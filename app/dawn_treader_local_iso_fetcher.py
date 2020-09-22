import os
import ftplib

import dawn_treader_helpers
import dawn_treader_credentials

from dawn_treader_subprocess import call_subprocess
from dawn_treader_error_interpreter import ErrorInterpreter
from dawn_treader_server_id import server_is_rms_type
from dawn_treader_local_copy_controller import get_rms_credential_file
from usb_install_builder_error import log_and_throw
from usb_install_builder_error import log_without_throw

# path on RMS where the isos can be found
RMS_PATH = "/Volumes/share"

# class used to retrieve ISO images via ftp rather than cifs mounting them
class DawnTreaderLocalFtper(object):
   def __init__(self, storage, iso_path, iso_name, Log = None):
     self.storage = storage
     self.iso_path = iso_path
     self.log = Log
     self.iso_name = iso_name
     self.local_copy = ""

   def validate_storage_exists(self):
     if os.path.isdir(self.storage):
       return True
     elif os.path.exists(self.storage):
       log_and_throw("{} is a file! ABORT! ABORT!\n".format(self.storage), self.log)
     else:
       dawn_treader_helpers.make_new_directory(self.storage)
       return True

   def get_stripped_name(self):
       opening = self.iso_path.find("//")
       return self.iso_path[opening+2:]

   def get_server_name(self):
       name = self.get_stripped_name()
       inflection = name.find("/")
       return name[:inflection+1]

   def deconstruct_server_name(self):
     full_server_name = self.get_stripped_name()
     inflection = full_server_name.find("/")
     if inflection > -1:
        return full_server_name[:inflection], full_server_name[inflection+1:]
     else:
        return full_server_name, None

   def source_is_remote(self):
     if self.iso_path.startswith("//"):
        return True
     else:
        log_and_throw("{} is not a remote path! ABORT! ABORT!\n".format(self.iso_path), self.log)
        return False

   # this is only supported for rms servers. if for some reason we've been invoked for another server, bail!
   def source_can_be_handled(self):
     if server_is_rms_type(self.get_server_name()):
       return True
     else:
       log_without_throw("dawn_treader is unaware of the process used to handle fetching {}\n".format(self.iso_path), self.log, WriteToStdout=True)
       return False

   def retrieve_source(self):
     server_name, server_subpath = self.deconstruct_server_name()
     src_file = os.path.join(server_subpath, self.iso_name)
     dst_file = os.path.join(self.storage, self.iso_name)
     log_without_throw("retrieve_source: {} -> {}".format(src_file, dst_file), self.log, WriteToStdout=True)

     rms_ftp_credential_file = get_rms_credential_file()
     rms_ftp_creds = dawn_treader_credentials.get_credentials_from_file(rms_ftp_credential_file)
     if rms_ftp_creds.Username is None:
       rms_ftp_creds = dawn_treader_credentials.DefaultCredentials

     _datawriter.open_file(dst_file)
     _datawriter.add_log(self.log)

     ftp = ftplib.FTP("{}".format(server_name))
     try:
       ftp.login("{}".format(rms_ftp_creds.Username), "{}".format(rms_ftp_creds.Password))
       log_without_throw(" logged in: {}".format(server_name), self.log, WriteToStdout=True)
       ftp.cwd(RMS_PATH)
       log_without_throw(" retrieving", self.log, WriteToStdout=True)
       ftp.retrbinary("RETR {}".format(src_file), handle_ftp_download)
       log_without_throw(" done".format(dst_file), self.log, WriteToStdout=True)
       _datawriter.close_file()
       return dst_file
     except ftplib.error_perm as e:
       log_without_throw("FTP error: {}".format(e.args), self.log, WriteToStdout=True)
       _datawriter.close_file()
       os.remove(dst_file)
       return None
     finally:
       # BOO! BOO! BOO!
       #
       # a well behaved client calles ftp.quit(). but it turns out
       # fcmrms03 hangs if you do that.
       #
       # this is one of those cases where we can't play nice if they can't play nice.
       ftp.close()

   def obtain_local_copy(self):
     if self.validate_storage_exists() and self.source_is_remote() and self.source_can_be_handled():
        r = self.retrieve_source()
        if r == None:
          log_without_throw("unable to obtain local copy of ISO: {}".format(os.path.join(self.iso_path, self.iso_name)), self.log, WriteToStdout=True)
        return r
     else:
        log_and_throw("Unable to obtain local copy of ISO: {}".format(os.path.join(self.iso_path, self.iso_name)), self.log, WriteToStdout=True)
        return None


########### retrbinary requires a callback.

# the callback is handle_ftp_download
# but it needs to know what file to write to
# iecause it tickles my sense of containerization, i've put this inside a class
#
# this class is EFFECTIVELY a singleton in each instance of the script, but
# that doesn't effect multiple instances of the script, since each should be
# writing to a different file name.
#
# HOWEVER there's a real, irritating, edge case where two different instances of the script
# trying to write to the SAME FILE.
#
# right now, that will cause something to die horribly in a fire.
#
#
# one fix is to have each instance of the script write to different _tmp directories
# but yuck
#
# another fix is to have the script detect if the file already exists on disk and
# then do SOMETHING - wait for it to be complete and then use it?
#
# but what if the original owner deletes it?
#
# reference count in a DB?
#
#
# the RIGHT fix is to have the script detect if the file exists and not use it,
# and then have the script not delete these - have a cron job delete periodically
# but only after checking to see that the script isn't running.
#
# that's for next week

class FTPBinaryDataWriter(object):
   def __init__(self, Filename, Log=None):
      self.log = Log
      self.filename = Filename
      self._file = None
      self.open_file(Filename)


   def open_file(self, name):
      if name != None and self.filename == None and self._file == None:
         self.filename = name
         self._file = open(self.filename, 'wb+')

   def add_log(self, log):
      self.log = log

   def write_block(self, block):
      if self._file != None:
        self._file.write(block)
      else:
        log_without_throw("? FtpBinaryDataWriter has no file?\n", self.log, WriteToStdout=True)

   def close_file(self):
      if self._file != None:
         self._file.close()
         log_without_throw("closing {}".format(self.filename), self.log)
         self._file = None
         self.filename = None

def handle_ftp_download(block):
   _datawriter.write_block(block)

_datawriter = FTPBinaryDataWriter(None)


########### functions used to pull remote dvds local

def ftp_local_copy_of_iso(storage, iso_loc, iso_name, Log=None):
  local_copier = DawnTreaderLocalFtper(storage, iso_loc, iso_name, Log)
  return local_copier.obtain_local_copy()
  # not yet implemented - somehow this entire branch got merged unexpectedly
  # it seems to be working, mostly because the code path isn't executed by default
  # and nothing in the default execution path changed. and yet.

  # is it a remote system?
  # is it a remote system i know how to access?
  # if so, access it

def rms_iso_is_cached(storage, remote_path, name, Log=None):
  # remote path isn't currently used but may be necessary later if anyone wants to deconstruct
  # whether this is actually RMS or not
  log_without_throw("in rms_iso_is_cached")
  if os.path.exists(os.path.join(storage, name)):
    log_without_throw("{} appears to be cached in {}, using that".format(name, storage), Log, WriteToStdout=True)
    return True
  else:
    return False

def should_cache_iso(iso_name):
  # this is somewhat hackish and very ineact
  # the basic idea is that if it's an adobe, fcps, or os iso, we should save it
  # but if it's a product iso, we shouldn't.
  # that's because os/adobe/fcps isos will be heavily reused
  # but product isos should not be - how many times do you need to build the same product ISO?
  if iso_name is not None:
     for infix in ["os_win8", "adobe", "fcps", "profiler", "acrobat"]:
        infix_start = iso_name.find(infix)
        if infix_start > -1:
           return True
  return False

def remove_local_copy_of_iso(iso_loc, iso_name, Log=None):
  if not should_cache_iso(iso_name):
     r, out = call_subprocess("rm -rf {0}".format(os.path.join(iso_loc,iso_name)), Log)
     ErrorInterpreter(r, "rm", Log, out).check()
