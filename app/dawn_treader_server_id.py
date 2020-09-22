# this is kind of silly, BUT
#
# rms can be multiple different servers.
#
# qaserv right now can't, and yet
#
# i think it makes consumer code look cleaner to have these functions rather than
# straight up string compares

def server_is_rms_type(server):
  if "fcmrms" in server:
    return True
  elif "blrmrms" in server:
    return True
  else:
    return False

def server_is_qaserv_type(server):
  if "qaserv" in server:
    return True
  else:
    return False

