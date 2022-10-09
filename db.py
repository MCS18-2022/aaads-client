import firebase_admin
from firebase_admin import credentials, storage, db
from pathlib import Path


__all__ = ("upload", "download_preds")


"""
Firebase Storage Database.

The connection to the Firebase Storage database will be
established the moment this module is imported to another
module.
"""

# The private key can be downloaded as a JSON file at
#   Firebase console
# > Project settings
# > Service accounts
# > Firebase Admin SDK
# > Generate new private key.
DB_PRIVATE_KEY = Path(".", "db_acc_cert.json")

# Storage link is found at Firebase Storage page.
# Paste it here WITHOUT the "gs://" prefix as a string.
STORAGE_URL = "aggressive-action-detection.appspot.com"

cred = credentials.Certificate(str(DB_PRIVATE_KEY))
app = firebase_admin.initialize_app(cred, {"storageBucket": STORAGE_URL})
bucket = storage.bucket()


def upload(path):
    """
    Upload a file to the Firebase Storage.

    Parameter:
    path : The path to the local file.
    """
    blob = bucket.blob(path)
    blob.upload_from_filename(path)


"""
Firebase Realtime Database.
"""

# Realtime Database link is found at Firebase Realtime Database page.
# Paste it here verbatim as a string.
REALTIME_DB_URL = "https://aggressive-action-detection-default-rtdb.asia-southeast1.firebasedatabase.app/"

realtime_db_ref = db.reference("/", url=REALTIME_DB_URL)


def download_preds():
    """
    Download all predictions in the Firebase Realtime Database,
    return in the form of a Python dictionary.
    """
    return realtime_db_ref.get()
