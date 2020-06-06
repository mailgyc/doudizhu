from __future__ import annotations

import time
from typing import Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import Element


class Msg(object):

    @staticmethod
    def parse_xml(data: str) -> Optional[Msg]:
        if len(data) == 0:
            return None
        xml = ElementTree.fromstring(data)
        msg_type = xml.find('MsgType').text

        factory = {'text': TextMsg, 'image': ImageMsg}
        return factory.get(msg_type).from_xml(xml)

    def __init__(self, *args, **kwargs):
        self.ToUserName = None
        self.FromUserName = None
        self.CreateTime = None
        self.MsgType = None
        self.MsgId = None

    def from_xml(self, xml: Element):
        self.ToUserName = xml.find('ToUserName').text
        self.FromUserName = xml.find('FromUserName').text
        self.CreateTime = xml.find('CreateTime').text
        self.MsgType = xml.find('MsgType').text
        self.MsgId = xml.find('MsgId').text
        return self

    def to_xml(self, *args, **kwargs):
        pass

    @property
    def timestamp(self):
        return int(time.time())


class TextMsg(Msg):

    def __init__(self):
        super().__init__()
        self.Content = None

    def from_xml(self, xml: Element):
        super().from_xml(xml)
        self.Content = xml.find('Content').text.encode("utf-8")
        return self

    def to_xml(self, content):
        return f"""<xml>
            <ToUserName><![CDATA[{self.FromUserName}]]></ToUserName>
            <FromUserName><![CDATA[{self.ToUserName}]]></FromUserName>
            <CreateTime>{self.timestamp}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
        </xml>"""


class ImageMsg(Msg):
    def __init__(self):
        super().__init__()
        self.PicUrl = None
        self.MediaId = None

    def from_xml(self, xml: Element):
        self.PicUrl = xml.find('PicUrl').text
        self.MediaId = xml.find('MediaId').text
        return self

    def to_xml(self, media):
        return f"""<xml>
            <ToUserName><![CDATA[{self.FromUserName}]]></ToUserName>
            <FromUserName><![CDATA[{self.ToUserName}]]></FromUserName>
            <CreateTime>{self.timestamp}</CreateTime>
            <MsgType><![CDATA[image]]></MsgType>
            <Image>
            <MediaId><![CDATA[{media}]]></MediaId>
            </Image>
        </xml>"""
