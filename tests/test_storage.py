"""Document storage adapter regression tests; no live bucket is contacted."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.storage import LocalStorage, S3Storage


class Body:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def read(self):
        return self.payload

    def close(self):
        self.closed = True


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.last_put = None
        self.last_body = None

    def put_object(self, **kwargs):
        self.last_put = kwargs
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, Bucket, Key):
        self.last_body = Body(self.objects[(Bucket, Key)])
        return {"Body": self.last_body}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


class StorageAdapterTests(unittest.TestCase):
    def test_local_storage_round_trip_and_rejects_path_keys(self):
        with tempfile.TemporaryDirectory() as root:
            store = LocalStorage(root)
            store.put("abc123.pdf", b"synthetic bytes", "application/pdf")
            self.assertEqual(store.get("abc123.pdf"), b"synthetic bytes")
            store.delete("abc123.pdf")
            with self.assertRaises(FileNotFoundError):
                store.get("abc123.pdf")
            for key in ("../secret", "/absolute", "nested/file", "", ".."):
                with self.assertRaises(ValueError):
                    store.put(key, b"x")

    def test_s3_adapter_encrypts_writes_and_closes_read_stream(self):
        client = FakeS3()
        store = S3Storage("synthetic-test-bucket", client=client)
        store.put("sha256.txt", b"test-data", "text/plain")
        self.assertEqual(client.last_put["ServerSideEncryption"], "AES256")
        self.assertEqual(client.last_put["ContentType"], "text/plain")
        self.assertEqual(store.get("sha256.txt"), b"test-data")
        self.assertTrue(client.last_body.closed)
        store.delete("sha256.txt")
        self.assertNotIn(("synthetic-test-bucket", "sha256.txt"), client.objects)

    def test_s3_adapter_rejects_user_controlled_paths(self):
        store = S3Storage("synthetic-test-bucket", client=FakeS3())
        with self.assertRaises(ValueError):
            store.get("../private-document")


if __name__ == "__main__":
    unittest.main(verbosity=2)
