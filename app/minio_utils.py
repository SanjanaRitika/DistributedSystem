import logging
from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile

logging.basicConfig(level=logging.INFO)

minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)


def upload_file_to_minio(file: UploadFile, bucket_name: str = "posts"):
    try:
        if not minio_client.bucket_exists(bucket_name):
            logging.info(f"Bucket '{bucket_name}' does not exist. Creating bucket...")
            minio_client.make_bucket(bucket_name)

        object_name = file.filename
        logging.info(f"Uploading '{object_name}' to bucket '{bucket_name}'...")

        minio_client.put_object(
            bucket_name, object_name, file.file, length=-1, part_size=10*1024*1024
        )

        return f"http://localhost:9000/{bucket_name}/{object_name}"

    except S3Error as e:
        logging.error(f"MinIO error: {e}")
        raise e
