import datetime
import sys
import os
import shutil

import dawn_treader_arguments
import dawn_treader_destination
import dawn_treader_helpers
import product_iso_set
import dawn_treader_local_copy_controller
import manifest

from usb_install_builder_error import log_without_throw
from usb_install_builder_error import USBInstallBuilderError

class USBImageBuilder(object):
    def __init__(self, destination, product_isos, winver=8):
        self.destination = destination
        self.product_isos = product_isos
        self.winver = int(winver)
        self.log_path = os.path.join(self.destination.FullDestination,  "builder.log")

        if not self.winver in [7, 8]:
            raise USBInstallBuilderError("ERROR: unknown OS version {}".format(self.winver))

    def create_log(self):
        try:
            self.builder_log = open(self.log_path, "w+")
        except IOerror:
            raise USBInstallBuilderError("Unable to create log at {}".format(self.log_path))

        self.product_isos.set_log(self.builder_log)
        self.builder_log.write("---USB THUMB DRIVE CREATOR LOG---")

        return True

    def create_manifest(self):
        ctime = self.destination.CreationDateTime
        msg = manifest.write_manifest(self.destination.FullDestination, self.destination.ProductName, ctime.strftime("%Y-%M-%D %H:%M:%S"), self.product_isos)
        self.builder_log.write(msg)

    def mount_isos(self):
        log_without_throw("mounting", self.builder_log)
        self.product_isos.mount_isos()
        log_without_throw("mounted", self.builder_log)

    def unmount_isos(self):
        self.product_isos.unmount_isos()

    def initialize_destination_dirs(self):
        try:
           self.destination.validate_and_make_destinations()
           self.create_log()
        except USBInstallBuilderError, e:
            return e.value

        try:
            self.create_manifest()
        except USBInstallBuilderError, e:
            self.builder_log.write(e.value)
            self.product_isos.set_log(None)
            self.builder_log.close()

            return e.value

    def unmount_destination_dirs(self):
        return destination.unmount_destination_dir()

    def build(self):
        try:
            log_without_throw("building windows image", self.builder_log)
            self.mount_isos()
            log_without_throw("trying to copy_fiery_iso", self.builder_log)
            if self.product_isos.Installer.iso_name != None:
                self.product_isos.copy_installer_iso(self.destination.USBDestination)
            self.product_isos.copy_fiery_iso(self.destination.USBDestination)
            self.product_isos.copy_windows_isos(self.destination.USBDestination)
            self.product_isos.copy_and_modify_usersw_iso(self.destination.USBDestination)
            self.product_isos.copy_and_modify_adobe_iso(self.destination.USBDestination)
            self.product_isos.copy_and_modify_fcps_iso(self.destination.USBDestination)
            self.product_isos.copy_windows_permission_override_behavior(self.destination.USBDestination)

            msg = "Success!\nlog and manifest created at {}\nUSB Installer created at {}".format(self.destination.FullDestination, self.destination.USBDestination)
            log_without_throw(msg, self.builder_log, WriteToStdout=True)
        except USBInstallBuilderError, e:
            self.builder_log.write(e.value)
            exit(e.value)
        except IOError as e:
            self.builder_log.write("Critical I/O error encountered: {}: {}\n".format(e.errno, e.strerror))
            exit(e.errno)
        except Exception as e:
            self.builder_log.write("Critical error encountered: {}\n".format(e))
        finally:
            try:
                self.unmount_isos()
                self.product_isos.set_log(None)
                self.builder_log.close()
            except Exception as e:
                self.builder_log.write("something unexpected happened while trying to clean up. {}".format(e))


if __name__ == "__main__":
    try:
        args = dawn_treader_arguments.parse_arguments()
        try:
            if args.Destination != None:
                if args.pull_isos == "True":
                    dawn_treader_local_copy_controller.use_local_copy_capacities()
                product_isos = product_iso_set.get_product_isos(args)
                destination = dawn_treader_destination.get_destination(args, datetime.datetime.now())
                builder = USBImageBuilder(destination, product_isos, args.WINVER)
                retval = builder.initialize_destination_dirs()
                if retval == None:
                    builder.build()
                    builder.unmount_destination_dirs()
                    sys.exit(0)
                else:
                    print("wtf")
                    sys.exit(retval)
        except IOError, e:
            # print("I/O error {} : {}".format(e.errno, e.strerror))
            raise
        except Exception as e:
            # print("Error: {}".format(e))
            raise
    except Exception as e:
      # print("Error: {}".format(e))
      raise
      sys.exit(500)
