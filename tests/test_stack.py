from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError

import yaml

from client import completions
from render import render


class InferenceContract(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.headers.get("Authorization") != "Bearer test-only-token":
            self.send_error(401)
            return
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if payload["stream"]:
            body = b'data: {"choices":[{"delta":{"content":"GPU "}}]}\n\ndata: {"choices":[{"delta":{"content":"ready"}}]}\n\ndata: [DONE]\n\n'
        else:
            body = b'{"choices":[{"message":{"content":"GPU ready"}}]}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class StackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), InferenceContract)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_completion_contract(self):
        self.assertEqual(list(completions(self.endpoint, "test-only-token", "hello")), ["GPU ready"])

    def test_stream_contract(self):
        self.assertEqual("".join(completions(self.endpoint, "test-only-token", "hello", stream=True)), "GPU ready")

    def test_existing_v1_base_path(self):
        self.assertEqual(list(completions(self.endpoint + "/v1/", "test-only-token", "hello")), ["GPU ready"])

    def test_bad_auth(self):
        with self.assertRaises(HTTPError) as caught:
            list(completions(self.endpoint, "wrong-test-token", "hello"))
        self.assertEqual(caught.exception.code, 401)

    def test_missing_auth(self):
        with self.assertRaises(ValueError):
            list(completions(self.endpoint, "", "hello"))

    def test_firewall_is_required(self):
        with self.assertRaises(ValueError):
            render(0)

    def test_worker_firewall_contract(self):
        source = (Path(__file__).parents[1] / "terraform" / "main.tf").read_text()
        workers = source.split('resource "linode_firewall" "workers" {', 1)[1].split('resource "linode_firewall" "endpoint"', 1)[0]
        self.assertIn('inbound_policy  = "DROP"', workers)
        self.assertNotIn("0.0.0.0/0", workers)
        self.assertIn('ports    = "30000-32767"', workers)
        self.assertIn('ipv4     = ["192.168.255.0/24"]', workers)
        self.assertIn('protocol = "IPENCAP"', workers)
        self.assertIn('ports    = "179,5473,10250,10256"', workers)
        self.assertIn('ports    = "51820"', workers)
        cluster = source.split('resource "linode_lke_cluster" "inference" {', 1)[1]
        self.assertEqual(len(re.findall(r'firewall_id\s*=\s*linode_firewall.workers.id', cluster)), 2)

    def test_manifest_contract(self):
        docs = {item["kind"]: item for item in yaml.safe_load_all(render(123))}
        self.assertEqual(set(docs), {"Namespace", "PersistentVolumeClaim", "Deployment", "Service", "NetworkPolicy"})
        service = docs["Service"]
        self.assertEqual(service["metadata"]["annotations"]["service.beta.kubernetes.io/linode-loadbalancer-firewall-id"], "123")
        pod = docs["Deployment"]["spec"]["template"]["spec"]
        container = pod["containers"][0]
        self.assertEqual(container["resources"]["limits"]["nvidia.com/gpu"], 1)
        self.assertEqual(pod["nodeSelector"], {"workload": "inference"})
        self.assertFalse(pod["enableServiceLinks"])
        self.assertIn("--api-key=$(VLLM_API_KEY)", container["args"])
        self.assertIn("--enable-auto-tool-choice", container["args"])
        self.assertIn("--max-model-len=8192", container["args"])
        self.assertIn("--max-num-seqs=8", container["args"])
        self.assertIn("--gpu-memory-utilization=0.90", container["args"])
        self.assertEqual(docs["Deployment"]["spec"]["strategy"]["type"], "Recreate")
        self.assertEqual(container["startupProbe"]["failureThreshold"], 120)


if __name__ == "__main__":
    unittest.main()

