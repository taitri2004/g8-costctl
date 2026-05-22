# sample_output/

These files are real outputs captured from the G8 AWS workshop account on
2026-05-22 in `us-west-2`.

Captured commands:

```bash
python costctl.py --region us-west-2 list ec2
python costctl.py --region us-west-2 list ec2 --missing-tag Application
python costctl.py --region us-west-2 cost --tag Application=FoodieDash --days 7
```

Current files:

- `list_ec2_2026-05-22.txt`
- `list_ec2_missing_app_2026-05-22.txt`
- `cost_FoodieDash_2026-05-22.txt`

The old `*_example.txt` template files were removed.
