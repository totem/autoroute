#!/usr/bin/python

import argparse
import json
import logging
import os
import sys
import time

import boto.ec2
import boto.ec2.autoscale
import boto.sqs

from boto.route53.connection import Route53Connection

from boto.sqs.message import RawMessage


UPDATE = ["autoscaling:EC2_INSTANCE_LAUNCH"]
SKIP = ["autoscaling:TEST_NOTIFICATION",
        "autoscaling:EC2_INSTANCE_LAUNCH_ERROR"]
REMOVE = ["autoscaling:EC2_INSTANCE_TERMINATE",
          "autoscaling:EC2_INSTANCE_TERMINATE_ERROR"]

LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(message)s'
LOG_DATE = '%Y-%m-%d %I:%M:%S %p'

logger = logging.getLogger('autoscale-dns')


class AutorouteError(Exception):
    pass


# check if the record is there
# if it isn't add the record
def add_record(id):
    # queue the route53 addition (may take time for ip address to get assigned)
    instance = ec2.get_only_instances([id])[0]

    if instance.public_dns_name is not None \
            and len(instance.public_dns_name) > 0:
        dns_name = instance.public_dns_name

        try:
            # get the tag data from the instance
            d = json.loads(instance.tags['dns'])

            name = "%s.%s" % (d['record'], d['zone'])
        except:
            raise AutorouteError("unable to get dns information")

        zone = r53.get_zone(d['zone'])
        records = zone.find_records(name, 'CNAME', all=True)

        # add DNS record
        # is this a list, or just one.
        if records is None:
            # straight up add
            logger.debug('no matching records, add')
            pass

        elif isinstance(records, list):
            for r in records:
                if r.identifier == id:
                    # is dns the same
                    if dns_name in r.resource_records:
                        logger.debug('found matching record, skip')
                        return

                    else:
                        # update or delete.
                        logger.debug('found matching record, update')
                        zone.update_record(r, dns_name, new_identifier=(id, 1))
                        return

        elif records.identifier == id:
            # is dns the same
            if dns_name in records.resource_records:
                logger.debug('found matching record, skip')
                return

            else:
                logger.debug('found matching record, update')
                zone.update_record(records, dns_name, new_identifier=(id, 1))
                return

        # this is a new record
        logger.debug(
            'adding record %s CNAME %s, (%s,1)' % (name, dns_name, id))
        zone.add_record(
            "CNAME", name, dns_name, ttl=60,
            identifier=(id, 1), comment='autoscaling group increased')

        return


def remove_record(id):
    instance = ec2.get_only_instances([id])[0]

    try:
        d = json.loads(instance.tags['dns'])

        name = "%s.%s" % (d['record'], d['zone'])
    except:
        raise AutorouteError("unable to get dns information")

    zone = r53.get_zone(d['zone'])
    records = zone.find_records(name, 'CNAME', all=True)

    if records is None:
        logger.debug("no records found for %s" % (name))
        return
    elif isinstance(records, list):
        for r in records:
            if r.identifier == id:
                logger.debug('deleting record %s, %s' % (name, id))
                zone.delete_record(r)
    elif records.identifier == id:
        logger.debug('deleting record %s, %s' % (name, id))
        zone.delete_record(records)


# todo: finish implementing this and have it run periodically
def sync_group():
    id = "i-f4bd6ea9"
    i = ec2.get_only_instances([id])[0]

    g = i.tags['aws:autoscaling:groupName']

    s = autoscale.get_all_groups(names=[g])[0]

    for ai in s.instances:
        #ai_id = ai.instance_id
        # get instance
        # get public dns
        # check r53
        pass


parser = argparse.ArgumentParser(description='do the dns')
parser.add_argument('--key', default=None)
parser.add_argument('--secret', default=None)
parser.add_argument('--region', default="us-west-1")
parser.add_argument('-q', '--queue', default="autoroute")
parser.add_argument('-l', '--level', default='info')

args = parser.parse_args()

logging.basicConfig(format=LOG_FORMAT,
                    datefmt=LOG_DATE,
                    level=args.level.upper())

# check for argument, env
key = args.key or os.environ.get('AWS_ACCESS_KEY_ID')
secret = args.secret or os.environ.get('AWS_SECRET_ACCESS_KEY')

logger.debug('attempting to connect to aws resources')

if key is not None:
    sqs = boto.sqs.connect_to_region(
        args.region, aws_access_key_id=key, aws_secret_access_key=secret)
    ec2 = boto.ec2.connect_to_region(
        args.region, aws_access_key_id=key, aws_secret_access_key=secret)
    autoscale = boto.ec2.autoscale.connect_to_region(
        args.region, aws_access_key_id=key, aws_secret_access_key=secret)
    r53 = Route53Connection(key, secret)
# fall back to instance role
else:
    sqs = boto.sqs.connect_to_region(args.region)
    ec2 = boto.ec2.connect_to_region(args.region)
    autoscale = boto.ec2.autoscale.connect_to_region(args.region)
    r53 = Route53Connection()


logger.debug('connceted to aws resources')

logger.info('hello')

# connect to SQS Queue
queue = sqs.get_queue(args.queue)

if queue is None:
    logger.error("unable to attach to queue '%s'" % (args.queue))
    sys.exit(1)

queue.set_message_class(RawMessage)


# on event
while True:
    try:
        message = queue.read(visibility_timeout=10, wait_time_seconds=20)
    except KeyboardInterrupt:
        logger.info('Goodbye')
        sys.exit(0)
    except Exception as e:
        logger.exception(e)
        logger.error('error reading from queue: %s' % (str(e)))
        message = None

    delete = False

    if message is not None:
        # in this case the data should be a json object, with an embedded
        # json message
        try:
            data = json.loads(message.get_body())
            details = json.loads(data['Message'])

            event = details["Event"]

            logger.debug('message about %s' % (event))

            # if launch, add (or queue) r53 update
            if event == "autoscaling:EC2_INSTANCE_LAUNCH":
                add_record(details["EC2InstanceId"])
                # if we get here (no exceptions), delete!
                delete = True

            elif event in SKIP:
                # we aren't going to do anything with this one.
                delete = True

            elif event in REMOVE:
                # we are going to attempt to remove the DNS record
                remove_record(details["EC2InstanceId"])
                # if we get here (no exceptions), delete!
                delete = True

            else:
                # whoops, whats this message here for
                delete = True

        except AutorouteError:
            # these failures shouldn't be retried later
            delete = True
        except Exception as e:
            # for now leave on queue and retry when they are visible
            logger.warn('error reading message: %s' % (str(e)))
            # delete = True

        if delete:
            queue.delete_message(message)
    else:
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            logger.info('Goodbye')
            sys.exit(0)
