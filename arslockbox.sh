# USAGE: ./arslockbox.sh <blob-name>

#!/bin/bash
storageaccount="arongkstorageacc"
http_trigger_endpoint="https://azextractapp.azurewebsites.net/api/azextracthttptrigger"
keys_endpoint="https://azextractapp.azurewebsites.net/api/lockboxkeys?code=x9TwsE3xrStiHbyd09owG9vihTRY5Y71TKeN0IldnrzgvqfgbNajVA=="
http_trigger_code="LLts8VK7IsJiZV/x3M59yIUjU8r8LfsqSHJFgUURzzL9CMUiJ9AjDQ=="
source="source"
dest="dest"
audit="audit"

blob=$1
file="./$1"
contentLength=$(stat --format="%s" ${blob})

# get SAS tokens
source_sas_token=$(curl -d "name=source" -X POST "${keys_endpoint}")
dest_sas_token=$(curl -d "name=dest" -X POST "${keys_endpoint}")
audit_sas_token=$(curl -d "name=audit" -X POST "${keys_endpoint}")

# upload blob to the source storage, exit if the blob can't uploaded
curl -X PUT -T ${file} -H "x-ms-date: $(date -u)" -H "x-ms-blob-type: BlockBlob" "https://${storageaccount}.blob.core.windows.net/${source}/${blob}?${source_sas_token}"
if [ $? -ne 0 ]; then
   echo "Could not upload ${file} to the source container"
   exit
fi

# execute the http-trigger, if the response is SUCCESS, wait for the audit file to be created before downloading the untarred files
http_trigger_response=$(curl -d "name=${blob}&content-length=${contentLength}" -X POST "${http_trigger_endpoint}?code=${http_trigger_code}")
if [ $? -ne 0 ]; then
   echo "http-trigger function failed"
   exit
fi
if [ "$http_trigger_response" != "SUCCESS" ]; then
   echo "http-trigger already executed"
   exit
fi

# wait for the audit file to be created which marks the completion of untarring
audit_file_name="${blob}.audit.txt"
while curl "https://${storageaccount}.blob.core.windows.net/${audit}/${audit_file_name}?${audit_sas_token}&comp=metadata" | grep BlobNotFound
do
    echo "audit file not found, sleeping for 30s"
    sleep 30s
done

# download the tar files from the dest container
echo "audit file found, downloading tar files."

# this returns the list of untarred blobs, the response is in XML format
blobs=$(curl "https://${storageaccount}.blob.core.windows.net/${dest}?prefix=${blob}&restype=container&comp=list&${dest_sas_token}" | grep -oP '(?<=Name>)[^<]+')

# create the folder where the untarred files will be saved
download_folder="downloads/${blob}"
mkdir -p ${download_folder}
cd ${download_folder}

IFS=$'\n'
for line in $blobs
do
    # replace / with _ to create a file name without the folder structure, TO-DO: preserve the folder structure
    local_file_name=$(echo $line | sed "s/\//_/g")
    # in blob storage, spaces are encoded with %20
    file_name=$(echo $line | sed "s/ /%20/g")
    # echo "Line: $file_name"
    curl "https://${storageaccount}.blob.core.windows.net/${dest}/${file_name}?${dest_sas_token}" --output $local_file_name
done

echo "DONE: ${blob}"
