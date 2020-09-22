import os
import dawn_treader_helpers
import dawn_treader_subprocess

from usb_install_builder_error import log_and_throw
from usb_install_builder_error import USBInstallBuilderError

# public interface - this function should be called to retrieve the Destination object.

def get_destination(Args, CreationDateTime):
  return DawnTreaderDestination(Args.Destination, Args.ProductName, CreationDateTime)

# DawnTreaderDestination object used for storing information about where dawn_treader's
# output should be put

# this supports both LOCAL and REMOTE and will mount the REMOTE if needed
#
# in practice, running on an IS&T server, this will always be local (the mount will be
# handled by IS&T). that means that while the REMOTE access worked when this was written
# it is at high risk of atrophying

class DawnTreaderDestination(object):
  def __init__(self, BaseOutputDir, ProductName, CreationDateTime):
    self.BaseDestination = BaseOutputDir
    self.ProductName = ProductName
    self.ProductDestination = os.path.join(self.BaseDestination, self.ProductName)
    self.CreationDateTime = CreationDateTime
    self.OutputName = self.obtain_output_subdirectory_name()
    self.FullDestination = os.path.join(self.ProductDestination, self.OutputName)
    self.USBDestination = os.path.join(self.FullDestination, "USB")
    self.DestinationIsExternalMount = False
    self.MountPoint = None
    self.MountSource = None

  def update_destinations(self, src, dst):
   self.BaseDestination = self.BaseDestination.replace(src, dst)
   self.ProductDestination = self.ProductDestination.replace(src, dst)
   self.FullDestination = self.FullDestination.replace(src, dst)
   self.USBDestination = self.USBDestination.replace(src, dst)

  def obtain_output_subdirectory_name(self):
    # return "tmp"
    return self.CreationDateTime.strftime("%y.%m.%d__%H.%M.%S")

  def mount_and_validate_base_destination(self):
    try:
      if self.BaseDestination.startswith("//"):
         self.DestinationIsExternalMount = True
         self.MountSource = self.BaseDestination
         self.MountPoint = self.generate_destination_mount_point_name()
         dawn_treader_subprocess.mount_network_fileshare(self.MountPoint, self.MountSource)
         self.update_destinations(self.MountSource, self.MountPoint)
      dawn_treader_helpers.validate_directory(self.BaseDestination)
    except:
      log_and_throw("unable to mount and validate destination {0}\n".format(self.BaseDestination))

  def validate_and_make_destinations(self):
    self.mount_and_validate_base_destination()
    for Subdirectory in [self.ProductDestination, self.FullDestination, self.USBDestination]:
       dawn_treader_helpers.make_new_directory(Subdirectory)

  def unmount_destination_dir(self):
    if self.DestinationIsExternalMount:
      dawn_treader_subprocess.unmount_network_fileshare(self.MountPoint)
      self.update_destinations(self.MountPoint, self.MountSource)
      self.MountSource = None
      self.MountPoint = None
      self.DestinationIsExternalMount = False

  def generate_destination_mount_point_name(self):
     return "/mnt/dt_DST_{0}".format(self.CreationDateTime.strftime("%m%d_%H%M%S%f"))
