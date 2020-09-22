from flask import Flask, make_response, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

from flask_rest_jsonapi import Api, ResourceDetail, ResourceList, ResourceRelationship

from marshmallow_jsonapi.flask import Schema, Relationship

from marshmallow_jsonapi import fields

MAX_STRLEN = 255

dt_flask = Flask(__name__)
dt_flask.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////opt//tools//dawn_treader//db//dt_flask.db'

CORS(dt_flask)

db = SQLAlchemy(dt_flask)

class USBInstall(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  status = db.Column(db.String(MAX_STRLEN), nullable=False)
  product_name = db.Column(db.String(MAX_STRLEN), nullable=False)
  fiery_iso = db.Column(db.String(MAX_STRLEN), nullable=False)
  usersw_iso = db.Column(db.String(MAX_STRLEN), nullable=False)
  osiso_one = db.Column(db.String(MAX_STRLEN), nullable=False)
  osiso_two = db.Column(db.String(MAX_STRLEN), nullable=False)
  adobe_iso = db.Column(db.String(MAX_STRLEN), nullable=True)
  fcps_iso = db.Column(db.String(MAX_STRLEN), nullable=True)
  other_isos = db.Column(db.String(1023), nullable=True)
  reserved_one = db.Column(db.String(MAX_STRLEN), nullable=True)
  reserved_two = db.Column(db.String(MAX_STRLEN), nullable=True)
  reserved_three = db.Column(db.String(MAX_STRLEN), nullable=True)
  reserved_four = db.Column(db.String(MAX_STRLEN), nullable=True)
  created_time = db.Column(db.DateTime, nullable=False)
  updated_time = db.Column(db.DateTime, nullable=False)

  def __repr__(self):
    return '<' + self.__class__.__name__ + ' ' + str(self.id) + '>'

class USBInstallSchema(Schema):
  class Meta:
    type_ = 'usbinstall'
    self_view = 'usbinstall_detail'
    self_view_kwargs = { 'id' : '<id>' }
    self_view_many = 'usbinstall_list'
  id = fields.Integer(as_string=True, dump_only=True)
  product_name = fields.Str()
  fiery_iso = fields.Str()
  usersw_iso = fields.Str()
  osiso_one = fields.Str()
  osiso_two = fields.Str()
  adobe_iso = fields.Str()
  fcps_iso = fields.Str()
  other_isos =  fields.Str()
  reserved_one =  fields.Str()
  reserved_two =  fields.Str()
  reserved_three =  fields.Str()
  reserved_four =  fields.Str()
  created_time = fields.DateTime()
  updated_time = fields.DateTime()

class USBInstallList(ResourceList):
  schema = USBInstallSchema
  data_layer = { 'session' : db.session, 'model' : USBInstall }

class USBInstallDetail(ResourceDetail):
  schema = USBInstallSchema
  data_layer = { 'session' : db.session, 'model' : USBInstall }

api = Api(dt_flask)
api.route(USBInstallList, 'usbinstall_list', '/api/v1/usbinstall')
api.route(USBInstallDetail, 'usbinstall_detail', '/api/v1/usbinstall/<int:id>')

@dt_flask.route('/api/v1/add_from_app', methods = ['POST',])
def insert_db_record_from_app():

  def request_json_looks_good(request_json):
     return True

  def create_usb_install_object(request_json, right_here_right_now):
    new_record = USBInstall(status="New", fiery_iso=request_json["fiery_iso"], osiso_one=request_json["osiso_one"],osiso_two=request_json["osiso_two"],usersw_iso=request_json["usersw_iso"],product_name=request_json["product_name"],created_time=right_here_right_now, updated_time=datetime.now())
    try:
      new_record.adobe_iso = request_json["adobe_iso"]
    except:
      pass
    try:
      new_record.fcps_iso = request_json["fcps_iso"]
    except:
      pass
    try:
      new_record.fcps_iso = request_json["fcps_iso"]
    except:
      pass
    return new_record

  request_json = request.get_json()
  with open('/tmp/drflask.out', 'w+') as outfile:
    outfile.write("{}\n".format(request_json))

  if request_json_looks_good(request_json):
     right_here_right_now = datetime.now()

     new_record = create_usb_install_object(request_json, right_here_right_now)
     db.session.add(new_record)
     db.session.commit()

     newly_created = USBInstall.query.filter_by(created_time=right_here_right_now).first()
     if newly_created is not None:
        return make_response(str(newly_created.id))
     return make_response("no")
  else:
     return make_response("no")

@dt_flask.route('/api/v1/update_status', methods = ['POST',])
  def request_json_looks_good(request_json):
    return True

  request_json = request.get_json()
  if request_json_looks_good(request_json):
    record_to_update = USBInstall.query.filter_by(id=request_json["id"])
    record_to_update.status = request_json["status"]
    record_to_update.updated_time = datetime.now()
    db.session.commit()
    return make_response("yes")
  else:
    return make_response("no")
  

def recreate(db):
  db.drop_all()
  db.create_all()
  db.session.add(USBInstall(status="Testing", product_name="no_application", fiery_iso = "/dev/null", usersw_iso = "/dev/null", osiso_one = "/dev/null", osiso_two = "/dev/null", created_time = datetime.now(), updated_time = datetime.now()))
  db.session.commit()
