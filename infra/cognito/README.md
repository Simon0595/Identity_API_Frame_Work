# Cognito default-group trigger (optional)

New Hosted UI sign-ups start with no group, so their tokens have no
`cognito:groups` claim and the API returns 401 (see `core/auth/cognito.py`).
This optional Lambda puts each confirmed sign-up in `public_caller`.

It lives outside the Django app on purpose. The API only reads group claims.
Delete this folder if you create users some other way.

## Files

- `post_confirmation.py`: handler (tested in `tests/test_post_confirmation.py`)
- `template.yaml`: AWS SAM function plus IAM (`AdminAddUserToGroup` on your pool)

## Deploy (AWS SAM)

```bash
cd infra/cognito
sam build
sam deploy --guided \
  --parameter-overrides UserPoolId=eu-west-1_XXXXXXXXX DefaultSignupGroup=public_caller
```

Note the `PostConfirmationFnArn` output.

## Attach to an existing pool

SAM grants invoke permission. Wire the trigger on the pool in the console or CLI:

- Console: Cognito, your pool, Extensions / Triggers, Post confirmation, pick
  the function.
- CLI: attach it as the `PostConfirmation` trigger. Fetch the pool first so you
  do not overwrite other `LambdaConfig` triggers:

  ```bash
  aws cognito-idp describe-user-pool --user-pool-id eu-west-1_XXXXXXXXX \
    --query 'UserPool.LambdaConfig'
  aws cognito-idp update-user-pool --user-pool-id eu-west-1_XXXXXXXXX \
    --lambda-config PostConfirmation=<PostConfirmationFnArn>
  ```

## Prerequisite

The default group must already exist in the pool. Create `public_caller`, plus
`subject`, `colleague`, and `admin`. The name must match a role the API maps
(see `ROLE_PRECEDENCE` in `core/auth/cognito.py`).

## Changing the default

Set `DefaultSignupGroup` at deploy time, or `DEFAULT_SIGNUP_GROUP` on the
function. Do not default self-signup to `admin`. `subject` only works once the
caller has a `Person` row whose `owner_sub` matches their `sub`.
