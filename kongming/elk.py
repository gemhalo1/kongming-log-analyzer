import httpx
import json
from tqdm import tqdm
from typing import List, Union, Dict, Any
from .constants import CLEAN_CONTEXT_MAGIC_STRING

null = None
true = True
false = False

def tensor(x):
    return x

def AnswerItem(**kwargs):
    return kwargs

def QuestionItem(**kwargs):
    return kwargs

def MultiModalConversationResponse(**kwargs):
    return kwargs

def MultiModalConversationOutput(**kwargs):
    return kwargs

def MultiModalConversationUsage(**kwargs):
    return kwargs

def Choice(**kwargs):
    return kwargs

def ObjectId(x):
    return x

def Message(x):
    return x


class NlpRequest(object):
    def __init__(self, record):
        self.record = record

    @property
    def location(self):
        return self.record['central-nlp-request']['metadata']['longitude'], self.record['central-nlp-request']['metadata']['latitude']
    
    @property
    def account_id(self):
        return self.record['central-nlp-request']['metadata']['accountId']

    @property
    def xj_account_id(self):
        return self.record['central-nlp-request']['metadata']['xjAccountId']

    @property
    def files(self):
        files = self.record['central-nlp-request'].get('files')
        if isinstance(files, list):
            return [file['ossUrl'] for file in files if 'ossUrl' in file]
        return None

    @property
    def device_id(self):
        return self.record['central-nlp-request']['metadata']['deviceId']

    @property
    def glass_device_id(self):
        return self.record['central-nlp-request']['metadata']['glassDeviceId']

    @property
    def iot_device_id(self):
        return self.record['central-nlp-request']['metadata']['iotDeviceId']

    @property
    def glass_product(self):
        return self.record['central-nlp-request']['metadata']['glassProduct']

    @property
    def function_type(self):
        return self.record['central-nlp-request']['metadata']['functionType']

    @property
    def origin_type(self):
        return self.record['central-nlp-request']['metadata']['originType']

    @property
    def session_id(self):
        return self.record['central-nlp-request']['metadata']['sessionId']

    @property
    def trace_id(self):
        return self.record['central-nlp-request']['metadata']['terminalTraceId']

    @property
    def time_zone(self):
        return self.record['central-nlp-request']['metadata']['timeZone']

    @property
    def query(self):
        q = self.record['central-nlp-request']['payload']['q']
        return q if q != CLEAN_CONTEXT_MAGIC_STRING else '<清除上下文>'


    @property
    def timestamp(self):
        return self.record['ltime']

class KongmingELKServer(object):
    DEFAUL_EXCLUDE_FIELDS = ["messageobj","log","level","fields","input","lblpl","lmt","class"]

    def __init__(self, server="https://elk.xjsdtech.com", 
                 username="ai", 
                 password="ai@123456", 
                 env:str="uat",
                 exclude_fields:Union[List[str],None]=None):
        self.server=server
        self.auth = (username, password)
        self.exclude_fields = exclude_fields or KongmingELKServer.DEFAUL_EXCLUDE_FIELDS

        self.url = f'{self.server}/s/ai/api/console/proxy?path={env}-kongming-%2A%2F_search&method=GET'

        self.headers = {
            'Content-Type': 'application/json',
            'kbn-xsrf': 'kibana'
        }

    def _run_query(self, 
                   request_body:Dict[str, Any], 
                   size:int,
                   pagesize:int,
                   out_file:Union[str,None]=None):
        response = httpx.post(self.url, auth=self.auth, headers=self.headers, json=request_body)
        records = []

        if response.status_code == 200:
            res_json = response.json()

            if out_file:
                with open(out_file, mode='w', encoding='utf-8') as f_orig:
                    json.dump(res_json, f_orig, ensure_ascii=False, indent=2)

            hits_total = res_json['hits']['total']['value']
            records = res_json['hits']['hits']

            if min(size, hits_total) > pagesize:
                for offset in tqdm(range(pagesize, min(size, hits_total), pagesize)):
                    request_body['from'] = offset
                    request_body['size'] = pagesize
                    response = httpx.post(self.url, auth=self.auth, headers=self.headers, json=request_body)
                    res_json = response.json()
                    records += res_json['hits']['hits']
        return records

    def query_nlp_request(self, 
                        timestamp_begin:Union[str,None]=None,
                        timestamp_end:Union[str,None]=None,
                        size:int=10000,
                        pagesize:int=10,
                        out_file:Union[str,None]=None):
        """ 查询所有central-manager收到的nlp请求，通过检查"central-nlp-request"字段是否存在来判断
        """

        must_clause = [
                        {
                            "exists": {
                                "field": "central-nlp-request"
                            }
                        },
                    ]

        if timestamp_begin:
            if  timestamp_end:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "gte": timestamp_begin,
                            "lt":  timestamp_end,
                        }
                    }
                })
            else:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "gte": timestamp_begin,
                        }
                    }
                })
        elif timestamp_end:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "lt":  timestamp_end,
                        }
                    }
                })

        request_body = {
            "query": {
                "bool": {
                    "must": must_clause,
                }
            },
            "from": 0,
            "size": pagesize,
            "sort": [
                { "@timestamp": "asc" }
            ],
            "_source": {
                "excludes": self.exclude_fields
            }
        }

        records = self._run_query(request_body=request_body, size=size, pagesize=pagesize, out_file=out_file)

        nlp_requests = [NlpRequest(r['_source']) for r in records]

        return records, nlp_requests
    def query_by_phrase(self, 
                        match_phrase:str,
                        match_fields:List[str]=["*"],
                        terms:Union[Dict[str,Any],None]=None,
                        timestamp_begin:Union[str,None]=None,
                        timestamp_end:Union[str,None]=None,
                        size:int=10000,
                        pagesize:int=10,
                        out_file:Union[str,None]=None):
        must_clause = [
                        {
                            "multi_match": {
                                "query": f"{match_phrase}",
                                "type": "phrase",
                                "fields": match_fields
                            }
                        }
                    ]

        must_not_clause = None

        if timestamp_begin:
            if  timestamp_end:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "gte": timestamp_begin,
                            "lt":  "timestamp_end",
                        }
                    }
                })
            else:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "gte": timestamp_begin,
                        }
                    }
                })
        elif timestamp_end:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "lt":  "timestamp_end",
                        }
                    }
                })

        # must_not_clause = [
        #   {
        #     "multi_match": {
        #                 "query": "llm_recommend",
        #                 "type": "phrase",
        #                 "fields": [
        #                     "*"
        #                 ]
        #             }
        #   },
        #   {
        #       "match_phrase": {
        #           "message": "\"type\":\"tts\""
        #       }
        #   },
        #   {
        #       "match_phrase": {
        #           "message": "\"type\":\"summary\""
        #       }
        #   },
        #   {
        #       "match_phrase": {
        #           "message": "\"type\":\"todos\""
        #       }
        #   },
        #   {
        #       "match_phrase": {
        #           "message": "\"type\":\"asr\""
        #       }
        #   },
        #   {
        #       "match_phrase": {
        #           "message": "summary request:"
        #       }
        #   },
        #   {
        #       "match_phrase": {
        #           "message": "收到数据"
        #       }
        #   }
        # ]


        if terms:
            for term in terms:
                must_clause.append({
                    "term": {
                        term: terms[term]
                    }
                })

        request_body = {
            "query": {
                "bool": {
                    "must": must_clause,
                    "must_not": must_not_clause
                }
            },
            "from": 0,
            "size": pagesize,
            "sort": [
                { "@timestamp": "asc" }
            ],
            "_source": {
                "excludes": self.exclude_fields
            }
        }

        return self._run_query(request_body=request_body, size=size, pagesize=pagesize, out_file=out_file)

    def query_by_trace_id(self, trace_id:str, env:str="uat", size:int=10000, pagesize:int=10, out_file:Union[str,None]=None):
        return self.query_by_phrase(trace_id, env=env, size=size, pagesize=pagesize, out_file=out_file)
