import os
import usb_install_builder_error
import product_iso_set

def write_manifest(destination, product_name, date_time, product_isos):
   try:
     manifest_filename = os.path.join(destination, "manifest.txt")
     with open(manifest_filename, "w+") as f:
       f.write("---USB THUMB DRIVE CREATOR MANIFEST----\n\n")
       f.write("Product: {0}\n".format(product_name))
       f.write("Time Created: {0}\n".format(date_time))
       f.write("FIERY ISO: {0}\n".format(product_isos.Fiery.iso_name))
       f.write("OS ISO #1: {0}\n".format(product_isos.OS1.iso_name))
       f.write("OS ISO #2: {0}\n".format(product_isos.OS2.iso_name))
       if product_isos.UserSoftware.iso_name != None:
         f.write("User Software ISO: {0}\n".format(product_isos.UserSoftware.iso_name))
       if product_isos.Adobe.iso_name != None:
         f.write("Adobe ISO: {0}\n".format(product_isos.Adobe.iso_name))
       if product_isos.FCPS.iso_name != None:
         f.write("FCPS ISO: {0}\n".format(product_isos.FCPS.iso_name))
     return "created manifest.txt{0}\n".format(manifest_filename)
   except:
     raise usb_install_builder_error.USBInstallBuilderError("UNABLE TO WRITE TO MANIFEST\n")
