import asyncio
import azure.functions as func
import logging
import os
import shutil
import tarfile
import tempfile
import threading
import time
import traceback
from azure.storage.blob import BlobServiceClient

# test comment updated2
STATUS_CONTAINER = 'status'
AUDIT_CONTAINER = 'audit'
SOURCE_CONTAINER = 'source'
DESTINATION_CONTAINER = "dest"
ACCOUNT_URL = "https://arongkstorageacc.blob.core.windows.net/"
CREDENTIAL = "8c4PujlNq2zxpca3gWcrLAam8iwEwditRTnMML/96c7FZI0T918Q8Pahxcu4sia6K8jaDRXiwj1AHR//Q270yQ=="
CHUNK_SIZE = 50 * 1024 * 1024

class BlobConfig():

    def __init__(self, blob_name, content_length):
        self.blob_name = blob_name
        self.content_length = int(content_length)

    def setup_files(self):
        self.temp_folder = tempfile.gettempdir()
        self.blob_temp_folder = self.get_temp_extraction_folder_folder(self.blob_name)
        self.tar_path = os.path.join(self.temp_folder, self.blob_temp_folder, self.blob_name)
        self.extracted_folder = os.path.join(self.temp_folder, self.blob_temp_folder, "extracted", self.blob_name)
        self.audit_path = os.path.join(self.temp_folder, self.blob_temp_folder) + '/' + self.blob_name + '.audit.txt'
        self.runtime_file_path = os.path.join(self.temp_folder, self.blob_temp_folder) + '/' + self.get_runtime_file_name()
        os.makedirs(self.extracted_folder)
        self.create_runtime_file(self.runtime_file_path)
        self.create_audit_file(self.audit_path)

    def get_blob_name(self, event):
        subject = event.subject
        last_index_of_slash = subject.rindex("/")
        return subject[last_index_of_slash + 1:]

    def get_temp_extraction_folder_folder(self, blob_name):
        ''' 
        this is the folder used for temporarily storing files for the blob under execution
        used time since epoch and filename to make the folder unique, it will be deleted after execution
        '''
        millis_since_epoch = round(time.time() * 1000)
        return str(millis_since_epoch) + "_" + blob_name

    def get_runtime_file_name(self):
        return self.blob_name + ".status"

    def get_audit_file_name(self):
        return self.blob_name + ".audit.txt"

    def create_audit_file(self, audit_path):
        f = open(audit_path, 'w+')
        f.write('=== Audit ===\n') 
        f.close()

    def create_runtime_file(self, runtime_file_path):
        f = open(runtime_file_path, 'w+')
        f.write('=== Running ===\n')
        f.close()

    def get_content_length(self, event):
        data = event.get_json()
        return data.get("contentLength")

class BlobClientFacade():

    def __init__(self, blob_config):
        self.service = BlobServiceClient(account_url=ACCOUNT_URL, credential=CREDENTIAL)
        self.config = blob_config

    def download_blob(self, container):
        logging.info("Started downloading " + self.config.blob_name )
        blobClient = self.service.get_blob_client(container=container, blob=self.config.blob_name)
        with open(self.config.tar_path, "wb") as my_blob:
            bytesRemaining = self.config.content_length
            start = 0
            while bytesRemaining > 0:
                logging.info("bytesRemaining " + str(bytesRemaining))
                if bytesRemaining < CHUNK_SIZE:
                    bytesToFetch = bytesRemaining
                else:
                    bytesToFetch = CHUNK_SIZE
                downloader = blobClient.download_blob(start, bytesToFetch)
                my_blob.write(downloader.content_as_bytes())
                start += bytesToFetch
                bytesRemaining -= bytesToFetch
        logging.info("Done downloading " + self.config.blob_name)

    def upload_to_blob_storage(self):
        source = self.config.extracted_folder
        audit_path = self.config.audit_path
        blob_name = self.config.blob_name
        prefix = ''
        prefix += os.path.basename(source) + '/'
        client = self.service.get_container_client(DESTINATION_CONTAINER)
        audit_file = open(audit_path, 'w+')
        object_count = 0
        for root, dirs, files in os.walk(source):
            for name in files:
                dir_part = os.path.relpath(root, source)
                dir_part = '' if dir_part == '.' else dir_part + '/'
                file_path = os.path.join(root, name)
                blob_path = prefix + dir_part + name
                self.upload_file(client, file_path, blob_path)
                audit_file.write("Uploaded " + blob_path + "\n")
                object_count += 1
        audit_file.write("=== Done uploading " + blob_name + " " + str(object_count) + " objects uploaded ===\n")
        audit_file.close()
        self.save_audit_file()
        logging.info("Done uploading files of blob " + source)

    def upload_file(self, client, source, dest):
        '''
        Upload a single file to a path inside the container
        '''
        logging.info('Uploading ' + source + ' to ' + dest)
        with open(source, 'rb') as data:
            client.upload_blob(name=dest, data=data, overwrite=True)

    def save_audit_file(self):
        client = self.service.get_container_client(AUDIT_CONTAINER)
        self.upload_file(client, self.config.audit_path, self.config.get_audit_file_name())

    def has_execution_started(self):
        blob = self.service.get_blob_client(container=STATUS_CONTAINER, blob=self.config.get_runtime_file_name())
        return blob.exists()

    def save_runtime_blob(self):
        client = self.service.get_container_client(STATUS_CONTAINER)
        self.upload_file(client, self.config.runtime_file_path, self.config.get_runtime_file_name())


def is_source_container(event):
    subject = event.subject
    return  'containers/' + SOURCE_CONTAINER in subject

def extract_all(blobClientFacade):
    config = blobClientFacade.config
    if tarfile.is_tarfile(config.tar_path):
        my_tar = tarfile.open(config.tar_path)
        my_tar.extractall(path=config.extracted_folder)
        my_tar.close()
        blobClientFacade.upload_to_blob_storage()
    else:
        logging.info("The uploaded file [" + config.blob_name + "] is not a tar file.")

def extract_tar_file(blobClientFacade):
    try:
        config = blobClientFacade.config
        blobClientFacade.download_blob(SOURCE_CONTAINER)
        extract_all(blobClientFacade)
    except:
        traceback.print_exc()
        logging.info("An error occured while untarring " + config.blob_name)
    finally:
        # delete the temp folder used to store the downloaded blob
        logging.info("Cleaning up resources " + config.blob_name)
        shutil.rmtree(os.path.join(config.temp_folder, config.blob_temp_folder))

async def start(blobClientFacade):
    asyncio.create_task(extract_tar_file(blobClientFacade))

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    blob_name = req.form.get('name')
    content_length = req.form.get('content-length')
    blob_config = BlobConfig(blob_name, content_length)
    blobClientFacade = BlobClientFacade(blob_config=blob_config)
    if not blobClientFacade.has_execution_started():
        blob_config.setup_files()
        blobClientFacade.save_runtime_blob()
        thread = threading.Thread(target=extract_tar_file, args=(blobClientFacade,))
        thread.start()
        return func.HttpResponse("SUCCESS", status_code=200)
    else:
        logging.info('Skipped executing, execution is already in progress: %s', blob_config.blob_name)
        return func.HttpResponse("ALREADY_IN_PROGRESS", status_code=200)