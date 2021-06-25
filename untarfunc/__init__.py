import logging
import tarfile
import tempfile
import shutil
import time
import os
import re
import azure.functions as func
from azure.storage.blob import BlobServiceClient

SOURCE_CONTAINER = 'test'
DESTINATION_CONTAINER = "dest"
ACCOUNT_URL = "https://arongkstorageacc.blob.core.windows.net/"
CREDENTIAL = "8c4PujlNq2zxpca3gWcrLAam8iwEwditRTnMML/96c7FZI0T918Q8Pahxcu4sia6K8jaDRXiwj1AHR//Q270yQ=="

service = BlobServiceClient(account_url=ACCOUNT_URL, credential=CREDENTIAL)
temp_folder = tempfile.gettempdir()

# the blobName includes the container name, only blobName is required for further processing
def remove_container_name_from_path(path):
    return re.sub(r"\w+\/", "", path)

# this is the folder used for temporarily storing files for the blob under execution
# used time since epoch and filename to make the folder unique, it will be deleted after execution
def get_temp_extraction_folder_folder(blob_name):
    millis_since_epoch = round(time.time() * 1000)
    return str(millis_since_epoch) + "_" + blob_name

def extract_tar_file(myblob):
    blob_name = remove_container_name_from_path(myblob.name)
    blobClient = service.get_blob_client(container=SOURCE_CONTAINER, blob=blob_name)
    extraction_folder = get_temp_extraction_folder_folder(blob_name)
    downloadedTarPath = os.path.join(temp_folder, extraction_folder, blob_name)
    extracted_folder = os.path.join(temp_folder, extraction_folder, "extracted")
    os.makedirs(extracted_folder)
    with open(downloadedTarPath, "wb") as my_blob:
        # blob_data = blobClient.download_blob()
        # my_blob.write(blob_data.content_as_bytes())
        bytesRemaining = myblob.length
        chunk_size= 8*1024*1024 #the chunk size
        start = 0
        while bytesRemaining > 0 :
            if bytesRemaining < chunk_size:
                bytesToFetch = bytesRemaining
            else:
                bytesToFetch = chunk_size
            downloader = blobClient.download_blob(start,bytesToFetch)
            # b = downloader.readinto(f)
            my_blob.write(downloader.content_as_bytes())
            # print(b)
            start += bytesToFetch
            bytesRemaining -= bytesToFetch

    if tarfile.is_tarfile(downloadedTarPath):
        logging.info(f"Started to untar " + blob_name)
        my_tar = tarfile.open(downloadedTarPath)
        for fileName in my_tar.getnames():
            if fileName != '.' or fileName != '..':
                my_tar.extract(fileName, path=extracted_folder)  
                blobClient = service.get_blob_client(container=DESTINATION_CONTAINER, blob=fileName)
                # the response to be saved, strategy under discussion
                response = blobClient.upload_blob(os.path.join(extracted_folder, fileName), overwrite=True)
                logging.info(response)
        logging.info(f"Done untarring " + blob_name)
        my_tar.close()
    else:
        logging.info(f"The uploade file [" + blob_name + "] is not a tar file")
    # cleanup
    shutil.rmtree(os.path.join(temp_folder, extraction_folder))

def main(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Name: {myblob.name}\n"
                 f"Blob Size: {myblob.length} bytes")
    try:
        extract_tar_file(myblob)
        logging.info(f"Completed untarring " + myblob.name)
    except:
        logging.info(f"An error occured while extracting " + myblob.name)