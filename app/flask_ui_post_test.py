from requests import post
import json

test_url = "http://roshar.efi.com:8989/api/v1/add_from_app"

outgoing = {}
outgoing["status"] = "test"
outgoing["product_name"] = "PortlandPDXDivision"
outgoing["fiery_iso"] = "/dev/null"
outgoing["usersw_iso"] = "/dev/null"
outgoing["osiso_one"] = "/dev/null"
outgoing["osiso_two"] = "3551 Division"

resp = post(test_url, json=outgoing)

print resp
#print json.loads(resp.text)
