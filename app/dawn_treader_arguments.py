import argparse
import json
import fileinput

from usb_install_builder_error import USBInstallBuilderError

### this file is used for parsing arguments to dawn_treader.
###
### the only function which should be called externally is parse_arguments,
### everything else is a helper function

## helper function to determine if there are no arguments. It returns true if, and only if, all expected arguments
## are "None".
def is_arg_set_empty(Args):
  for Arg in [Args.Destination, Args.ProductName, Args.FieryISO, Args.OsISO1, Args.OsISO2, Args.usersw, Args.Adobe, Args.FCPS, Args.WINVER, Args.conf]:
    if Arg != None:
      return False
  return True

## helper function to determine if all required arguments are there.
def check_for_required_arguments(Args):
  for Arg in [Args.Destination, Args.ProductName]:
   if Arg == None:
      raise USBInstallBuilderError("\n\nFatal Error: unable to proceed without knowing where to place output.\n")
  for Arg in [Args.FieryISO, Args.OsISO1, Args.OsISO2]:
    if Arg == None:
      raise USBInstallBuilderError("\n\nFatal Error: In order to build a USB image, you need *at least* a Fiery ISO and two OS ISOs.\n")

def remove_prefix_and_rstrip(Prefixed):
   if "file://" in Prefixed:
     # remove file:/ but keep the last /
     PrefixEnd = Prefixed.index("file://")+6
     retval = Prefixed[PrefixEnd:]
   elif "://" in Prefixed:
     # remove the : and everything before it but keep the //
     PrefixEnd = Prefixed.index("://") + 1
     retval = Prefixed[PrefixEnd:]
   else:
     retval = Prefixed
   return retval.rstrip()

# helper function which looks in a set, sees if an element exists in
# that set, and returns that element OR some provided string, depending
def update_if_exists(ArgumentOverrides, ExistingString, Override):
  if Override in ArgumentOverrides:
    return remove_prefix_and_rstrip(ArgumentOverrides[Override])
  else:
    return ExistingString

# helper function to deal with the fact that this string may not be entirely correct in user input
def fixup_pull_isos(pull_isos):
  if pull_isos == "True" or pull_isos == "true":
     return "True"
  elif pull_isos == "False" or pull_isos == "false":
     return "False"
  else:
     return None

# helper function to read arguments from a conf file. this will OVERRIDE anything in the
# commandline input - but only what's in the config file!
#
# it does this by using update_if_exists to choose either the existing string or the
# string fromt he conf file, depending on whether the string in the conf file exists.
def fixup_args(Args):
  if Args.conf == None:
     return Args
  ArgumentsOverride = json.loads(open(Args.conf).read())

  Args.Destination = update_if_exists(ArgumentsOverride, Args.Destination, "dest")
  Args.ProductName = update_if_exists(ArgumentsOverride, Args.ProductName, "product")
  Args.InstallerISO = update_if_exists(ArgumentsOverride, Args.InstallerISO, "installer_fiery_iso")
  Args.FieryISO = update_if_exists(ArgumentsOverride, Args.FieryISO, "system_sw_iso")
  Args.usersw = update_if_exists(ArgumentsOverride, Args.usersw, "user_sw_iso")
  Args.Adobe = update_if_exists(ArgumentsOverride, Args.Adobe, "adobe_iso")
  Args.FCPS = update_if_exists(ArgumentsOverride, Args.FCPS, "fcps_iso")
  Args.pull_isos = fixup_pull_isos(update_if_exists(ArgumentsOverride, Args.pull_isos, "pull_isos"))

# the conf file provided by narnia has grouped the os isos, which is nice, but
# that part of the string needs to be suppressed
  if "os_isos" in ArgumentsOverride:
      Args.OsISO1 = remove_prefix_and_rstrip(ArgumentsOverride["os_isos"][0])
      try:
        Args.OsISO2 = remove_prefix_and_rstrip(ArgumentsOverride["os_isos"][1])
      except Exception as e:
        if "os1" in Args.OsISO1:
          Args.OsISO2 = Args.OsISO1.replace("os1", "os2")
        elif "os2" in Args.OsISO1:
          Args.OsISO2 = Args.OsISO1.replace("os2", "os1")
      

# WINVER needs to be a number, but narnia is going to provide a string
  if "product_os" in ArgumentsOverride:
    if ArgumentsOverride["product_os"] == "windows":
      Args.WINVER = 7
    else:
      Args.WINVER = -1

  return Args
  

### main function logic,
def parse_arguments():
  ArgParser = argparse.ArgumentParser(description="Build a USB installer from Fiery DVD components")
  ArgParser.add_argument("--Dest", dest="Destination", help="output destination.")
  ArgParser.add_argument("--Product", dest="ProductName", help="product name (as you'd like to reference it on disk)")
  ArgParser.add_argument("--WINVER", help="windows OS version; default is win7/8",default=None)
  ArgParser.add_argument("--conf", help="optional file containing ISO information. NOTE: if --conf conflicts with other arguments, --conf will override them.",default=None)
  ArgParser.add_argument("--pull_isos", help="copy ISOs locally before mounting them", default="True")

  ISOArgs = ArgParser.add_argument_group("Source ISOs")
  ISOArgs.add_argument("--Installer", dest="InstallerISO", help="OS installer spec for decoupling", default=None)
  ISOArgs.add_argument("--Fiery", dest="FieryISO", help="fiery OS image ISO, eg:  /server_software/ellington1.0j/ellington1.0j_090815_090453.iso")
  ISOArgs.add_argument("--OS1", dest="OsISO1", help="first OS image ISO")
  ISOArgs.add_argument("--OS2", dest="OsISO2", help="second OS image ISO")
  ISOArgs.add_argument("--usersw", help="user software ISO", default=None)
  ISOArgs.add_argument("--Adobe", help="Adobe software ISO",default=None)
  ISOArgs.add_argument("--FCPS", help="FCPS software ISO",default=None)
  Args = ArgParser.parse_args()

  if Args.conf != None:
     Args = fixup_args(Args)

  if is_arg_set_empty(Args):
    ArgParser.print_help()
  else:
    check_for_required_arguments(Args)

  return Args
