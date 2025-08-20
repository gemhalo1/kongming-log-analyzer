from pydantic import BaseModel
from typing import Literal, Union, List, Optional, Dict

ID_TYPE = Literal['deviceId', 'glassDeviceId', 'iotDeviceId', 'xjAccountId', 'accountId']
# GLASS_PRODUCT = Literal['', '1001', '1002', '1003', '1004', '1005']

DeviceCodeMap = {
    '1001': 'Concept',
    '1002': 'Star',
    '1003': 'Air',
    '1004': 'AirPro',
    '1005': 'Normandy',

    '1200': '指环一代',
    '1201': '指环国内二代',
    '1202': '指环国外二代',
    '1203': '指环美版二代',

    '5001': '海外Air',
    '5002': '海外AirPro',
    '5003': '海外Normandy',
}

class DialogLogFilter(BaseModel):
    timestamp_begin: Optional[str] = None
    timestamp_end: Optional[str] = None
    glass_product: Optional[str] = None
    id_type: Optional[ID_TYPE] = None
    id_value: Optional[str] = None
    phrase: Optional[str] = None

class Location(BaseModel):
    longitude: float
    latitude: float

    def __str__(self):
        return f'{self.longitude:.5f}, {self.latitude:.5f}'

class OssFile(BaseModel):
    ossUrl: Optional[str] = None
    resourceName: Optional[str] = None
    resourceOssName: Optional[str] = None
    resourceSize: Optional[str] = None
    resourceType: Optional[str] = None

class NLPIntent(BaseModel):
    namespace: str
    name: str

    def __str__(self):
        return self.namespace + '::'+ self.name

class NLPError(BaseModel):
    code: Optional[int] = None
    errorMsg: Optional[str] = None

    def __str__(self):
        return f'[{self.code or "?"}] - {self.errorMsg or ""}'

class NLPUtterance(BaseModel):
    id: str = ''
    screen: str = ''
    speech: str = ''

    def __str__(self):
        s = []
        if self.id:
            s.append(f'[{self.id}]')
        if self.speech is not None:
            s.append(self.speech)
        elif self.screen is not None:
            s.append(self.screen)

        return ' '.join(s)

class NLPRound(BaseModel):
    request_timestamp: Optional[str] = None
    response_timestamp: Optional[str] = None

    query: Optional[str] = None

    # from response message
    isNextRecorded: Optional[bool] = None
    isSoundOpened: Optional[bool] = None
    intent: Optional[NLPIntent] = None  # from "header" field
    utterance: Optional[NLPUtterance] = None
    error: Optional[NLPError] = None

    @staticmethod
    def from_records(nlp_request: Dict, nlp_response: Dict):
        round = NLPRound()

        if nlp_request:
            round.request_timestamp = nlp_request['_source']['@timestamp']
            msg = nlp_request['_source']['central-nlp-request']
            round.query = msg['payload']['q']

        if nlp_response:
            round.response_timestamp = nlp_response['_source']['@timestamp']
            msg = nlp_response['_source']['central-nlp-response']
            payload = msg['payload']
            round.intent = NLPIntent(**payload['header'])
            round.isNextRecorded = payload['payload'].get('isNextRecorded')
            round.isSoundOpened = payload['payload'].get('isSoundOpened')

            if 'utterance' in payload['payload']:
                round.utterance = NLPUtterance(**payload['payload']['utterance'])
            elif 'code' in payload['payload'] and 'errorMsg' in payload['payload']:
                round.error = NLPError(**payload['payload'])

        return round
        return round

class LLMRound(BaseModel):
    request_timestamp: Optional[str] = None
    response_timestamp: Optional[str] = None

    channel_type: Optional[int] = None
    clean_context: Optional[int] = None

    intent_name: Optional[str] = None
    files: Optional[List[OssFile]] = None

    # originType: Optional[int] = None
    play_status: Optional[int] = None
    use_deepseek: Optional[int] = None
    use_search: Optional[int] = None
    visual_aids_status: Optional[int] = None

    query: Optional[str] = None
    raw_qery: Optional[str] = None

    # from response message
    answer: Optional[str] = None
    base_status: Optional[int] = None  # base_status of answer
    reason: Optional[str] = None       # 思考过程
    reasoning_latency: Optional[int] = None
    thoughts_data: Optional[List[Dict[str,str]]] = None  # 深度搜索的数据

    @staticmethod
    def from_records(llm_request, llm_response):
        if llm_request is None:
            return None

        round = LLMRound()

        msg = llm_request['_source']['central-answer-request']
        
        round.request_timestamp = llm_request['_source']['@timestamp']
        round.channel_type = msg.get('channel_type')
        round.clean_context = msg.get('clean_context')
        round.intent_name = msg.get('intent_name')
        if msg.get('files'):
            round.files = [OssFile(**x) for x in msg.get('files')]
        # round.originType = msg.get('originType')
        round.play_status = msg.get('play_status')
        round.use_deepseek = msg.get('use_deepseek')
        round.use_search = msg.get('use_search')
        round.visual_aids_status = msg.get('visual_aids_status')

        round.query = msg.get('query')
        round.raw_qery = msg.get('raw_query')

        if llm_response:
            round.response_timestamp = llm_response['_source']['@timestamp']

            payload = llm_response['_source']['central-answer-response']['payload']
            round.answer = payload.get('answer')
            round.base_status = payload.get('base_status')
            round.thoughts_data = payload.get('thoughts_data')

            reason = payload.get('reason')
            if isinstance(reason, dict):
                round.reasoning_latency = reason.get('reasoning_latency')
                round.reason = reason.get('answer')

        return round

class DialogRound(BaseModel):
    timestamp: str
    traceId: str

    location: Optional[Location] = None

    # glass type code, 
    glassProduct: Optional[str] = None

    # various ids, could be: '', '1001', '1002', '1003', '1004', '1005'
    accountId: Optional[str]= None
    xjAccountId: Optional[str]= None
    deviceId: Optional[str]= None
    glassDeviceId: Optional[str]= None
    iotDeviceId: Optional[str]= None

    sessionId: Optional[str]= None
    msgId: Optional[str]= None

    # 请求发起端：0:眼镜  1:手机
    originType: Optional[int]= None

    #　请求类型：0:语音 2:文本
    functionType: Optional[int]= None

    sessionFirstFlag: Optional[bool] = None

    local:Optional[str]= None   # 怀疑是locale的笔误
    timeZone: Optional[str]= None
    nluLanguage: Optional[str]= None

    nlp_round: Optional[NLPRound] = None
    llm_round: Optional[LLMRound] = None

    @staticmethod
    def from_records(nlp_request, nlp_response, llm_request, llm_response):
        if nlp_request is None:
            return None

        nlp_request_msg = nlp_request['_source']['central-nlp-request']
        metadata = nlp_request_msg.get('metadata')

        if not metadata:
            return None

        round = DialogRound(timestamp=nlp_request['_source']['@timestamp'], traceId = nlp_request['_source']['traceId'])

        if metadata:
            round.location = Location(longitude=metadata.get('longitude', 0), latitude=metadata.get('latitude', 0))
            round.glassProduct = metadata.get('glassProduct')
            round.accountId = metadata.get('accountId')
            round.xjAccountId = metadata.get('xjAccountId')
            round.deviceId = metadata.get('deviceId')
            round.glassDeviceId = metadata.get('glassDeviceId')
            round.iotDeviceId = metadata.get('iotDeviceId')
            round.sessionId = metadata.get('sessionId')
            round.msgId = metadata.get('msgId')
            round.originType = metadata.get('originType')
            round.functionType = metadata.get('functionType')
            round.local = metadata.get('local')
            round.timeZone = metadata.get('timeZone')
            round.nluLanguage = metadata.get('nluLanguage')
            round.sessionFirstFlag = metadata.get('sessionFirstFlag')


        round.nlp_round = NLPRound.from_records(nlp_request, nlp_response)
        round.llm_round = LLMRound.from_records(llm_request, llm_response)

        return round