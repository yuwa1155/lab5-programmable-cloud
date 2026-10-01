import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from part1 import create_instance, ensure_firewall


def main():
    directory = Path(__file__).resolve().parent
    config = json.loads((directory / "config.json").read_text())
    credentials = service_account.Credentials.from_service_account_file(
        str(directory / "service-credentials.json"),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    compute = build("compute", "v1", credentials=credentials)
    project = config["project"]
    zone = config["zone"]
    name = config["vm2_name"]

    ensure_firewall(compute, project)
    try:
        instance = compute.instances().get(
            project=project, zone=zone, instance=name
        ).execute()
        print(f"{name} already exists.")
    except HttpError as error:
        if error.resp.status != 404:
            raise
        instance = create_instance(
            compute,
            project,
            zone,
            name,
            (directory / "vm2-startup-script.sh").read_text(),
            config["machine_type"],
        )

    ip = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
    url = f"http://{ip}:5000"
    (directory / "vm2-url.txt").write_text(url + "\n")
    print(f"VM2 Flask URL: {url}", flush=True)


if __name__ == "__main__":
    main()
