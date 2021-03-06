#!/bin/bash -x

# source config
ami_id=ami-5189a661 #Ubuntu Server 14.04 LTS (HVM)

autoscale_group=xd-as-group
launch_config=xd-launch-config
zone=${EC2_REGION}a
AUTH="--access-key-id ${AWS_ACCESS_KEY} --secret-key ${AWS_SECRET_KEY}"

aws iam create-instance-profile --instance-profile-name xd-scraper
aws iam add-role-to-instance-profile --instance-profile-name xd-scraper --role-name xd-scraper

# from https://alestic.com/2011/11/ec2-schedule-instance/

as-create-launch-config \
    ${launch_config} \
    ${AUTH} \
  --iam-instance-profile xd-scraper \
  --key $KEY \
  --instance-type t2.small \
  --user-data-file src/aws/userdata-bootstrap.sh \
  --image-id $ami_id

as-create-auto-scaling-group \
    ${AUTH} \
  --auto-scaling-group "$autoscale_group" \
  --launch-configuration "$launch_config" \
  --availability-zones "$zone" \
  --min-size 0 \
  --max-size 0

as-suspend-processes \
    ${AUTH} \
  --auto-scaling-group "$autoscale_group" \
  --processes ReplaceUnhealthy

# UTC at 1am (5pm PST)
as-put-scheduled-update-group-action \
    ${AUTH} \
  --name "xd-schedule-start" \
  --auto-scaling-group "$autoscale_group" \
  --min-size 1 \
  --max-size 1 \
  --recurrence "0 01 * * *"

as-put-scheduled-update-group-action \
    ${AUTH} \
  --name "xd-schedule-stop" \
  --auto-scaling-group "$autoscale_group" \
  --min-size 0 \
  --max-size 0 \
  --recurrence "55 01 * * *"

# launch now if any script parameters
if [ -n "$1" ] ; then
    #  created via IAM console: role/xd-scraper
    ec2-run-instances \
      --group ssh-only \
      --key $KEY \
      --instance-type t2.small \
      --instance-initiated-shutdown-behavior terminate \
      --iam-profile xd-scraper \
      --user-data-file src/aws/userdata-bootstrap.sh \
      $ami_id
fi
