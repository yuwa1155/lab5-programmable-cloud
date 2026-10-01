import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Reuse our Part 1 helpers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "part1"))
from part1 import ensure_firewall, wait_for_operation


def get_or_none(request):
    try:
        return request.execute()
    except HttpError as error:
        if error.resp.status != 404:
            raise
        return None


def main():
    credentials, default_project = google.auth.default()
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=default_project)
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--source", default="lab5-part1")
    parser.add_argument("--machine-type", default="f1-micro")
    args = parser.parse_args()
    if not args.project:
        parser.error("Provide --project.")

    compute = build("compute", "v1", credentials=credentials)
    project, zone = args.project, args.zone
    source = compute.instances().get(
        project=project, zone=zone, instance=args.source
    ).execute()
    boot_disk = next(disk for disk in source["disks"] if disk["boot"])
    disk_name = boot_disk["source"].rsplit("/", 1)[-1]
    snapshot_name = f"base-snapshot-{args.source}"
    image_name = f"base-image-{args.source}"

    snapshot = get_or_none(compute.snapshots().get(
        project=project, snapshot=snapshot_name
    ))
    if snapshot is None:
        print(f"Creating snapshot of boot disk {disk_name}...", flush=True)
        operation = compute.disks().createSnapshot(
            project=project, zone=zone, disk=disk_name,
            body={"name": snapshot_name}
        ).execute()
        wait_for_operation(compute, project, operation, zone)
        snapshot = compute.snapshots().get(
            project=project, snapshot=snapshot_name
        ).execute()
    if snapshot["status"] != "READY":
        raise RuntimeError(f"Snapshot is not ready: {snapshot['status']}")

    image = get_or_none(compute.images().get(
        project=project, image=image_name
    ))
    if image is None:
        print(f"Creating image {image_name}...", flush=True)
        operation = compute.images().insert(
            project=project,
            body={
                "name": image_name,
                "sourceSnapshot": snapshot["selfLink"]
            }
        ).execute()
        wait_for_operation(compute, project, operation)
        image = compute.images().get(
            project=project, image=image_name
        ).execute()
    if image["status"] != "READY":
        raise RuntimeError(f"Image is not ready: {image['status']}")

    ensure_firewall(compute, project)
    timing_path = Path(__file__).with_name("TIMING.md")
    if not timing_path.exists():
        timing_path.write_text(
            "# Part 2 provisioning times\n\n"
            "Measured from the insert request until its operation is DONE.\n"
            "Flask readiness is checked separately.\n"
        )

    for number in range(1, 4):
        name = f"lab5-part2-{number}"
        existing = get_or_none(compute.instances().get(
            project=project, zone=zone, instance=name
        ))
        if existing is not None:
            print(f"{name} already exists; skipping.", flush=True)
            continue

        config = {
            "name": name,
            "machineType": f"zones/{zone}/machineTypes/{args.machine_type}",
            "disks": [{
                "boot": True,
                "autoDelete": True,
                "initializeParams": {
                    "sourceImage": image["selfLink"],
                    "diskType": f"zones/{zone}/diskTypes/pd-standard"
                }
            }],
            "networkInterfaces": [{
                "network": f"projects/{project}/global/networks/default",
                "accessConfigs": [{
                    "name": "External NAT",
                    "type": "ONE_TO_ONE_NAT"
                }]
            }],
            "tags": {"items": ["allow-5000"]}
        }
        # Flask and its enabled systemd service are already on the disk.
        print(f"Creating {name}...", flush=True)
        started = time.perf_counter()
        operation = compute.instances().insert(
            project=project, zone=zone, body=config
        ).execute()
        wait_for_operation(compute, project, operation, zone)
        elapsed = time.perf_counter() - started

        instance = compute.instances().get(
            project=project, zone=zone, instance=name
        ).execute()
        ip = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
        url = f"http://{ip}:5000"
        print(f"{name}: {elapsed:.2f} seconds — {url}", flush=True)

        with timing_path.open("a") as report:
            report.write(
                f"\n- {name}: {elapsed:.2f} seconds\n"
                f"  - UTC: {datetime.now(timezone.utc).isoformat()}\n"
                f"  - Zone: {zone}; machine type: {args.machine_type}\n"
                f"  - Snapshot: {snapshot_name}; image: {image_name}\n"
                f"  - URL: {url}\n"
            )

    print(f"Timing results saved to {timing_path}")


if __name__ == "__main__":
    main()
