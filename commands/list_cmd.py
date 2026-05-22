"""list — list AWS resources by type, filter by tag / missing-tag.

WHAT YOU MUST BUILD
-------------------
Support 4 resource types: ec2, rds, s3, volume.
Each takes:
- `want` — list of (key, value) tag pairs the resource MUST have
- `missing` — list of tag keys the resource MUST NOT have

Print a formatted table to stdout. Test cases are in tests/test_list.py.

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)            # "Owner=alice" -> ("Owner", "alice")
  tags_to_dict(items) -> dict       # boto3 [{"Key","Value"}] -> {k: v}
  tags_match(tags, want, missing) -> bool

AWS APIS YOU'LL NEED
--------------------
- EC2: ec2.describe_instances() with get_paginator
- RDS: rds.describe_db_instances(), then list_tags_for_resource(ResourceName=arn)
- S3:  s3.list_buckets(), then get_bucket_tagging(Bucket=name)
       (catch ClientError when bucket has no tagging config — treat as {})
- EBS: ec2.describe_volumes() with get_paginator

EXPECTED OUTPUT FORMAT (when run from CLI)
------------------------------------------
    EC2 Environment=dev — 1 found:
    ------------------------------------------------------------------------------
      i-0abc123def456789a       t3.micro       running       Environment=dev

VERIFY
------
    pytest tests/test_list.py -v
"""
import boto3
from botocore.exceptions import ClientError

from commands._common import parse_kv, tags_to_dict, tags_match


def _list_ec2(want, missing):
    """List EC2 instances matching tag filters.

    Args:
        want: list of (key, value) tag pairs that must all match
        missing: list of tag keys that must NOT be present

    Returns:
        list of (instance_id, instance_type, state, tags_dict) tuples
    """
    ec2 = boto3.client("ec2")
    rows = []

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                tags = tags_to_dict(instance.get("Tags"))
                if tags_match(tags, want, missing):
                    rows.append(
                        (
                            instance["InstanceId"],
                            instance.get("InstanceType", ""),
                            instance.get("State", {}).get("Name", ""),
                            tags,
                        )
                    )
    return rows


def _list_rds(want, missing):
    """Same shape as _list_ec2 but for RDS DB instances.

    Note: RDS tags require a separate API call per DB:
        rds.list_tags_for_resource(ResourceName=db['DBInstanceArn'])

    Returns:
        list of (db_id, db_class, db_status, tags_dict) tuples
    """
    rds = boto3.client("rds")
    rows = []

    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page.get("DBInstances", []):
            arn = db["DBInstanceArn"]
            tag_list = rds.list_tags_for_resource(ResourceName=arn).get("TagList", [])
            tags = tags_to_dict(tag_list)
            if tags_match(tags, want, missing):
                rows.append(
                    (
                        db["DBInstanceIdentifier"],
                        db.get("DBInstanceClass", ""),
                        db.get("DBInstanceStatus", ""),
                        tags,
                    )
                )
    return rows


def _list_s3(want, missing):
    """List S3 buckets matching tag filters.

    Note: get_bucket_tagging raises ClientError if no tagging config exists
    for that bucket. Treat that as an empty tags dict, not an error.

    Returns:
        list of (bucket_name, "bucket", "active", tags_dict) tuples
    """
    s3 = boto3.client("s3")
    rows = []

    for bucket in s3.list_buckets().get("Buckets", []):
        name = bucket["Name"]
        try:
            tag_set = s3.get_bucket_tagging(Bucket=name).get("TagSet", [])
        except ClientError:
            tag_set = []
        tags = tags_to_dict(tag_set)
        if tags_match(tags, want, missing):
            rows.append((name, "bucket", "active", tags))
    return rows


def _list_volume(want, missing):
    """List EBS volumes matching tag filters.

    Returns:
        list of (volume_id, "<type>-<size>GB", state, tags_dict) tuples
        e.g. ("vol-0abc", "gp2-100GB", "in-use", {"purpose": "practice"})
    """
    ec2 = boto3.client("ec2")
    rows = []

    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate():
        for volume in page.get("Volumes", []):
            tags = tags_to_dict(volume.get("Tags"))
            if tags_match(tags, want, missing):
                volume_type = volume.get("VolumeType", "")
                size = volume.get("Size", "")
                rows.append(
                    (
                        volume["VolumeId"],
                        f"{volume_type}-{size}GB",
                        volume.get("State", ""),
                        tags,
                    )
                )
    return rows


DISPATCH = {
    "ec2": _list_ec2,
    "rds": _list_rds,
    "s3": _list_s3,
    "volume": _list_volume,
}


def run(args):
    """Entry point called by costctl.py.

    Steps you should perform:
      1. Convert args.tag (list of "k=v" strings) → want pairs via parse_kv
      2. Use args.missing_tag (list of keys) as-is
      3. Call DISPATCH[args.type](want, missing) → rows
      4. Print a header line, separator, then one row per resource

    Args set by argparse:
        args.type         — one of "ec2", "rds", "s3", "volume"
        args.tag          — list[str], each "key=value"
        args.missing_tag  — list[str], each "key"
    """
    want = [parse_kv(item) for item in args.tag]
    missing = args.missing_tag
    rows = DISPATCH[args.type](want, missing)

    filters = []
    filters.extend(f"{k}={v}" for k, v in want)
    filters.extend(f"missing:{k}" for k in missing)
    filter_text = " ".join(filters) if filters else "all"

    print(f"{args.type.upper()} {filter_text} - {len(rows)} found:")
    print("-" * 78)
    for rid, kind, state, tags in rows:
        tag_text = ", ".join(f"{k}={v}" for k, v in sorted(tags.items()))
        print(f"  {rid:<28} {kind:<16} {state:<12} {tag_text}")
