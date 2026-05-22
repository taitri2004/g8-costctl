# Reflections

## Multi-account

To run `costctl` against 100 AWS accounts, I would add a profile/account loop and assume a cross-account role in each target account. The output should include the account id and account alias on every row, and commands like `list` and `cost` should support exporting CSV/JSON so results can be aggregated safely.

## `clean --apply` blast radius

If `clean --tag Environment=dev --apply` was accidentally run in a shared account, I would want guardrails before the command can delete anything: an allow-list of approved tag keys, a required ownership tag such as `Owner` or `Application`, a maximum deletion count, and a confirmation summary that shows exact resource ids. For production use I would also require IAM permissions scoped to practice resources only.

## W7 carry-over

I would keep `list`, `cost`, and `tag` for W7 because they are useful in multi-account operations and have low destructive risk. I would keep `terminate` and `clean` only with stronger safety controls, audit logging, and role-based permissions because those commands can cause real outages or data loss.
