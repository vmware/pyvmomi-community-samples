"""
Written by Michael Rice <michael@michaelrice.org>
Github: https://github.com/michaelrice
Website: https://michaelrice.github.io/
Blog: http://www.errr-online.com/
This code has been released under the terms of the Apache 2.0 licenses
http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import print_function

import logging
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import tostring

import requests


def reset_alarm(**kwargs):
    """
    Resets an alarm on a given HostSystem in a vCenter to the green state
    without someone having to log in to do it manually.

    This is done by using an unexposed API call. This requires us
    to manually construct the SOAP envelope. We use the session key
    that pyvmomi provides during its connection.

    More information can be found about this process
    in this article written by William Lam:
    http://www.virtuallyghetto.com/2010/10/how-to-ack-reset-vcenter-alarm.html

    I adopted his process from perl to groovy:
    https://gist.github.com/michaelrice/d54a237295e017b032a5
    and from groovy now to python.

    Usage:
    SI = SmartConnect(xxx)
    HOST = SI.content.searchIndex.FindByxxx(xxx)
    alarm.reset_alarm(entity_moref=HOST._moId, entity_type='HostSystem',
                      alarm_moref='alarm-1', service_instance=SI)
    :param service_instance:
    :param entity_moref:
    :param alarm:
    :return boolean:
    """
    service_instance = kwargs.get("service_instance")
    payload = _build_payload(**kwargs)
    logging.debug(payload)
    session = service_instance._stub
    if not _send_request(payload, session):
        return False
    return True


def _build_payload(**kwargs):
    """
    Builds a SOAP envelope to send to the vCenter hidden API

    :param entity_moref:
    :param alarm_moref:
    :param entity_type:
    :return:
    """
    entity_moref = kwargs.get("entity_moref")
    entity_type = kwargs.get("entity_type")
    alarm_moref = kwargs.get("alarm_moref")
    if not entity_moref or not entity_type or not alarm_moref:
        raise ValueError("entity_moref, entity_type, and alarm_moref "
                         "must be set")

    attribs = {
        'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xmlns:soap': 'http://schemas.xmlsoap.org/soap/envelope/'
    }
    root = Element('soap:Envelope', attribs)
    body = SubElement(root, 'soap:Body')
    alarm_status = SubElement(body, 'SetAlarmStatus', {'xmlns': 'urn:vim25'})
    this = SubElement(alarm_status, '_this', {
        'xsi:type': 'ManagedObjectReference',
        'type': 'AlarmManager'
    })
    this.text = 'AlarmManager'
    alarm = SubElement(alarm_status, 'alarm', {'type': 'Alarm'})
    alarm.text = alarm_moref
    entity = SubElement(alarm_status, 'entity', {
        'xsi:type': 'ManagedObjectReference',
        'type': entity_type
    })
    entity.text = entity_moref
    status = SubElement(alarm_status, 'status')
    status.text = 'green'
    # I hate hard coding this but I have no idea how to do it any other way
    # pull requests welcome :)
    return '<?xml version="1.0" encoding="UTF-8"?>{0}'.format(tostring(root))


def _send_request(payload=None, session=None):
    """
    Using requests we send a SOAP envelope directly to the
    vCenter API to reset an alarm to the green state.

    :param payload:
    :param session:
    :return:
    """
    stub = session
    host_port = stub.host
    # Ive seen some code in pyvmomi where it seems like we check for http vs
    # https but since the default is https do people really run it on http?
    url = 'https://{0}/sdk'.format(host_port)
    logging.debug("Sending {0} to {1}".format(payload, url))
    # I opted to ignore invalid ssl here because that happens in pyvmomi.
    # Once pyvmomi validates ssl it wont take much to make it happen here.
    res = requests.post(url=url, data=payload, headers={
        'Cookie': stub.cookie,
        'SOAPAction': 'urn:vim25',
        'Content-Type': 'application/xml'
    }, verify=False)
    if res.status_code != 200:
        logging.debug("Failed to reset alarm. HTTP Status: {0}".format(
            res.status_code))
        return False
    return True


def print_triggered_alarms(entity=None):
    """
    This is a useful method if you need to print out the alarm morefs

    :param entity:
    """
    alarms = entity.triggeredAlarmState
    for alarm in alarms:
        print("#"*40)
        # The alarm key looks like alarm-101.host-95
        print("alarm_moref: {0}".format(alarm.key.split('.')[0]))
        print("alarm status: {0}".format(alarm.overallStatus))


def get_alarm_refs(entity=None):
    """
    Useful method that will return a list of dict with the moref and alarm
    status for all triggered alarms on a given entity.


    :param entity:
    :return list: [{'alarm':'alarm-101', 'status':'red'}]
    """
    alarm_states = entity.triggeredAlarmState
    ret = []
    for alarm_state in alarm_states:
        tdict = {
            "alarm": alarm_state.key.split('.')[0],
            "status": alarm_state.overallStatus
        }
        ret.append(tdict)
    return ret
