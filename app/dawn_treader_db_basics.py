from peewee import *
from datetime import datetime

database = SqliteDatabase('/opt/tools/dawn_treader/app/dawn_treader.db')

class DawnTreaderBaseModel(Model):
  class Meta:
     database = database

class DawnTreaderUSBData(DawnTreaderBaseModel):
  id = PrimaryKeyField()
  status = CharField(default = "created")
  created_time = DateTimeField(default = datetime.now())
  product_name = CharField(default = "")
  fiery_iso = CharField(default = "")
  usersw_iso = CharField(default = "")
  osiso_one = CharField(default = "")
  osiso_two = CharField(default = "")
  adobe_iso = CharField(default = "")
  fcps_iso = CharField(default = "")
  other_isos = CharField(default = "")
  destination = CharField(default = "")
  manifest = CharField(default = "")
  logfile = CharField(default = "")
  updated_time = DateTimeField(default = datetime.now())

  def dump_job(self):
    retval = {}
    retval["id"] = self.id
    retval["status"] = self.status
    retval["created_time"] = self.created_time
    retval["product_name"] = self.product_name
    retval["fiery_iso"] = self.fiery_iso
    retval["usersw_iso"] = self.usersw_iso
    retval["osiso_one"] = self.osiso_one
    retval["osiso_two"] = self.osiso_two
    retval["adobe_iso"] = self.adobe_iso
    retval["fcps_iso"] = self.fcps_iso
    retval["other_isos"] = self.other_isos
    retval["destination"] = self.destination
    retval["manifest"] = self.manifest
    retval["logfile"] = self.logfile
    retval["updated_time"] = self.updated_time
    return retval

  def initialize(self, destination, product_name, fiery_iso, osiso_one, osiso_two, usersw, adobe, fcps):
    print "initializing"
    self.destination = destination
    self.product_name = product_name
    self.fiery_iso = fiery_iso
    self.osiso_one = osiso_one
    self.osiso_two = osiso_two
    self.usersw_iso = usersw
    self.adobe_iso = adobe
    self.fcps_iso = fcps
    self.status = "initialized"
    self.updated_time = datetime.now()
    self.save()

  def initialize_with_args(self, args):
    print "initializing with args: {}".format(args)
    self.destination = args.Destination
    self.product_name = args.ProductName
    self.fiery_iso = args.FieryISO
    self.osiso_one = args.OsISO1
    self.osiso_two = args.OsISO2
    self.usersw_iso = args.usersw 
    if args.Adobe:
      self.adobe_iso = args.Adobe
    if args.FCPS:
      self.fcps = args.FCPS
    self.status = "initialized"
    self.updated_time = datetime.now()
    self.save()

  def mark_error(self, err):
    print "mark error"
    self.status = err
    self.update_time = datetime.now()
    self.save()

  def mark_success(self):
    print "mark success"
    self.status = "success"
    self.update_time = datetime.now()
    self.save()


def dump():
  print "dumping"
  usb_jobs = DawnTreaderUSBData.select()

  print "len == {}".format(len(usb_jobs))
  for job in usb_jobs:
     print job.dump_job()
