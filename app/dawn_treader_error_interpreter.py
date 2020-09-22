import os
import sys
import errno
import subprocess
import traceback

from usb_install_builder_error import log_and_throw
from usb_install_builder_error import log_without_throw

# this class is intended to provide some user friendly error feedback for errors raised by 
# various external processes dawn_treader interacts with
#
# this is done because in many respects, the built in output is not helpful unless
# someone checks errno.

class ErrorInterpreter(object):
  def __init__(self, errno, cmd, log = None, output = None):
    self.errno = errno
    self.cmd = cmd
    self.log = log
    self.output = output

  def has_output(self):
    return self.output != None

  def append_output(self, base):
    retval = base
    if self.has_output():
       retval = base + "Associated output: {0}\n".format(self.output)
    return retval

  def check(self):
    if self.errno != 0:
      log_without_throw("dawn_treader_error_interpreter checking cmd {0}, errno {1}\n".format(self.cmd, self.errno), self.log)
      if self.cmd == "rsync":
         self.rsync_failure()
      elif self.cmd == "mkdir":
         self.mkdir_failure()
      elif self.cmd == "mount.cifs":
         self.mount_cifs_failure()
      elif self.cmd == "umount":
         self.umount_failure()
      elif self.cmd == "rm":
         self.rm_failure()
      elif self.cmd == "mount":
         self.mount_failure()
      elif self.cmd == "mv":
         self.mv_failure()
      else:
         self.unknown_failure()

  def unknown_failure(self):
    log_without_throw("huh? {}".format(self.output), self.log)
    log_without_throw("{}".format(traceback.print_stack()), self.log)
    log_and_throw("WTFLOLBBQ", self.log)

  def rsync_failure(self):
    err = "rsync isn't happy, and it says its reason is {0}\n".format(self.errno)
    log_and_throw(self.append_output(err), self.log)

  def mkdir_failure(self):
    err = "mkdir isn't happy, and it says its reason is {0}\n".format(self.errno)
    log_and_throw(self.append_output(err), self.log)

  def mount_cifs_failure(self):
    # https://msdn.microsoft.com/en-us/library/ee441884.aspx
    if self.errno == 3:
      err = "A component in the path prefix is not a directory, so mount.cifs cannot mount it\n"
    elif self.errno == 5:
      err = "CIFS is denying access for some reason\n"
    elif self.errno == 8:
      err = "mount.cifs is unable to obtain more memory from the server\n"
    elif self.errno == 0xF:
      err = "mount.cifs was confused by an invalid drive\n"
    elif self.errno == 0x20:
      err = "mount.cifs cannot open with a mode that conflicts with an existing file handle's sharing mode\n"
    elif self.errno == 0x21:
      err = "mount.cifs is encountering a problem with an existing file lock\n"
    elif self.errno == 0x50:
      err = "mount.cifs cannot create a file or directory because it is unable to reuse an existing name\n"
    else:
      err = "mount.cifs isn't happy, and it says its reason is {0}\n".format(self.errno)
    log_and_throw(self.append_output(err), self.log)

  def umount_failure(self):
    if self.errno == errno.EPERM:
      err = "You aren't allowed to run umount\n"
    if self.errno == errno.EINVAL:
      err = "You have asked umount to unmount something that isn't a mount point.\n"
    elif self.errno == errno.ENOENT:
      err = "You have asked umount to unmount something that it can't find.\n"
    else:
      err = "Umount isn't happy, and it says its reason is {0}\n".format(self.errno)

    # failure to mount is recoverable, please don't throw
    log_without_throw(self.append_output(err), self.log)

  def rm_failure(self):
    err = "ERROR: Unspecified error {0} using --rm--\n".format(self.errno)
    # failure to rm is recoverable, please don't throw
    log_without_throw(self.append_output(err), self.log)

  def mv_failure(self):
    err = "ERROR: unexpected problem renaming directory with mv. Skipping rename.\n"
    log_without_throw(self.append_output(err), self.log)

  def mount_failure(self):
    if self.errno == errno.EPERM:
      err = "You aren't allowed to run mount.\n"
    elif self.errno == errno.ENOENT:
      err = "You asked mount to use a directory or file it can't find.\n"
    elif self.errno == 32:
      err = "You asked mount to use a directory or file it can't find.\n"
    elif self.errno == errno.EACCES:
      err = "You asked mount to use a directory or file it can't access.\n"
    elif self.errno == errno.EBUSY:
      err = "You asked mount to use a directory or file that's already busy.\n"
    elif self.errno == errno.ENOTDIR:
      err = "Something you told mount was a directory wasn't\n"
    else:
      err = "Mount isn't happy, and it says its reason is {0}\n".format(self.errno)

    log_and_throw(self.append_output(err), self.log)

