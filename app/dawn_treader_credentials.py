import os
import json

from dawn_treader_server_id import server_is_rms_type
from dawn_treader_server_id import server_is_qaserv_type

RMS_USER_CREDS_FILE = "/opt/tools/dawn_treader/creds/rms.creds"
QASERV_CREDS_FILE = "/opt/tools/dawn_treader/creds/qaserv.creds"
LOCAL_CREDS_FILE = "/opt/tools/dawn_treader/creds/local.creds"
PROD_RMS_FTP_CREDS_FILE = "/opt/tools/dawn_treader/creds/rms_ftp.creds"
LOCAL_RMS_FTP_CREDS_FILE = "./rms_ftp.creds"

# object containing credentials

class DawnTreaderLocalCredentials(object):
  def __init__(self, uid, gid, storage=None):
    self.uid = uid
    self.gid = gid
    self.iso_storage = storage

class DawnTreaderServerCredentials(object):
  def __init__(self, uname, pwd, domain=None):
    self.Username = uname
    self.Password = pwd
    self.Domain = domain

# internal helper functions

def verify_credentials(new_creds, default_creds):
  if new_creds.Username == None:
    return default_creds
  else:
    return new_creds

def get_credentials_from_file(cred_file):
  retval = DawnTreaderServerCredentials(None, None)
  if os.path.exists(cred_file):
    file_data = json.loads(open(cred_file).read())
    retval.Username = read_if_exists(file_data, "username")
    retval.Password = read_if_exists(file_data, "password")
    retval.Domain = read_if_exists(file_data, "domain")
  return retval

def get_local_credentials_from_file():
   retval = DawnTreaderLocalCredentials(None, None)
   if os.path.exists(LOCAL_CREDS_FILE):
     file_data = json.loads(open(LOCAL_CREDS_FILE).read())
     retval.uid = read_if_exists(file_data, "uid")
     retval.gid = read_if_exists(file_data, "gid")
     retval.iso_storage = read_if_exists(file_data, "storage")
   return retval

def read_if_exists(cred_file_map, cred):
  if cred in cred_file_map:
    return cred_file_map[cred]
  else:
    return None

# efficiency is served if these are preloaded
DefaultCredentials = DawnTreaderServerCredentials("guest", "guest")
LocalCredentials = get_local_credentials_from_file()
RMS_user_credentials = get_credentials_from_file(RMS_USER_CREDS_FILE)
QAServCredentials = get_credentials_from_file(QASERV_CREDS_FILE)

# public function which retrieves the local server credentials
def get_credentials_for_local():
  return LocalCredentials

# public function which either returns the preloaded RMS and QAServ 
# credentials or calls __get_credentials_for_server for more.

def get_credentials_for_server(Server):
  if not "//" in Server[0:2]:
    return DefaultCredentials
  if server_is_rms_type(Server):
   return verify_credentials(RMS_user_credentials, DefaultCredentials)
  elif server_is_qaserv_type(Server):
   return verify_credentials(QAServCredentials, DefaultCredentials)
  return DefaultCredentials
