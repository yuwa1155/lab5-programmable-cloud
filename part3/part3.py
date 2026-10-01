import argparse
import json
from pathlib import Path
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "part1"))
from part1 import wait_for_operation


def main():
    directory = Path(__file__).resolve().parent
    part1_directory = directory.parent / "part1"
    key_path = directory / "service-credentials.json"
    credentials = service_account.Credentials.from_service_account_file(
        str(key_path),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=credentials.project_id)
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--machine-type", default="f1-micro")
    parser.add_argument("--vm1-name", default="lab5-part3-vm1")
    parser.add_argument("--vm2-name", default="lab5-part3-vm2")
    args = parser.parse_args()

    compute = build("compute", "v1", credentials=credentials)
    image = compute.images().getFromFamily(
        project="ubuntu-os-cloud", family="ubuntu-2204-lts"
    ).execute()

    vm2_config = {
        "project": args.project,
        "zone": args.zone,
        "machine_type": args.machine_type,
        "vm2_name": args.vm2_name,
    }
    metadata = {
        "startup-script": (directory / "vm1-startup-script.sh").read_text(),
        "service-credentials": key_path.read_text(),
        "config": json.dumps(vm2_config),
        "part1-code": (part1_directory / "part1.py").read_text(),
        "vm1-launch-vm2-code": (directory / "vm1-launch-vm2.py").read_text(),
        "vm2-startup-script": (
            part1_directory / "startup-script.sh"
        ).read_text(),
    }

    config = {
        "name": args.vm1_name,
        "machineType": (
            f"zones/{args.zone}/machineTypes/{args.machine_type}"
        ),
        "disks": [{
            "boot": True,
            "autoDelete": True,
            "initializeParams": {
                "sourceImage": image["selfLink"],
                "diskSizeGb": "10",
                "diskType": f"zones/{args.zone}/diskTypes/pd-standard",
            },
        }],
        "networkInterfaces": [{
            "network": f"projects/{args.project}/global/networks/default",
            "accessConfigs": [{
                "name": "External NAT",
                "type": "ONE_TO_ONE_NAT",
            }],
        }],
        "metadata": {
            "items": [
                {"key": key, "value": value}
                for key, value in metadata.items()
            ]
        },
    }

    print(f"Creating {args.vm1_name} using service account...", flush=True)
    operation = compute.instances().insert(
        project=args.project, zone=args.zone, body=config
    ).execute()
    wait_for_operation(compute, args.project, operation, args.zone)
    print("VM1 created. Its startup script will create VM2.")
    print(f"Check VM1 startup logs in zone {args.zone}.")


if __name__ == "__main__":
    main()
