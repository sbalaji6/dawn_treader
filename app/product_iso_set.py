import os
import shutil
import fnmatch
import dawn_treader_helpers
import dawn_treader_local_copy_controller

from dawn_treader_helpers import generate_iso_source_location_mount_point_name
from dawn_treader_helpers import generate_dvd_image_mount_point_name
from dawn_treader_helpers import prepend_if_needed
from dawn_treader_helpers import replace_information_in_xml_file
from dawn_treader_helpers import replace_information_in_xml_file_flame9
from dawn_treader_helpers import get_local_iso_storage

from dawn_treader_subprocess import mount_network_fileshare
from dawn_treader_subprocess import mount_dvd_image
from dawn_treader_subprocess import unmount_dvd_image
from dawn_treader_subprocess import unmount_network_fileshare
from dawn_treader_subprocess import copy_tree
from dawn_treader_subprocess import dir_chmod
from dawn_treader_local_iso_fetcher import ftp_local_copy_of_iso
from dawn_treader_local_iso_fetcher import rms_iso_is_cached
from dawn_treader_local_iso_fetcher import remove_local_copy_of_iso
from dawn_treader_local_copy_controller import using_local_rms_ftp_capacity
from dawn_treader_local_copy_controller import using_local_rms_netapp_mount
from dawn_treader_server_id import server_is_rms_type

from usb_install_builder_error import log_and_throw
from usb_install_builder_error import log_without_throw

# this contains a class that represents all of the product isos
# eg, server, os, user, adobe, etc.

# some constants used for string comparison later
_LOCAL = "Local"
_NETAPP_MOUNT = "Netapp"
_FTP_MOUNT = "FTP"
_CIFS_MOUNT = "CIFS"


# external code calls this to get product isos. the structure is expected
# to be the same as the dawn_treader_arguments args structure.

def get_product_isos(Args):
  return ProductISOSet(Args.InstallerISO,Args.FieryISO, Args.OsISO1, Args.OsISO2,Args.usersw, Args.Adobe, Args.FCPS)

class ProductISOInstance(object):
  def __init__(self, iso_path):
    # isos have a mount point, which represents where you can find them,
    # and a dvd mount point, which represents where the ISO's contents can be accessed,
    # and a mounting_type, which represents how the ISO file is mounted - that is
    # it represents what technology is used to get access to the raw ISO file,
    # NOT the technology which is used to get access to the ISO's contents.
    self.iso_mount_pt = None
    self.dvd_mount_pt  = None
    self.iso_loc = None
    self.iso_name = None
    self.mounting_type = None
    self.use_udf = False

    if iso_path == None:
       self.iso_loc = None
       self.iso_name = None
    elif self.is_remote_location(iso_path):
       self.setup_remote_location(iso_path)
    else:
       self.setup_local_location(iso_path)

  def is_remote_location(self, iso_path):
    if iso_path.startswith("//"):
       return True
    else:
       return False

  def setup_remote_location(self, iso_path):
     inflection = iso_path.rfind("/")
     self.iso_loc = iso_path[:inflection]
     self.iso_name = iso_path[inflection+1:]

  def setup_local_location(self, iso_path):
     self.iso_loc = _LOCAL
     self.iso_name = iso_path

  def fixup_name_for_cifs(self):
     ## HACKITY HACK HACK HACK
     #
     # currently rms is storing iso names as [ISO] and then creating symlinks named server.[ISO] and client.[ISO]
     # that's fine and dandy EXCEPT
     # mount -o loop doesn't work on a symlink.
     #
     # narnia will feed us the names of the symlinks, because this is what end users want to use.
     # and in FTP-land we want to use the symlinks because we can ftp them AND that prevents name clashes.
     # but in cifs-land, since we can't mount them, we need to strip them.
     #
     # eventually rms will use hardlinks instead. yay!
     if self.iso_name is not None:
       for prefix in ["client.", "server."]:
         prefix_start = self.iso_name.find(prefix)
         if prefix_start == 0:
           prefix_end = prefix_start + len(prefix)
           tmp = self.iso_name[prefix_end:]
           self.iso_name = tmp

#-----------------------------------------------------------------------

class ProductISOSet(object):
  def __init__(self, Installer, Fiery, OS1, OS2, UserSoftware, Adobe, FCPS):
    self.Log = None
    # representations of ISOs
    self.Installer = ProductISOInstance(Installer)
    self.Fiery = ProductISOInstance(Fiery)
    self.Fiery.use_udf = True
    self.OS1 = ProductISOInstance(OS1)
    self.OS2 = ProductISOInstance(OS2)
    self.UserSoftware = ProductISOInstance(UserSoftware)
    self.Adobe = ProductISOInstance(Adobe)
    self.FCPS = ProductISOInstance(FCPS)

  def set_log(self, Log):
    self.Log = Log
    log_without_throw("Log attaching to ProductISOSet. Fiery = {0}/{1}, OS1 = {2}/{3}, OS2 = {3}/{4}, usersw = {4}/{5}".format(self.Fiery.iso_loc, self.Fiery.iso_name, self.OS1.iso_loc, self.OS1.iso_name, self.OS2.iso_loc, self.OS2.iso_name, self.UserSoftware.iso_loc, self.UserSoftware.iso_name), self.Log, WriteToStdout=False)

  def isos(self):
    return [self.Installer,self.Fiery, self.OS1, self.OS2, self.UserSoftware, self.Adobe, self.FCPS]

  # a helper function
  def simple_iso_image_copy(self, Srcdir, destdir, Log=None):
      copy_tree(Srcdir, destdir, False, Log)
      return "succeeded at copying {0} to {1}".format(Srcdir, destdir)

  def iso_image_copy_with_permission_override(self, Srcdir, destdir, Log=None):
      copy_tree(Srcdir, destdir, True, Log)
      return "succeeded at copying {0} to {1}".format(Srcdir, destdir)

  def simple_file_copy(self, Filename, DestFilename, Log=None):
      shutil.copyfile(Filename, DestFilename)
      return "succeeded at copying {0} to {1}".format(Filename, DestFilename)

  def should_try_netapp_mount(self, already_mounted, location):
      if already_mounted == None and location != None and server_is_rms_type(location) and using_local_rms_netapp_mount():
         return True
      else:
         return False

  def using_rms_ftp_subsystem(self, already_mounted, location):
      if already_mounted == None and location != None and server_is_rms_type(location) and using_local_rms_ftp_capacity():
         return True
      else:
         return False

  def rms_iso_is_cached(self, storage, remote_path, name):
     return rms_iso_is_cached(storage, remote_path, name)

  #-----------------------
  def mount_isos(self):
    for mounting_loc in self.isos():
      log_without_throw("mounting {}".format(mounting_loc.iso_name), self.Log)
      mounted = None
      if mounting_loc.iso_loc != _LOCAL:
        log_without_throw("iso loc is not local", self.Log)
        if self.should_try_netapp_mount(mounted, mounting_loc.iso_loc) is True:
          # ok, in theory this should just set the mounting_loc to the correct value for the netapp mount
          log_without_throw("trying to use local_rms_netapp_mount capacity to load {}".format(mounting_loc.iso_loc), self.Log)
          mounted = None
          if mounted == None:
            mounting_loc.mounting_type = _NETAPP_MOUNT

        if self.using_rms_ftp_subsystem(mounted, mounting_loc.iso_loc) is True:
          log_without_throw("using the rms ftp subsystem", self.Log)
          local_storage = "/tmp"
          try:
            local_storage = get_local_iso_storage()
          except Exception as e:
            log_and_throw("exception {}".format(e), self.Log)
          if self.rms_iso_is_cached(local_storage, mounting_loc.iso_loc, mounting_loc.iso_name) is True:
             log_without_throw("rms iso seems to be cached", self.Log)
             mounting_loc.iso_mount_pt = local_storage
             mounted = True
             mounting_loc.mounting_type = _FTP_MOUNT
          else:
            log_without_throw("trying to use rms ftp capacity to load {}".format(mounting_loc.iso_loc), self.Log)
            mounting_loc.iso_mount_pt = local_storage
            mounted = ftp_local_copy_of_iso(mounting_loc.iso_mount_pt, mounting_loc.iso_loc, mounting_loc.iso_name, self.Log)
            if mounted is not None:
              mounting_loc.mounting_type = _FTP_MOUNT

        if mounted == None:
          log_without_throw("trying to use cifs mount capacity to load {}".format(mounting_loc.iso_loc), self.Log, WriteToStdout = True)
          mounting_loc.fixup_name_for_cifs()
          mounting_loc.iso_mount_pt = generate_iso_source_location_mount_point_name(mounting_loc.iso_loc)
          mounted = mount_network_fileshare(mounting_loc.iso_mount_pt, mounting_loc.iso_loc, self.Log)
          if mounted != None:
           mounting_loc.mounting_type = _CIFS_MOUNT

    # FIXME: it's really not clear that this works at all if the mounting_loc's iso_loc is _LOCAL.
    # unfortunately, I also can't imagine what the workflow was where that was desired.
    for mounting_img in self.isos():
      if mounting_img.iso_name != None:
         log_without_throw("generating dvd image mount point name", self.Log)
         mounting_img.dvd_mount_pt = generate_dvd_image_mount_point_name(mounting_img.iso_name)
         log_without_throw("trying to mount {} image {}".format(mounting_img.iso_mount_pt, mounting_img.iso_name), self.Log)
         log_without_throw("dvd_mount_pt = {}".format(mounting_img.dvd_mount_pt), self.Log)
         mount_dvd_image(mounting_img.dvd_mount_pt, os.path.join(mounting_img.iso_mount_pt, mounting_img.iso_name), self.Log, mounting_img.use_udf)

  def unmount_isos(self):
    for unmounting_img in self.isos():
      if unmounting_img.dvd_mount_pt != None and unmounting_img.iso_name != None:
         try:
           unmount_dvd_image(unmounting_img.dvd_mount_pt, self.Log)
           unmounting_img.dvd_mount_pt = None
         except:
           log_without_throw("failed to unmount {}, ignoring".format(unmounting_img.dvd_mount_pt), self.Log)
    for unmounting_loc in self.isos():
      if unmounting_loc.mounting_type == _FTP_MOUNT:
         remove_local_copy_of_iso(unmounting_loc.iso_mount_pt, unmounting_loc.iso_name)
         unmounting_loc.iso_mount_pt = None
      elif unmounting_loc.mounting_type == _NETAPP_MOUNT:
         # it's an error to remove the local copy of the ISO, and the "mount_point" in this sense is a local dir rather than a mount
         # so set it to nil :)
         unmounting_loc.iso_mount_pt = None
      if unmounting_loc.iso_mount_pt != None:
         unmount_network_fileshare(unmounting_loc.iso_mount_pt, self.Log)
         unmounting_loc.iso_mount_pt = None

  # this somewhat presumes that it's ok to mount all six and then unmount all six
  # but whaat happens if multiple instances are invoked?
  # it may be that this needs to be reworked so that the calling code can iteratively mount, copy, and unmount, while updating the mount point
  # that's kinda an icky workflow, though


  #-----------------------
  # windows workflow

  def copy_windows_permission_override_behavior(self, destdir):
     r, out = dir_chmod(destdir, self.Log)

  def copy_fiery_iso(self, destdir):
     if self.Installer == None:
       self.simple_iso_image_copy(self.Fiery.dvd_mount_pt, destdir, self.Log)
     else:
       if self.Fiery.iso_name != None:
         subdir = "Fiery"
         self.copy_and_modify_subdir_iso(self.Fiery.dvd_mount_pt, destdir, subdir)  

  def copy_windows_isos(self, destdir):
     self.simple_iso_image_copy(self.OS1.dvd_mount_pt, destdir, self.Log)
     self.simple_iso_image_copy(self.OS2.dvd_mount_pt, destdir, self.Log)

  def copy_and_modify_subdir_iso(self, mount_pt, destdir, subdir):
    actual_destdir = os.path.join(destdir, subdir)
    os.makedirs(actual_destdir)
    self.simple_iso_image_copy(mount_pt, actual_destdir, self.Log)
    self.modify_and_copy_subdir_xml(destdir, subdir)

  def copy_installer_iso(self, destdir):
    self.simple_iso_image_copy(self.Installer.dvd_mount_pt, destdir, self.Log)


  def copy_and_modify_usersw_iso(self, destdir):
    if self.UserSoftware.iso_name != None:
       subdir = "UserSoftware"
       self.copy_and_modify_subdir_iso(self.UserSoftware.dvd_mount_pt, destdir, subdir)

  def copy_and_modify_adobe_iso(self, destdir):
    if self.Adobe.iso_name != None:
       subdir = "Adobe"
       self.copy_and_modify_subdir_iso(self.Adobe.dvd_mount_pt, destdir, subdir)

  def copy_and_modify_fcps_iso(self, destdir):
    if self.FCPS.iso_name != None:
       subdir = "CPS"
       self.copy_and_modify_subdir_iso(self.FCPS.dvd_mount_pt, destdir, subdir)

  def get_subdir_xml(self, destdir):
    for File in os.listdir(destdir):
      if fnmatch.fnmatch(File, '*.xml'):
        return File
    return None

  def modify_and_copy_subdir_xml(self, destdir, subdir):
    try:
      full_path_to_subdir = os.path.join(destdir, subdir)
      xml_name = self.get_subdir_xml(full_path_to_subdir)
      xml = os.path.join(full_path_to_subdir, xml_name)
      retval = ""
      #print("balaji Installer " ,self.Installer)
      if self.Installer == None:
        print("balaji debug Installer is null")
        retval = replace_information_in_xml_file(subdir, xml)
      else:
        print("balaji debug Installer is not null")
        retval = replace_information_in_xml_file_flame9(subdir, xml)  
      log_without_throw(retval, self.Log)

      new_xml = os.path.join(destdir, xml_name)
      self.simple_file_copy(xml, new_xml)
    except Exception as e:
      log_without_throw("EEEK! Unable to replace information in xml_file {} because {}".format(xml_name, e), self.Log)
