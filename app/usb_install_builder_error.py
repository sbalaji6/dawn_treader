### exceptions
class USBInstallBuilderError(Exception):
  def __init__(self, value):
     self.value = value
  def __str__(self):
     return self.value

def log_without_throw(Err, Log=None, WriteToStdout = False):
   if (Log != None):
     Log.write(Err + "\n")
   if WriteToStdout==True:
     print Err
   return Err

def log_and_throw(Err, Log=None):
  log_without_throw(Err, Log)
  raise USBInstallBuilderError(Err)

