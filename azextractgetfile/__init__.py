import logging

import azure.functions as func
from azure.storage.blob import BlobServiceClient

ACCOUNT_URL = "https://arongkstorageacc.blob.core.windows.net/"
CREDENTIAL = "8c4PujlNq2zxpca3gWcrLAam8iwEwditRTnMML/96c7FZI0T918Q8Pahxcu4sia6K8jaDRXiwj1AHR//Q270yQ=="
DESTINATION_CONTAINER = "dest"


def get_file_name(path):
    last_indes_of_slash = path.rindex("/")
    if last_indes_of_slash == -1:
        return path
    return path[last_indes_of_slash + 1:]

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    path = req.params.get('name')
    if not path:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            path = req_body.get('name')

    if path:
        filename = get_file_name(path)
        service = BlobServiceClient(account_url=ACCOUNT_URL, credential=CREDENTIAL)
        blobClient = service.get_blob_client(container=DESTINATION_CONTAINER, blob=path)
        downloader = blobClient.download_blob()
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-disposition": "attachment; filename=" + filename
        }
        resp = func.HttpResponse(downloader.content_as_bytes(), status_code=200, headers=headers)
        return resp
    else:
        return func.HttpResponse(
             "You need to pass the name of the file to be downloaded",
             status_code=200
        )
