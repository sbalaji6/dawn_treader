import os
import sys
import datetime
import errno
import fileinput
import dawn_treader_credentials
from xml.etree.ElementTree import ElementTree
import xml
import shutil

from usb_install_builder_error import USBInstallBuilderError

def strip_filename(fullpath):
   delim = fullpath.rfind("/")
   return fullpath[delim+1:]

def validate_directory(DirPath):
  if os.path.isdir(DirPath):
    return True
  else:
    raise USBInstallBuilderError("{0} is an invalid directory\n".format(DirPath))

def validate_file_exists(FilePath):
  if os.path.exists(FilePath):
     return True
  else:
     raise USBInstallBuilderError("{0} is missing\n".format(FilePath))

def validate_iso_file(FileName):
   if not FileName.ISOName == None:
     if validate_file_exists(FileName.ISOName):
       return "validated {0}\n".format(FileName.ISOName)
     else:
       return "Error validating {0}\n".format(FileName.ISOName)
   else:
     return "Error validating!\n"

def make_new_directory(DirPath):
  try:
    os.makedirs(DirPath)
  except OSError, e:
    if e.errno != errno.EEXIST:
      raise USBInstallBuilderError("FATAL ERROR creating {0}\n".format(DirPath))

def append_if_needed(Path, Appendage):
   if Path[-1] != Appendage:
     return Path + Appendage
   else:
     return Path

def prepend_if_needed(Path, Appendage):
   if Path[1] != Appendage:
      return Appendage + Path
   else:
      return Path

# it's very odd this isn't handled in dawn_treader_destination
def get_local_iso_storage():
  local_credentials = dawn_treader_credentials.get_credentials_for_local()
  if local_credentials.iso_storage is None:
    retval = "/tmp/dt_local_storage"
  else:
    retval = local_credentials.iso_storage

  try:
    validate_directory(retval)
  except USBInstallBuilderError as e:
    os.makedirs(retval)
  return retval

def generate_iso_source_location_mount_point_name(Mountable):
   if Mountable == None:
      return Mountable
   ModifiedMountable = Mountable.replace("/", "_")
   return "/mnt/dt_SRC_{0}_{1}".format(datetime.datetime.now().strftime("%m%d%H%M%S%f"), ModifiedMountable)

def generate_dvd_image_mount_point_name(Mountable):
   return  "/mnt/dt_DVD_{0}_{1}".format(datetime.datetime.now().strftime("%m%d%H%M%S%f"), Mountable)


# this is bizarre and needs explanation.
# the windows installer uses xml files to tell itself where to find resources
# the assumption in the DDEFAULT xml files is that everything is in the root subdir
# but this process puts some things in subdirectories
# in which case the xml file needs to be updated to map to \Subdir rather than \

def replace_information_in_xml_file(Subdir, XMLFileName):
   if Subdir == None:
      return "unable to replace information in a file located in a nonexistent directory\n"
   elif XMLFileName == None:
      return "unable to replace information in a nonexistent file!\n"
   else:
      FirstSearch = "<SourcePath>\\</SourcePath>"
      FirstReplace = "<SourcePath>\\" + Subdir + "</SourcePath>"
      SecondSearch = "MediaMountPoint=\"\\\""
      SecondReplace = "MediaMountPoint=\"\\" + Subdir + "\""
      validate_file_exists(XMLFileName)
      for line in fileinput.input(XMLFileName, inplace=True):
         line = line.replace(FirstSearch, FirstReplace)
         line = line.replace(SecondSearch, SecondReplace)
         sys.stdout.write(line)
      return "stuff replaced in xml file {0}\n".format(XMLFileName)

def replace_information_in_xml_file_flame9(Subdir, XMLFileName):
   try:
    if Subdir == None:
        return "unable to replace information in a file located in a nonexistent directory\n"
    elif XMLFileName == None:
        return "unable to replace information in a nonexistent file!\n"
    else:
        tree = ElementTree()
        tree.parse(XMLFileName)
        xml.etree.ElementTree.register_namespace("", "http://PlatformGroup.efi.com/Fiery/SubsystemSetup")
        p = tree.find(".//{http://PlatformGroup.efi.com/Fiery/SubsystemSetup}RecoveryFiles")
        newp = [p.remove(item) for item in p[1:]]
        srcNode = tree.find(".//{http://PlatformGroup.efi.com/Fiery/SubsystemSetup}RecoverySetupFileCopy")
        srcNode[0].text = '\\' +  Subdir

        p = tree.findall(".//*[@MediaMountPoint]")
        for item in p:
            temp = item.attrib['MediaMountPoint']
            item.attrib['MediaMountPoint'] = "\\" + Subdir  + temp
        xml.etree.ElementTree.dump(tree)
        tree.write(XMLFileName+ ".new",xml_declaration=True, method='xml', encoding='UTF-8')
        shutil.move(XMLFileName, XMLFileName + ".orig")
        shutil.move(XMLFileName + ".new",XMLFileName)
        os.remove(XMLFileName + ".orig")
   except Exception as e:   
     return "failed to  replace in xml file {0}\n".format(XMLFileName)
   return "new stuff replaced in xml file {0}\n".format(XMLFileName)  


def copydir(source, dest):
    """Copy a directory structure overwriting existing files"""
    for root, dirs, files in os.walk(source):
        if not os.path.isdir(root):
            os.makedirs(root)

        for file in files:
            rel_path = root.replace(source, '').lstrip(os.sep)
            dest_path = os.path.join(dest, rel_path)

            if not os.path.isdir(dest_path):
                os.makedirs(dest_path)

            shutil.copyfile(os.path.join(root, file), os.path.join(dest_path, file))
            



