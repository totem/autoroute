autoroute
=========

Autoroute is a service to process notifications from AWS Autoscaling groups to add Route53 weighted records.

## Running

The service can be run directly, or by using the provided upstart script. When run in EC2 it can use an Instance Role. The Access Key and Secret key can be passed in as arguments, or can be environment variables.

    autoroute.py -l debug -q autoroute

### Logs

The log output can be found at `/var/log/upstart/autoroute.log`.

## Deploying

To simplify and speed up deployment this project comes with the Instance Role, AMI build scripts, and Cloud Formation Template.

### Instance Role

Create an IAM role off of aws/roles.json.

### Building

This project uses [Packer](http://www.packer.io/) to build the AMI to be deployed. The base AMI is Ubuntu 13.04.

    packer build packer.json

### Cloud Formation Template

A script is included to replace the defaults in the Cloud Formation Template.

    aws/process-template.py -g default -g services -k default -r autoroute-role -o "-q my-autoroute" -a us-east-1,ami-xyz > customized-template.json
