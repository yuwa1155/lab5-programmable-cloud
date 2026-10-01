# Lab 5 running notes

Setup:
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

The scripts default to us-west1-b and f1-micro.
VM creation failed with ZONE_RESOURCE_POOL_EXHAUSTED during testing,
so I tested with us-central1-a and e2-micro.

Run from the repository root:
    python part1/part1.py --project YOUR_PROJECT --zone us-central1-a --machine-type e2-micro
    python part2/part2.py --project YOUR_PROJECT --zone us-central1-a --machine-type e2-micro
    python part3/part3.py --project YOUR_PROJECT --zone us-central1-a --machine-type e2-micro

Part1 and Part2 use Application Default Credentials.
Part3 uses part3/service-credentials.json with Compute Admin and
Service Account User roles. The credential file is excluded from Git.

Part1 creates a VM, installs Flask through a startup script,
configures a systemd service, and allows TCP port 5000.

Part2 creates a boot disk snapshot, a custom image, and three VMs.
All three websites retained the original test post.
Creation times are recorded in part2/TIMING.md.

Part3 creates VM1 using service account credentials.
VM1 reads files from metadata and runs Python to create VM2.
VM2 installs Flask using the Part1 startup script.
Registration, login, and posting worked on VM2.

VM creation completes before Flask installation finishes.
Check startup logs if the website is not ready.
Use new VM names or remove previous test VMs before repeating
Part1 or Part3.
