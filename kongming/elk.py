import httpx
import json
from tqdm import tqdm
from typing import List, Union, Dict, Any, Optional, Tuple, Any, Literal
from .constants import CLEAN_CONTEXT_MAGIC_STRING
from .model import DialogLogFilter, DialogRound, Location, NLPRound, LLMRound, NLPIntent, NLPUtterance, OssFile


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


KongmingEnvironmentType = Literal['uat', 'prod', 'fat']

class KongmingELKServer(object):
    DEFAUL_EXCLUDE_FIELDS = ["messageobj","log","level","fields","input","lblpl","lmt","class"]

    def __init__(self, server="https://elk.xjsdtech.com", 
                 username="ai", 
                 password="ai@123456", 
                 env:KongmingEnvironmentType="uat",
                 exclude_fields:Union[List[str],None]=None):
        self.server=server
        self.auth = (username, password)
        self.exclude_fields = exclude_fields or KongmingELKServer.DEFAUL_EXCLUDE_FIELDS

        self.url = self._format_url(env)

        self.headers = {
            'Content-Type': 'application/json',
            'kbn-xsrf': 'kibana'
        }

    def _format_url(self, env:KongmingEnvironmentType)->str:
        return f'{self.server}/s/ai/api/console/proxy?path={env}-kongming-%2A%2F_search&method=GET'

    def transform_record(self, record):
        src = record['_source']

        def is_json_seriable(x):
            try:
                _ = json.dumps(x)
                return True
            except:
                return False


        for remove_key in ['_ignored', '_score', '_type', 'sort']:
            if remove_key in record:
                del record[remove_key]

        for remove_key in ['messageobj', 'log', 'input', 'lmt', 'level', 'fields', 'class', 'lblpl', 'lnode', 'lenv', 'type', 'sort']:
            if remove_key in src:
                del src[remove_key]

        if 'message' in src and isinstance(src['message'], str):
            try:
                msg = src['message']

                if ',---headers' in msg:
                    splits = msg.split(',---headers')
                    msg = splits[0]
                    src['message'] = msg
                    src['headers'] = splits[1]

                    try:
                        src['headers'] = eval(splits[1])
                    except:
                        pass

                # TODO: support regex prefix
                #.   'start rule match:{query},domain:'
                #.   'get context payload traceId:{trace_id}, response:'
                #.   'music {query} response: '
                for prefix in ['调用魅族服务结束，返回结果:',
                            'asr-result:',
                            'music_rule_response: ',
                            'phonecall_rule_response: ',
                            'music_ml_response: ',
                            'upload request:',
                            'upload result:',
                            'receive request:',
                            'start normalize-slot:',
                            'summary request:',
                            'deal request:',
                            'post  body ',
                            ' nlp _result:',
                            'todos request:',
                            '数据库中 asrRecord:',
                            "合规账号查询结果响应:",
                            '收到数据',
                            '合规文本请求',
                            '合规文本响应',
                            '合规图片响应',
                            'tts 请求 数据',
                            'answers  response:',
                            'answer request params:',
                            'start request:',
                            'matched normalize-slot:',
                            'received client request text: ',
                            'current instruction info is:',
                            'global_ml_response:',
                            'upload stkscontext request:',
                            'global request :metadata ',
                            'global_rule_response: ',
                            'longtail_rule_response: ',
                            'hinter request params:',
                            'received speech vad0 info, send to client vad mid result, msg: ',
                            'say visible v2 start, request:',
                            'speech client onMessage received: ']:
                    if msg.startswith(prefix):
                        msg = msg[len(prefix):]
                        src['message.prefix'] = prefix
                        break
                src['message'] = msg

                for postfix in [',从发首包到收到结果耗时:', 
                                ',version is:', 
                                ',domain:weather',
                                '-- 耗时:',
                                ' 耗时:',
                                ',耗时:',
                                ',耗时：',
                                ', latency=',
                                ',url:',
                                ',session:',
                                ',url:http://myvu-rule.xr-nbs.svc.cluster.local']:
                    if postfix in msg:
                        pos = msg.index(postfix)
                        src['message.postfix'] = msg[pos:]
                        msg = msg[:pos]

                        break

                src['message'] = msg

                msg = json.loads(msg)

                if type(msg) == str:
                    # 可能是又嵌套了一层的json, 例如central-manager的合规文本响应
                    try:
                        msg = json.loads(msg)
                    except Exception as e:
                        print(e)

                if isinstance(msg, dict):
                    x = msg.get('msg')
                    if isinstance(x, str):
                        if '<HTTPStatus.OK: 200>' in x:
                            x = x.replace('<HTTPStatus.OK: 200>', '200')
                        if '<Response [200]>' in x:
                            x = x.replace('<Response [200]>', '200')

                        msg['msg'] = x

                        if not x.startswith('parse request'): # badcase from laname:'dlg-dm-glasses'
                            for prefix in ['response: ',
                                            'got query embedding: ', 
                                            'tokenizer inputs: ',
                                            'load profile succeed: ',
                                            'Get request: ',
                                            'Chitchat Skill response: ',
                                            'multi_answers：',
                                            'Chitchat Parse response:',
                                            'past context info: ',
                                            'base multi parse request, nlu_info: ',
                                            'save profile to redis succeed! profile info: ',
                                            "{'get_dify_global_todos response: 200, text:",
                                        ]:
                                if x.startswith(prefix):
                                    x = x[len(prefix):]

                                    if prefix == "{'get_dify_global_todos response: 200, text:":
                                        x = x[:-2]

                                    msg['msg'] = x
                                    msg['msg.prefix'] = prefix

                                    break

                            for postfix in ['， new_key=',
                                            ', business_state:']:
                                if postfix in x:
                                    pos = x.index(postfix)
                                    msg['msg.postfix'] = x[pos:]
                                    x = x[:pos]
                                    msg['msg'] = x
                                    break

                            try:
                                x = eval(x)

                                if is_json_seriable(x):
                                    msg['msg'] = x
                            except Exception as e:
                                # print('++++', x)
                                # print('===> ', e)
                                pass

                    for key in ['result']:
                        try:
                            msg[key] = json.loads(msg[key])
                        except:
                            pass

                src['message'] = msg
            except Exception as e:
                pass

        for key in ['asr-recognize-start',
                    'asr-recognize-result',
                    'api-server-request',
                    'api-server-response', 
                    'central-nlp-request',
                    'central-nlp-response',
                    'central-hinter-request',
                    'central-hinter-response',
                    'central-answer-request',
                    'central-answer-response'
                    ]:
            try:
                src[key] = json.loads(src[key])
            except:
                pass

        return record

    def _run_query(self, 
                   request_body:Dict[str, Any], 
                   size:int,
                   pagesize:int,
                   env:Optional[KongmingEnvironmentType]=None,
                   out_file:Optional[str]=None):
        url = self._format_url(env) if env else self.url

        response = httpx.post(url, auth=self.auth, headers=self.headers, json=request_body, timeout=20)
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
                    response = httpx.post(url, auth=self.auth, headers=self.headers, json=request_body)
                    res_json = response.json()
                    records += res_json['hits']['hits']

        # print(json.dumps(request_body, indent=2, ensure_ascii=False))
        return [self.transform_record(r) for r in records]

    def query_dialogs(self, 
                      filter: DialogLogFilter, 
                      size:int=10000, 
                      pagesize:int=1000, 
                      env:Optional[KongmingEnvironmentType]=None,
                      out_file:Optional[str]=None
                    ) -> Tuple[Dict[str,Any],List[DialogRound]]:
        fields = ["central-nlp-request", "central-nlp-response", "central-answer-request", "central-answer-response"]
        must_clause = [
                        {
                            "bool": {
                                "should": [
                                    {
                                        "exists": { "field": field }
                                    } for field in fields
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    ]

        if filter.phrase:
            must_clause.append(                        {
                            "multi_match": {
                                "query": f"{filter.phrase}",
                                "type": "phrase",
                                "fields": fields
                            }
            })


        if filter.timestamp_begin:
            if  filter.timestamp_end:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "gte": filter.timestamp_begin,
                            "lt":  filter.timestamp_end,
                        }
                    }
                })
            else:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "gte": filter.timestamp_begin,
                        }
                    }
                })
        elif filter.timestamp_end:
                must_clause.append({
                    "range": {
                        "@timestamp": {
                            "lt":  filter.timestamp_end,
                        }
                    }
                })

        if filter.glass_product is not None:
            must_clause.append({
                "multi_match": {
                "query": f"\"glassProduct\":\"{filter.glass_product}\"",
                "type": "phrase",
                "fields": fields
                }
            })

        if filter.id_type and filter.id_value:
            must_clause.append({
                "multi_match": {
                "query": f"\"{filter.id_type}\":\"{filter.id_value}\"",
                "type": "phrase",
                "fields": fields
                }
            })

        # 对每个trace_id, 实际可能搜到4条或６条 (两次nlp请求+响应，１次llm请求+响应)，这里放大到８倍
        query_size = min(size * 8, 10000)

        request_body = {
            "query": {
                "bool": {
                    "must": must_clause,
                }
            },
            "from": 0,
            "size": query_size,
            "sort": [
                { "@timestamp": "asc" }
            ],
            "_source": {
                "excludes": self.exclude_fields
            }
        }

        # print(json.dumps(request_body, indent=2, ensure_ascii=False ))
        records = self._run_query(request_body=request_body, size=query_size, pagesize=pagesize, env=env, out_file=out_file)

        traceid_round_map = {}
        for r in records:
            traceId = r['_source']['traceId']
            if traceId not in traceid_round_map:
                traceid_round_map[traceId] = {
                    'nlp_request': None,
                    'nlp_response': None,
                    'llm_request': None,
                    'llm_response': None
                }

            # 在大模型请求时，同一个traceId可能会有２个NLU请求，第二个通话是清除上下文的动作，因此如果已经有第一个消息了，就不要再存入map
            if 'central-nlp-request' in r['_source']:
                if traceid_round_map[traceId].get('nlp_request') is None:
                    traceid_round_map[traceId]['nlp_request'] = r
            elif 'central-nlp-response' in r['_source']:
                if traceid_round_map[traceId].get('nlp_request') is not None and traceid_round_map[traceId].get('nlp_response') is None:
                    traceid_round_map[traceId]['nlp_response'] = r
            elif 'central-answer-request' in r['_source']:
                traceid_round_map[traceId]['llm_request'] = r
            elif 'central-answer-response' in r['_source']:
                traceid_round_map[traceId]['llm_response'] = r

        rounds:List[DialogRound] = []

        for traceId in traceid_round_map:
            round = DialogRound.from_records(**traceid_round_map[traceId])
            rounds.append(round)

        if len(rounds) > size:
            rounds = rounds[:size]

        return records, rounds
    def query_by_phrase(self, 
                        match_phrase:str,
                        match_fields:List[str]=["*"],
                        terms:Union[Dict[str,Any],None]=None,
                        timestamp_begin:Optional[str]=None,
                        timestamp_end:Optional[str]=None,
                        size:int=10000,
                        pagesize:int=10,
                        env:Optional[KongmingEnvironmentType]=None,
                        out_file:Optional[str]=None):
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


        return self._run_query(request_body=request_body, size=size, pagesize=pagesize, env=env, out_file=out_file)


    def query_by_time_range(self, 
                        timestamp_begin:Optional[str]=None,
                        timestamp_end:Optional[str]=None,
                        size:int=10000,
                        pagesize:int=10,
                        env:Optional[KongmingEnvironmentType]=None,
                        out_file:Optional[str]=None):
        if timestamp_begin is None and timestamp_end is None:
            return None

        must_clause = []

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
                    "must": must_clause
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

        return self._run_query(request_body=request_body, size=size, pagesize=pagesize, env=env, out_file=out_file)

    def query_dialog_by_trace_id(self, trace_id:str, env:Optional[KongmingEnvironmentType]=None, out_file:Optional[str]=None):
        from .utils import adjust_timestamp

        filter = DialogLogFilter(phrase=trace_id)

        records, rounds = self.query_dialogs(filter, size=1, pagesize=10, env=env, out_file=None)

        if rounds:
            round = rounds[0]
            start_time = round.nlp_round.request_timestamp
            stop_time = round.llm_round.response_timestamp if (round.llm_round and round.llm_round.response_timestamp) else None

            if not stop_time:
                stop_time = round.nlp_round.response_timestamp if (round.nlp_round and round.nlp_round.response_timestamp) else None

            if start_time and stop_time:
                start_time = adjust_timestamp(start_time, -15.0)
                stop_time = adjust_timestamp(stop_time, 2.0)

                records = self.query_by_phrase(timestamp_begin=start_time,
                                     timestamp_end=stop_time,
                                     match_phrase=trace_id,
                                     size=10000,
                                     pagesize=1000,
                                     out_file=out_file)
                
                return records, rounds

        return None

    def query_by_trace_id(self, trace_id:str, size:int=10000, pagesize:int=10, env:Optional[KongmingEnvironmentType]=None, out_file:Optional[str]=None):
        return self.query_by_phrase(trace_id, size=size, pagesize=pagesize, env=env, out_file=out_file)
