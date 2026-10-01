#!/usr/bin/env python3
"""Create a VM and deploy the Flask tutorial application."""

import argparse
from pathlib import Path
import time

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def wait_for_operation(compute, project, operation, zone=None):
    """Wait for a zonal or global Compute Engine operation."""
    deadline = time.monotonic() + 600

    while time.monotonic() < deadline:
        if zone:
            result = compute.zoneOperations().get(
                project=project, zone=zone,
                operation=operation["name"]
            ).execute()
        else:
            result = compute.globalOperations().get(
                project=project,
                operation=operation["name"]
            ).execute()

        if result["status"] == "DONE":
            if "error" in result:
                raise RuntimeError(result["error"])
            return result

        time.sleep(2)

    raise TimeoutError(f'Operation timed out: {operation["name"]}')


def ensure_firewall(compute, project):
    try:
        compute.firewalls().get(
            project=project, firewall="allow-5000"
        ).execute()
        print("Firewall allow-5000 already exists.")
        return
    except HttpError as error:
        if error.resp.status != 404:
            raise

    rule = {
        "name": "allow-5000",
        "network": f"projects/{project}/global/networks/default",
        "direction": "INGRESS",
        "sourceRanges": ["0.0.0.0/0"],
        "targetTags": ["allow-5000"],
        "allowed": [{"IPProtocol": "tcp", "ports": ["5000"]}],
    }
    operation = compute.firewalls().insert(
        project=project, body=rule
    ).execute()
    wait_for_operation(compute, project, operation)
    print("Created firewall allow-5000.")


def create_instance(compute, project, zone, name, startup_script, machine_type="f1-micro"):
    image = compute.images().getFromFamily(
        project="ubuntu-os-cloud", family="ubuntu-2204-lts"
    ).execute()

    config = {
        "name": name,
        "machineType": f"zones/{zone}/machineTypes/{machine_type}",
        "disks": [{
            "boot": True,
            "autoDelete": True,
            "initializeParams": {
                "sourceImage": image["selfLink"],
                "diskSizeGb": "10",
                "diskType": f"zones/{zone}/diskTypes/pd-standard",
            },
        }],
        "networkInterfaces": [{
            "network": f"projects/{project}/global/networks/default",
            "accessConfigs": [{
                "name": "External NAT",
                "type": "ONE_TO_ONE_NAT",
            }],
        }],
        "metadata": {
            "items": [{
                "key": "startup-script",
                "value": startup_script,
            }],
        },
    }

    print(f"Creating {name} in {zone}...")
    operation = compute.instances().insert(
        project=project, zone=zone, body=config
    ).execute()
    wait_for_operation(compute, project, operation, zone)

    instance = compute.instances().get(
        project=project, zone=zone, instance=name
    ).execute()

    tags = instance.get("tags", {})
    tag_items = list(tags.get("items", []))
    if "allow-5000" not in tag_items:
        tag_items.append("allow-5000")

    operation = compute.instances().setTags(
        project=project, zone=zone, instance=name,
        body={
            "items": tag_items,
            "fingerprint": tags["fingerprint"],
        },
    ).execute()
    wait_for_operation(compute, project, operation, zone)

    instance = compute.instances().get(
        project=project, zone=zone, instance=name
    ).execute()
    return instance


def main():
    credentials, default_project = google.auth.default()
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=default_project)
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--name", default="lab5-part1")
    parser.add_argument("--machine-type", default="f1-micro")
    args = parser.parse_args()

    if not args.project:
        parser.error("Provide --project with your Google Cloud project ID.")

    compute = build("compute", "v1", credentials=credentials)
    startup_script = Path(__file__).with_name(
        "startup-script.sh"
    ).read_text()

    ensure_firewall(compute, args.project)
    instance = create_instance(
        compute, args.project, args.zone, args.name, startup_script, args.machine_type
    )

    ip = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
    print(f"\nVM created. Flask URL: http://{ip}:5000")
    print("The startup script may need several minutes to install Flask.")


if __name__ == "__main__":
    main()
