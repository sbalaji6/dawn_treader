import os
import sys
import subprocess
import datetime
import errno
import fileinput
import mchammer.ex

from dawn_treader_credentials import get_credentials_for_server
from dawn_treader_credentials import get_credentials_for_local

from dawn_treader_helpers import append_if_needed
from dawn_treader_helpers import strip_filename
from dawn_treader_helpers import get_local_iso_storage

from dawn_treader_error_interpreter import ErrorInterpreter

from usb_install_builder_error import log_without_throw
from usb_install_builder_error import log_and_throw
from usb_install_builder_error import USBInstallBuilderError

def call_subprocess(cmd, log=None, _timeout=None, capture_output=True):
  if _timeout is None:
     timeout = 300
  else:
    timeout = _timeout
  log_without_throw("mchammer.ex: timeout {0}, cmd {1}\n".format(timeout, cmd), log)
  r, out = mchammer.ex.ex(timeout, cmd, buffer_output_in_memory=capture_output)
  if r != 0:
    log_without_throw("Error Detected {0}\n".format(r), log)
  return r, out

def copy_tree(src_dir, dest_dir, override_perms, log=None):
   log_without_throw("copy_tree {0} {1}\n".format(src_dir, dest_dir), log)
   # DANGEROUS BUG - in *theory*, iterative_rsync with override_perms set to TRUE ought to do what we want.
   # but in practice, when copying an ISO on ubuntu 14.04, the process runs out of open file handles.
   # so ... don't use this that way.
   iterative_rsync(src_dir, dest_dir, override_perms, log)

#------------rsync functions

# you would expect that you could just rsync a directory.
# the problem with that is that the directories are so large,
# and some of the files so big, that doing so fails - the
# rsync call gets timed out.

# that wouldn't be so bad, but something also goes horribly wrong
# with the recovery such that the .swm files are corrupted
# if the failure happens during the transfer of those files,
# which it is likely to, because they are big
# 
# so instead, iteratively rsync the files individually

def dir_chmod(dest_dir, log=None):
   chmod_cmdline = "chmod a+w -R {}/*".format(dest_dir)
   log_without_throw("calling {}".format(chmod_cmdline), log)
   r, out = call_subprocess(chmod_cmdline, log, _timeout = 300)
   log_without_throw("got back r: {}, out {}".format(r, out), log)
   ErrorInterpreter(r, "chmod", log, out).check()
   return r, out
   

def rsync_file_with_retries(src_file, dest_dir, override_perms, log=None):
   rsync_cmdline = "rsync -av -W \"{0}\" \"{1}\"".format(src_file, dest_dir)
   chperm_cmdline = "chmod 666 \"{}\"".format(os.path.join(dest_dir, strip_filename(src_file)))
   rsync_timeout = 240
   rsync_hangup_error = 20
   max_retries = 10
   retries = 0

   r, out = call_subprocess(rsync_cmdline, log, capture_output=False, _timeout=rsync_timeout)
  
   while (r == rsync_hangup_error and retries < max_retries):
     log_without_throw("rsync hangup error detected on {0}, retrying\n".format(src_file), log, WriteToStdout = True)
     
     r, out = call_subprocess(rsync_cmdline, log, capture_output=True, _timeout=rsync_timeout)
     log_without_throw("output: {0}\n".format(out), log)

     retries = retries + 1

   if (r == rsync_hangup_error):
      log_without_throw("BE WORRIED: rsync error {0} encountered after {1}  retries\n".format(rsync_hangup_error, max_retries), log, WriteToStdout=True)

   ErrorInterpreter(r, "rsync", log, out).check()

   if override_perms is True or file_requires_permission_override(strip_filename(src_file)):
     log_without_throw("overriding permissions on {}\n".format(src_file), log)
     r, out = call_subprocess(chperm_cmdline, log, capture_output=True)
     ErrorInterpreter(r, "chmod", log, out).check()
   return r, out

def iterative_rsync(src_dir, dest_dir, override_perms, log=None):
 try:
   src_list = os.listdir(src_dir)
   log_without_throw("--iterative_rsync: ({0}) : {1}---\n".format(src_dir, src_list), log)
   print("balaji --iterative_rsync: ({0}) : {1}---\n".format(src_dir, src_list), log)
   for _src in src_list:
      full_src_name = os.path.join(src_dir, _src)
      if os.path.isdir(full_src_name):
         full_dst_name = os.path.join(dest_dir, _src)
         try:
           log_without_throw(" making directory {0}\n".format(full_dst_name), log)
           print("balaji making directory {0}\n".format(full_dst_name), log)
           os.makedirs(full_dst_name)
         except OSError as e:
           log_without_throw("suppressing OS Error {0} from os.makedirs\n".format(e.errno), log)
         iterative_rsync(full_src_name, full_dst_name, override_perms, log)
      else:
         r, out = rsync_file_with_retries(os.path.join(src_dir, _src), dest_dir, override_perms, log)
 except Exception as e:
   print("balaji...........")
   log_and_throw("iterative rsync encountered {}".format(e))
  
         

# mount and unmount network fileshares.
# 
# currently we use mount.cifs to mount smb mounts
#
# and then a loopback mount to mount a DVD image

def mount_network_fileshare(mount_point, mountable, log=None):
   if mount_point is None or mountable is None:
     #"calling code wishes to do this and have it absorbed so that calling code can iterate through objects silently do nothing for nonexistent ones"
     return None

   elif not os.path.isdir(mount_point):
     r, out = call_subprocess("sudo mkdir {0}".format(mount_point), log)
     ErrorInterpreter(r, "mkdir", log, out).check()

     Creds = get_credentials_for_server(mountable)
     LocalCreds = get_credentials_for_local()

     BaseCmdLine = "sudo mount.cifs {0} {1}".format(mountable, mount_point)
     
     if Creds.Domain is None:
       UNamePasswd = "-o user={0},pass={1}".format(Creds.Username, Creds.Password)
     else:
       UNamePasswd = "-o user={0},doman={1},pass={2}".format(Creds.Username, Creds.Domain, Creds.Password)

     if LocalCreds.uid is None:
       CIFSMountCmdline = "{0} {1}".format(BaseCmdLine, UNamePasswd)
     else:
       CIFSMountCmdline = "{0} {1},uid={2},gid={3}".format(BaseCmdLine, UNamePasswd, LocalCreds.uid, LocalCreds.gid)

     r, out = call_subprocess(CIFSMountCmdline, log)
     ErrorInterpreter(r, "mount.cifs", log, out).check()

     return mount_point

   else:
     log_without_throw("skipping mounting of duplicate directory {0}\n".format(mountable), log, WriteToStdout=False)
     return None

def unmount_network_fileshare(mount_point, log = None):

   forbidden = get_local_iso_storage()
   if mount_point == forbidden:
     log_without_throw("skipping unmounting of forbidden directory {}".format(forbidden))
   elif os.path.isdir(mount_point):
     try:
      r, out = call_subprocess("sudo umount {0}".format(mount_point), log)
      ErrorInterpreter(r, "umount", log, out).check()
    
      # only try to rm if you successfully unmounted, to avoid accidentally doing very bad things
      # however, rename it, to prevent future runs from being confused by lingering data
      if r == 0:
        r, out = call_subprocess("sudo rm -rf {0}".format(mount_point), log)
        ErrorInterpreter(r, "rm", log, out).check()
      else:
        log_without_throw("declining to delete {0} because it wasn't successfully unmounted\n".format(mount_point), log)
        unmountable_rename = "{0}__unmountable".format(mount_point)

        r, out = call_subprocess("sudo mv {0} {1}".format(mount_point, unmountable_rename), log)
        log_without_throw("moving {0} to {1} because it's unmountable for some reason".format(mount_point, unmountable_rename), log, WriteToStdout=True)

        ErrorInterpreter(r, "mv", log, out).check()
     except:
      pass
   else:
     log_without_throw("skipping unmounting of already unmounted directory {0}\n".format(mount_point), log, WriteToStdout=False)

def mount_dvd_image(mount_point, dvd_image, log = None, mount_udf = False):
   log_without_throw("mount_dvd_image: mount_point {} dvd_image {}\n".format(mount_point, dvd_image), log)
   if mount_point is None or dvd_image is None:
     return None
     #"calling code wishes to do this and have it absorbed so that calling code can iterate through objects silently do nothing for nonexistent ones"

   r, out = call_subprocess("sudo mkdir {0}".format(mount_point), log)
   ErrorInterpreter(r, "mkdir", log, out).check()

# the initial implementation of dawntreader just did a loopback ount without specifying
# type.
#
# but it turns out that there's a problem where unless you sxplicitly suppress the rock ridge extensions,
# mount handles the Joliet filenames incorrectly.
# so I changed the code to work around it, on advice from trux.

#   r, out = call_subprocess("sudo mount -o loop {0} {1}".format(dvd_image, mount_point), log)
   if mount_udf:
     r, out = call_subprocess("sudo mount -o loop {0} {1}".format(dvd_image, mount_point), log)
   else:
     r, out = call_subprocess("sudo mount -t iso9660 -o loop -o norock {0} {1}".format(dvd_image, mount_point), log)
   ErrorInterpreter(r, "mount", log, out).check()

def unmount_dvd_image(mount_point, log=None): 
   forbidden = get_local_iso_storage()
   if not mount_point == forbidden:
     r, out = call_subprocess("sudo umount {0}".format(mount_point), log)
     ErrorInterpreter(r, "umount", log, out).check()

     # only try to rm if you successfully unmounted, to avoid accidentally doing very bad things
     if r == 0:
       r, out = call_subprocess("sudo rm -rf {0}".format(mount_point), log)
       ErrorInterpreter(r, "rm", log, out).check()

#### irritating whitelist

# it turns out that Paul thinks certain files cannot use the permissions as
# established by rsync. Why, it's not clear.

# to minimize the effect of global permission blasts, those are put here.
def file_requires_permission_override(filename):
  OVERRIDE_REQUIRED = ["boot.wim"]

  if filename in OVERRIDE_REQUIRED:
    return True
  else:
    return False

