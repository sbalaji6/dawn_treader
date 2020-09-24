from xml.etree.ElementTree import ElementTree
import xml

def replace_information_in_xml_file_flame9(Subdir, XMLFileName):
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

      p = tree.findall(".//{http://PlatformGroup.efi.com/Fiery/SubsystemSetup}ExternalTaskInfo")
      for item in p:
          temp = item.attrib['MediaMountPoint']
          print(temp)
          item.attrib['MediaMountPoint'] = "\\" + Subdir  + temp
      xml.etree.ElementTree.dump(tree)
      tree.write(XMLFileName+ ".new",xml_declaration=True, method='xml', encoding='UTF-8')

replace_information_in_xml_file_flame9("Fiery","spec_server_sw.xml")