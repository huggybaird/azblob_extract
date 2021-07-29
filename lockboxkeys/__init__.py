import logging
import datetime
from azure.storage.blob._shared_access_signature import BlobSharedAccessSignature 
import azure.functions as func

ACCOUNT_NAME = "arongkstorageacc"
CREDENTIAL = "8c4PujlNq2zxpca3gWcrLAam8iwEwditRTnMML/96c7FZI0T918Q8Pahxcu4sia6K8jaDRXiwj1AHR//Q270yQ=="
service = BlobSharedAccessSignature(account_name=ACCOUNT_NAME, account_key=CREDENTIAL)

permissions = {
    'source': 'racwdl',
    'dest': 'rl',
    'audit': 'rl'
}

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    today = datetime.date.today()
    tomorrow = datetime.date.today() + datetime.timedelta(days=1, hours=1)
    container_name = req.form.get('name')
    if container_name:
        sas_token = service.generate_container(container_name, permission=permissions[container_name], expiry=tomorrow, start=today, protocol='https')
        return func.HttpResponse(sas_token)
    else:
        return func.HttpResponse(
            "Pass the name of the key to returned.", status_code=200
        )
